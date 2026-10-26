#!/usr/bin/env bash
# Regenera el grafo de arquitectura en .context/ con graphify (solo AST: sin LLM ni API key).
# Requiere: pip install "graphifyy==0.9.80"
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf graphify-out
graphify extract . --code-only        # respeta .graphifyignore (excluye tests/ y docs/)
# Los números de comunidad cambian entre ejecuciones: los nombres se asignan por una clase
# representativa (.context/comunidades.json, "clase": "nombre"); gana la primera que aparezca.
python3 - <<'PY'
import json
from pathlib import Path
anclas = json.loads(Path(".context/comunidades.json").read_text(encoding="utf-8"))
grafo = json.loads(Path("graphify-out/graph.json").read_text(encoding="utf-8"))
comunidad = {n["label"]: n["community"] for n in grafo["nodes"] if n.get("_callable_class")}
etiquetas = {}
for clase, nombre in anclas.items():
    if clase in comunidad:
        etiquetas.setdefault(str(comunidad[clase]), nombre)
# graphify descarta todas las etiquetas si falta alguna: las comunidades sin ancla (los
# __init__.py sueltos) se nombran por su archivo
for n in grafo["nodes"]:
    etiquetas.setdefault(str(n["community"]), "Módulo " + n.get("source_file", "?").removeprefix("src/flota/"))
Path("graphify-out/.graphify_labels.json").write_text(json.dumps(etiquetas, ensure_ascii=False, indent=1), encoding="utf-8")
PY
graphify cluster-only . --no-label
cp graphify-out/graph.json .context/architecture_graph.json
cp graphify-out/GRAPH_REPORT.md graphify-out/graph.html .context/
sed -i '1s/.*/# Graph Report - proyecto-poo/' .context/GRAPH_REPORT.md
echo "Grafo actualizado en .context/"
