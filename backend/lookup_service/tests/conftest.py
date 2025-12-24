import sys
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
LOOKUP_SERVICE_DIR = TESTS_DIR.parent
BACKEND_DIR = LOOKUP_SERVICE_DIR.parent

for path in (LOOKUP_SERVICE_DIR, BACKEND_DIR / "audos_console"):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
