"""La documentación no debe enlazar a archivos que no existen."""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
DOCUMENTOS = ["README.md", "docs/CAMBIOS_DISENO.md", "docs/fase3-uml/CHANGELOG_UML.md"]
ENLACE = re.compile(r"\]\((<[^>]+>|[^)\s]+)\)")  # [texto](ruta) o [texto](<ruta con espacios>)


@pytest.mark.parametrize("documento", DOCUMENTOS)
def test_todos_los_enlaces_relativos_existen(documento):
    ruta = RAIZ / documento
    for destino in ENLACE.findall(ruta.read_text(encoding="utf-8")):
        destino = destino.strip("<>").split("#")[0]
        if destino and not destino.startswith(("http", "mailto")):
            assert (ruta.parent / destino).exists(), f"{documento} enlaza a {destino}, que no existe"
