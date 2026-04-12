"""
tests/generate_test_zips.py  –  Gerador de ZIPs de teste
Cria vários arquivos .zip (e um .tar.gz) na pasta tests/fixtures/
para exercitar todos os cenários de decompressor.py e filter.py.

Uso:
    python -m tests.generate_test_zips
"""
from __future__ import annotations

import io
import os
import struct
import zipfile
from pathlib import Path

# ── Diretório de saída ────────────────────────────────────────────────────────
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _ensure_fixtures_dir() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_zip(name: str, files: dict[str, str | bytes]) -> Path:
    """Cria um ZIP com os arquivos dados (nome -> conteúdo)."""
    path = FIXTURES_DIR / name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, content in files.items():
            data = content.encode() if isinstance(content, str) else content
            zf.writestr(fname, data)
    print(f"  ✔ {name} ({path.stat().st_size:,} bytes)")
    return path


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CENÁRIOS PARA decompressor.py
# ═══════════════════════════════════════════════════════════════════════════════


def gen_valid_simple() -> None:
    """ZIP válido com alguns .py — cenário feliz."""
    _create_zip("valid_simple.zip", {
        "main.py": "print('hello')\n",
        "utils.py": "def add(a, b): return a + b\n",
        "src/core.py": "class Core: pass\n",
    })


def gen_valid_nested() -> None:
    """ZIP válido com estrutura de pastas profunda."""
    _create_zip("valid_nested.zip", {
        "projeto/app.py": "from projeto.utils import helper\n",
        "projeto/utils/__init__.py": "",
        "projeto/utils/helper.py": "def helper(): ...\n",
        "projeto/models/user.py": "class User: ...\n",
        "projeto/models/__init__.py": "",
    })


def gen_wrong_extension() -> None:
    """Arquivo com extensão errada (.tar.gz) — deve ser rejeitado."""
    path = FIXTURES_DIR / "wrong_ext.tar.gz"
    # Conteúdo é um ZIP real, mas a extensão está errada
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("hello.py", "print('hi')\n")
    path.write_bytes(buf.getvalue())
    print(f"  ✔ wrong_ext.tar.gz ({path.stat().st_size:,} bytes)")


def gen_oversized() -> None:
    """ZIP que excede MAX_ZIP_SIZE_BYTES (50 MB) — deve ser rejeitado.

    Cria um arquivo de ~51 MB com dados compressíveis (zeros) para que
    a geração seja rápida mas o arquivo em disco ultrapasse o limite.
    """
    path = FIXTURES_DIR / "oversized.zip"
    target_size = 51 * 1024 * 1024  # 51 MB

    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as zf:
        # ZIP_STORED = sem compressão, o tamanho do ZIP ≈ tamanho dos dados
        chunk = b"\x00" * (1024 * 1024)  # 1 MB de zeros
        for i in range(52):
            zf.writestr(f"pad_{i:03d}.bin", chunk)

    print(f"  ✔ oversized.zip ({path.stat().st_size / 1024 / 1024:.1f} MB)")


def gen_corrupted() -> None:
    """Arquivo .zip com bytes aleatórios — não é um ZIP válido."""
    path = FIXTURES_DIR / "corrupted.zip"
    # Cabeçalho inválido (não começa com PK\x03\x04)
    path.write_bytes(b"NOT_A_REAL_ZIP_FILE" + os.urandom(256))
    print(f"  ✔ corrupted.zip ({path.stat().st_size:,} bytes)")


def gen_path_traversal() -> None:
    """ZIP com path traversal (zip-slip) — deve ser bloqueado pelo decompressor.

    Injeta manualmente um entry com '../' no nome usando manipulação binária.
    """
    path = FIXTURES_DIR / "path_traversal.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("safe_file.py", "print('safe')\n")
    raw = buf.getvalue()

    # Cria um segundo ZIP adicionando um membro com path traversal
    buf2 = io.BytesIO()
    with zipfile.ZipFile(buf2, "w") as zf:
        zf.writestr("safe_file.py", "print('safe')\n")
        zf.writestr("../../../etc/malicious.py", "print('hacked')\n")
    path.write_bytes(buf2.getvalue())
    print(f"  ✔ path_traversal.zip ({path.stat().st_size:,} bytes)")


def gen_empty_zip() -> None:
    """ZIP vazio (sem membros) — válido mas sem arquivos."""
    path = FIXTURES_DIR / "empty.zip"
    with zipfile.ZipFile(path, "w") as zf:
        pass  # nenhum arquivo
    print(f"  ✔ empty.zip ({path.stat().st_size:,} bytes)")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. CENÁRIOS PARA filter.py
# ═══════════════════════════════════════════════════════════════════════════════


def gen_with_ignored_dirs() -> None:
    """ZIP contendo diretórios que devem ser removidos pelo filtro.

    IGNORED_DIRS = {tests, test, docs, doc, .venv, venv, env,
                    __pycache__, .git, build, dist}
    """
    files: dict[str, str] = {
        # Arquivos válidos que devem sobreviver
        "projeto/app.py": "print('app')\n",
        "projeto/lib.py": "def lib(): ...\n",
        # Diretórios ignorados
        "__pycache__/cached.cpython-312.pyc": "<bytecode>",
        ".git/config": "[core]\n",
        ".git/HEAD": "ref: refs/heads/main\n",
        "venv/lib/site-packages/pkg.py": "# virtualenv\n",
        ".venv/pyvenv.cfg": "home = /usr/bin\n",
        "tests/test_app.py": "def test(): ...\n",
        "test/test_other.py": "def test2(): ...\n",
        "docs/readme.md": "# Docs\n",
        "doc/index.html": "<html></html>\n",
        "build/lib/main.py": "# build artifact\n",
        "dist/projeto-1.0.tar.gz": "<binary>",
        "env/bin/activate": "# activate\n",
    }
    _create_zip("with_ignored_dirs.zip", files)


def gen_with_ignored_files() -> None:
    """ZIP contendo arquivos que devem ser removidos pelo filtro.

    IGNORED_FILES = {setup.py, conftest.py}
    """
    _create_zip("with_ignored_files.zip", {
        "app.py": "print('app')\n",
        "utils.py": "def util(): ...\n",
        "setup.py": "from setuptools import setup\nsetup()\n",
        "conftest.py": "import pytest\n",
        "src/conftest.py": "# nested conftest\n",
    })


def gen_with_unsupported_extensions() -> None:
    """ZIP com extensões não suportadas — apenas .py deve sobreviver.

    SUPPORTED_EXTENSIONS = {.py}
    """
    _create_zip("with_unsupported_exts.zip", {
        # Devem sobreviver
        "main.py": "print('main')\n",
        "helpers.py": "def h(): ...\n",
        # Devem ser removidos
        "README.md": "# Readme\n",
        "data.json": '{"key": "value"}\n',
        "config.yaml": "key: value\n",
        "script.sh": "#!/bin/bash\necho hi\n",
        "image.png": b"\x89PNG".decode("latin-1"),
        "notes.txt": "anotações\n",
        "lib.c": "int main() { return 0; }\n",
        "style.css": "body { color: red; }\n",
        "index.html": "<html><body>hi</body></html>\n",
        "Makefile": "all:\n\techo build\n",
        "requirements.txt": "requests>=2.0\n",
    })


def gen_only_valid_py() -> None:
    """ZIP com apenas arquivos .py válidos — nada deve ser removido."""
    _create_zip("only_valid_py.zip", {
        "app.py": "print('running')\n",
        "core/__init__.py": "",
        "core/engine.py": "class Engine: pass\n",
        "utils/helpers.py": "def help(): ...\n",
        "utils/__init__.py": "",
    })


def gen_mixed_full() -> None:
    """ZIP misto com TODOS os cenários de filtragem combinados.

    Contém: dirs ignorados, arquivos ignorados, extensões inválidas,
    e arquivos .py válidos que devem sobreviver.
    """
    _create_zip("mixed_full.zip", {
        # ── válidos (devem sobreviver) ──
        "projeto/app.py": "from projeto.core import run\n",
        "projeto/core/__init__.py": "",
        "projeto/core/engine.py": "def run(): print('ok')\n",
        "projeto/utils.py": "import os\n",
        # ── diretórios ignorados ──
        "projeto/__pycache__/app.cpython-312.pyc": "<cache>",
        "projeto/.git/HEAD": "ref: refs/heads/main\n",
        "projeto/venv/lib/pkg.py": "# venv\n",
        "projeto/tests/test_engine.py": "def test(): ...\n",
        "projeto/docs/api.md": "# API\n",
        "projeto/build/out.py": "# build\n",
        # ── arquivos ignorados ──
        "projeto/setup.py": "from setuptools import setup; setup()\n",
        "projeto/conftest.py": "import pytest\n",
        # ── extensões não suportadas ──
        "projeto/README.md": "# Projeto\n",
        "projeto/data.csv": "col1,col2\n1,2\n",
        "projeto/config.toml": '[project]\nname = "x"\n',
        "projeto/Dockerfile": "FROM python:3.12\n",
        "projeto/requirements.txt": "flask\n",
    })


def gen_deeply_nested_ignored() -> None:
    """ZIP com diretórios ignorados profundamente aninhados."""
    _create_zip("deeply_nested_ignored.zip", {
        "a/b/c/app.py": "print('deep')\n",
        "a/b/c/__pycache__/cached.pyc": "<cache>",
        "a/b/.git/objects/abc": "<git-object>",
        "a/b/c/d/venv/lib/x.py": "# env\n",
        "a/b/c/d/main.py": "print('main')\n",
    })


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CENÁRIOS DE SEGURANÇA (ZIPs perigosos)
# ═══════════════════════════════════════════════════════════════════════════════


def gen_zip_bomb() -> None:
    """Zip bomb — arquivo pequeno que expande para um tamanho enorme.

    Cria um ZIP de poucos KB que, ao ser extraído, gera ~1 GB de dados.
    Usa compressão máxima com dados repetitivos (zeros).
    """
    path = FIXTURES_DIR / "zip_bomb.zip"
    # 1 GB de zeros comprime muito bem (~1 MB de ZIP)
    huge_content = b"\x00" * (100 * 1024 * 1024)  # 100 MB de zeros
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for i in range(10):  # 10 × 100 MB = 1 GB descomprimido
            zf.writestr(f"bomb_{i:03d}.bin", huge_content)
    print(f"  ✔ zip_bomb.zip ({path.stat().st_size / 1024:.1f} KB → ~1 GB descomprimido)")


def gen_nested_zip_bomb() -> None:
    """Zip bomb aninhado — ZIP dentro de ZIP dentro de ZIP.

    Cada camada contém o ZIP anterior, criando expansão exponencial.
    """
    # Camada mais interna: 10 MB de zeros
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr("payload.bin", b"\x00" * (10 * 1024 * 1024))

    # Aninha 5 camadas
    current = inner.getvalue()
    for depth in range(5):
        layer = io.BytesIO()
        with zipfile.ZipFile(layer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"layer_{depth}.zip", current)
        current = layer.getvalue()

    path = FIXTURES_DIR / "nested_zip_bomb.zip"
    path.write_bytes(current)
    print(f"  ✔ nested_zip_bomb.zip ({path.stat().st_size:,} bytes, 5 camadas)")


def gen_absolute_path() -> None:
    """ZIP com caminhos absolutos — tenta escrever em locais do sistema."""
    path = FIXTURES_DIR / "absolute_path.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("safe.py", "print('safe')\n")
        # Caminhos absolutos perigosos (Linux e Windows)
        zf.writestr("/etc/passwd", "root:x:0:0:::/bin/bash\n")
        zf.writestr("/tmp/malware.py", "import os; os.system('rm -rf /')\n")
        zf.writestr("C:/Windows/System32/evil.py", "print('evil')\n")
    path.write_bytes(buf.getvalue())
    print(f"  ✔ absolute_path.zip ({path.stat().st_size:,} bytes)")


def gen_null_byte_filename() -> None:
    """ZIP com bytes nulos no nome do arquivo — pode causar truncamento."""
    path = FIXTURES_DIR / "null_byte_filename.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("normal.py", "print('ok')\n")
        zf.writestr("evil\x00.py", "print('null byte')\n")
        zf.writestr("path/to\x00/../../etc/passwd", "hacked\n")
    path.write_bytes(buf.getvalue())
    print(f"  ✔ null_byte_filename.zip ({path.stat().st_size:,} bytes)")


def gen_long_filename() -> None:
    """ZIP com nomes de arquivo extremamente longos — pode causar erros de FS."""
    _create_zip("long_filename.zip", {
        "normal.py": "print('ok')\n",
        "a" * 255 + ".py": "print('long name')\n",  # limite NTFS/ext4
        "deep/" * 50 + "file.py": "print('deep path')\n",  # caminho profundo
        "b" * 500 + ".py": "print('very long')\n",  # excede limite de FS
    })


def gen_duplicate_entries() -> None:
    """ZIP com entradas duplicadas — mesmo nome de arquivo múltiplas vezes.

    Pode causar sobrescrita silenciosa ou comportamento inesperado.
    """
    path = FIXTURES_DIR / "duplicate_entries.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("config.py", "SECRET = 'original'\n")
        zf.writestr("config.py", "SECRET = 'overwritten_malicious'\n")
        zf.writestr("app.py", "print('first')\n")
        zf.writestr("app.py", "import os; os.system('whoami')\n")
    path.write_bytes(buf.getvalue())
    print(f"  ✔ duplicate_entries.zip ({path.stat().st_size:,} bytes)")


def gen_special_chars_filename() -> None:
    """ZIP com caracteres especiais e unicode nos nomes — pode causar injeção."""
    _create_zip("special_chars_filename.zip", {
        "normal.py": "print('ok')\n",
        "file with spaces.py": "print('spaces')\n",
        "café.py": "print('unicode')\n",
        "file;rm -rf.py": "print('injection attempt')\n",
        "file|cat /etc/passwd.py": "print('pipe injection')\n",
        "$(whoami).py": "print('command substitution')\n",
        "file\\..\\..\\secret.py": "print('backslash traversal')\n",
        ".hidden_file.py": "print('dot file')\n",
        "CON.py": "print('reserved Windows name')\n",
        "NUL.py": "print('reserved Windows name')\n",
        "PRN.py": "print('reserved Windows name')\n",
    })


def gen_symlink_zip() -> None:
    """ZIP contendo um symlink apontando para fora do diretório.

    Simula um ataque via link simbólico dentro do ZIP.
    """
    path = FIXTURES_DIR / "symlink.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.py", "print('legit')\n")
        # Cria um entry que simula um symlink (external_attr + conteúdo = target)
        info = zipfile.ZipInfo("link_to_passwd")
        info.create_system = 3  # Unix
        # Symlink: mode 0o120777 no Unix
        info.external_attr = (0o120777 << 16)
        zf.writestr(info, "/etc/passwd")

        info2 = zipfile.ZipInfo("link_to_root")
        info2.create_system = 3
        info2.external_attr = (0o120777 << 16)
        zf.writestr(info2, "/")
    path.write_bytes(buf.getvalue())
    print(f"  ✔ symlink.zip ({path.stat().st_size:,} bytes)")


def gen_path_traversal_variants() -> None:
    """ZIP com múltiplas variantes de path traversal."""
    path = FIXTURES_DIR / "path_traversal_variants.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("safe.py", "print('safe')\n")
        # Variantes de traversal
        zf.writestr("../escape.py", "print('one level up')\n")
        zf.writestr("../../escape2.py", "print('two levels up')\n")
        zf.writestr("foo/../../escape3.py", "print('relative traversal')\n")
        zf.writestr("foo/bar/../../../escape4.py", "print('deeper traversal')\n")
        zf.writestr("./../escape5.py", "print('dot-slash traversal')\n")
        zf.writestr("foo/./../../escape6.py", "print('dot in middle')\n")
    path.write_bytes(buf.getvalue())
    print(f"  ✔ path_traversal_variants.zip ({path.stat().st_size:,} bytes)")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════


def main() -> None:
    _ensure_fixtures_dir()
    print("Gerando ZIPs de teste em:", FIXTURES_DIR.resolve())
    print()

    print("─── Cenários: decompressor.py ───")
    gen_valid_simple()
    gen_valid_nested()
    gen_wrong_extension()
    gen_oversized()
    gen_corrupted()
    gen_path_traversal()
    gen_empty_zip()
    print()

    print("─── Cenários: filter.py ───")
    gen_with_ignored_dirs()
    gen_with_ignored_files()
    gen_with_unsupported_extensions()
    gen_only_valid_py()
    gen_mixed_full()
    gen_deeply_nested_ignored()
    print()

    print("─── Cenários: segurança (ZIPs perigosos) ───")
    gen_zip_bomb()
    gen_nested_zip_bomb()
    gen_absolute_path()
    gen_null_byte_filename()
    gen_long_filename()
    gen_duplicate_entries()
    gen_special_chars_filename()
    gen_symlink_zip()
    gen_path_traversal_variants()
    print()

    print("✅ Todos os ZIPs gerados com sucesso!")


if __name__ == "__main__":
    main()
