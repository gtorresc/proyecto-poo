"""Todo el código compila, incluidos los paneles de la GUI que las pruebas no importan."""
from pathlib import Path

import pytest

RAIZ = Path(__file__).parent.parent
ARCHIVOS = sorted((RAIZ / "src").rglob("*.py")) + [RAIZ / "main.py"]


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda a: a.relative_to(RAIZ).as_posix())
def test_compila(archivo):
    compile(archivo.read_text(encoding="utf-8"), str(archivo), "exec")
