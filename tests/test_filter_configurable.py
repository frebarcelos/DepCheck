"""
tests/test_filter_configurable.py  –  Dev 2 | Sprint 4
Testes para o parâmetro extra_excluded_dirs de filter_extracted().
Cobre retrocompatibilidade, exclusão de diretório customizado e union
com IGNORED_DIRS.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.filter import filter_extracted


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_py(directory: Path, name: str, content: str = "x = 1") -> Path:
    """Cria um arquivo .py com conteúdo mínimo dentro de *directory*."""
    f = directory / name
    f.write_text(content, encoding="utf-8")
    return f


def _make_subdir_py(root: Path, subdir: str, filename: str = "mod.py") -> Path:
    """Cria sub-diretório com um arquivo .py dentro de *root*."""
    d = root / subdir
    d.mkdir(parents=True, exist_ok=True)
    return _make_py(d, filename)


# ── Testes ────────────────────────────────────────────────────────────────────


class TestFilterExtraExcludedDirs:
    """Testa filter_extracted() com extra_excluded_dirs especificado."""

    def test_extra_dir_is_excluded(self, tmp_path: Path) -> None:
        """Diretório em extra_excluded_dirs deve ser removido junto com seu conteúdo."""
        main_py = _make_py(tmp_path, "main.py")
        _make_subdir_py(tmp_path, "mydir")

        kept = filter_extracted(tmp_path, extra_excluded_dirs=["mydir"])

        assert (tmp_path / "mydir").exists() is False, "mydir deveria ter sido removido"
        assert len(kept) == 1
        assert kept[0].name == "main.py"

    def test_extra_dir_combined_with_defaults(self, tmp_path: Path) -> None:
        """IGNORED_DIRS padrão e extra_excluded_dirs devem ser combinados (union)."""
        _make_py(tmp_path, "app.py")
        # diretório padrão
        _make_subdir_py(tmp_path, ".git")
        # diretório customizado
        _make_subdir_py(tmp_path, "scripts")

        kept = filter_extracted(tmp_path, extra_excluded_dirs=["scripts"])

        assert (tmp_path / ".git").exists() is False, ".git deveria ter sido removido"
        assert (tmp_path / "scripts").exists() is False, "scripts deveria ter sido removido"
        assert len(kept) == 1

    def test_multiple_extra_dirs(self, tmp_path: Path) -> None:
        """Múltiplos diretórios extras devem ser todos excluídos."""
        _make_py(tmp_path, "core.py")
        _make_subdir_py(tmp_path, "migrations")
        _make_subdir_py(tmp_path, "fixtures")
        _make_subdir_py(tmp_path, "sandbox")

        kept = filter_extracted(
            tmp_path,
            extra_excluded_dirs=["migrations", "fixtures", "sandbox"],
        )

        assert (tmp_path / "migrations").exists() is False
        assert (tmp_path / "fixtures").exists() is False
        assert (tmp_path / "sandbox").exists() is False
        assert len(kept) == 1
        assert kept[0].name == "core.py"

    def test_extra_dir_not_present_is_ignored_gracefully(self, tmp_path: Path) -> None:
        """Diretório extra que não existe não deve causar erros."""
        _make_py(tmp_path, "utils.py")

        kept = filter_extracted(tmp_path, extra_excluded_dirs=["nonexistent_dir"])

        assert len(kept) == 1
        assert kept[0].name == "utils.py"


class TestFilterRetrocompatibility:
    """Testa que o comportamento sem extra_excluded_dirs é idêntico ao original."""

    def test_without_parameter_keeps_py_files(self, tmp_path: Path) -> None:
        """Chamada sem extra_excluded_dirs deve retornar só .py sem deletar manifests."""
        _make_py(tmp_path, "main.py")
        (tmp_path / "readme.txt").write_text("doc", encoding="utf-8")

        kept = filter_extracted(tmp_path)

        assert len(kept) == 1
        assert kept[0].name == "main.py"
        # Arquivos não-.py são preservados no disco (pyproject.toml, requirements.txt, etc.)
        assert (tmp_path / "readme.txt").exists()

    def test_without_parameter_removes_ignored_dirs(self, tmp_path: Path) -> None:
        """Chamada sem extra_excluded_dirs deve continuar removendo IGNORED_DIRS."""
        _make_py(tmp_path, "app.py")
        _make_subdir_py(tmp_path, ".git")
        _make_subdir_py(tmp_path, "__pycache__")
        _make_subdir_py(tmp_path, "venv")

        kept = filter_extracted(tmp_path)

        assert not (tmp_path / ".git").exists()
        assert not (tmp_path / "__pycache__").exists()
        assert not (tmp_path / "venv").exists()
        assert len(kept) == 1

    def test_none_parameter_behaves_same_as_no_parameter(self, tmp_path: Path) -> None:
        """extra_excluded_dirs=None deve ser equivalente a omitir o parâmetro."""
        _make_py(tmp_path, "run.py")
        _make_subdir_py(tmp_path, "build")

        kept = filter_extracted(tmp_path, extra_excluded_dirs=None)

        assert not (tmp_path / "build").exists()
        assert len(kept) == 1


class TestFilterEmptyList:
    """Testa filter_extracted() com lista vazia como extra_excluded_dirs."""

    def test_empty_list_keeps_non_ignored_dirs(self, tmp_path: Path) -> None:
        """Lista vazia não deve excluir diretórios além dos padrões."""
        _make_py(tmp_path, "service.py")
        _make_subdir_py(tmp_path, "mypackage")

        kept = filter_extracted(tmp_path, extra_excluded_dirs=[])

        # mypackage não está em IGNORED_DIRS nem na lista vazia → permanece
        assert (tmp_path / "mypackage").exists()
        # arquivos .py em mypackage também são mantidos
        assert len(kept) == 2  # service.py + mypackage/mod.py

    def test_empty_list_still_removes_default_ignored_dirs(self, tmp_path: Path) -> None:
        """Lista vazia não interfere na remoção dos diretórios padrão."""
        _make_py(tmp_path, "main.py")
        _make_subdir_py(tmp_path, "tests")

        kept = filter_extracted(tmp_path, extra_excluded_dirs=[])

        assert not (tmp_path / "tests").exists()
        assert len(kept) == 1


class TestFilterCustomUserDir:
    """Testa exclusão de diretório customizado digitado pelo usuário na GUI."""

    def test_user_custom_dir_excluded(self, tmp_path: Path) -> None:
        """
        Simula o fluxo onde o usuário digita um diretório customizado na GUI.
        O diretório deve ser excluído mesmo não fazendo parte de IGNORED_DIRS.
        """
        _make_py(tmp_path, "api.py")
        # Diretório que normalmente não seria excluído
        custom_dir = tmp_path / "data_lake"
        custom_dir.mkdir()
        (custom_dir / "etl.py").write_text("pass", encoding="utf-8")

        # Simula o valor retornado por render_exclusion_config()
        user_exclusions: list[str] = ["data_lake"]

        kept = filter_extracted(tmp_path, extra_excluded_dirs=user_exclusions)

        assert not custom_dir.exists(), "data_lake deveria ter sido excluído pelo usuário"
        assert len(kept) == 1
        assert kept[0].name == "api.py"

    def test_user_custom_dir_with_nested_content(self, tmp_path: Path) -> None:
        """Diretório customizado com sub-pastas deve ser completamente removido."""
        _make_py(tmp_path, "server.py")
        nested = tmp_path / "uploads" / "raw" / "2024"
        nested.mkdir(parents=True)
        (nested / "data.py").write_text("pass", encoding="utf-8")

        kept = filter_extracted(tmp_path, extra_excluded_dirs=["uploads"])

        assert not (tmp_path / "uploads").exists()
        assert len(kept) == 1

    def test_invalid_root_raises_value_error(self, tmp_path: Path) -> None:
        """Passar um caminho que não é diretório deve lançar ValueError."""
        fake_path = tmp_path / "not_a_dir"

        with pytest.raises(ValueError, match="não é um diretório válido"):
            filter_extracted(fake_path, extra_excluded_dirs=["anything"])
