"""core/__init__.py — Pacote de constantes e configurações globais."""
from core.constants import (
    APP_ENV,
    IGNORED_DIRS,
    IGNORED_FILES,
    LOG_LEVEL,
    MAX_ZIP_SIZE_BYTES,
    MAX_ZIP_SIZE_MB,
    PYPROJECT_FILE,
    REQUIREMENTS_FILES,
    SUPPORTED_EXTENSIONS,
)
from core.paths import (
    CORE_DIR,
    GUI_DIR,
    ROOT_DIR,
    SRC_DIR,
    TEMP_DIR,
    TESTS_DIR,
    get_upload_dir,
)

__all__ = [
    # constants
    "APP_ENV",
    "LOG_LEVEL",
    "MAX_ZIP_SIZE_MB",
    "MAX_ZIP_SIZE_BYTES",
    "SUPPORTED_EXTENSIONS",
    "IGNORED_DIRS",
    "IGNORED_FILES",
    "REQUIREMENTS_FILES",
    "PYPROJECT_FILE",
    # paths
    "ROOT_DIR",
    "CORE_DIR",
    "SRC_DIR",
    "GUI_DIR",
    "TESTS_DIR",
    "TEMP_DIR",
    "get_upload_dir",
]
