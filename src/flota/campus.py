"""Carga los datos del campus (campus.json), arma la flota inicial y lee la geometría de OSM."""
import json
from pathlib import Path

from flota.dominio.flota import Flota
from flota.dominio.robot import Dron, RobotOrugas, RobotRuedas
from flota.dominio.ruta import RedSenderos
from flota.dominio.ubicacion import Ubicacion, Zona

RUTA_CAMPUS = Path(__file__).with_name("campus.json")
RUTA_GEOMETRIA = Path(__file__).with_name("campus_osm.json")  # la genera scripts/descargar_campus_osm.py
TIPOS_ROBOT = {"ruedas": RobotRuedas, "orugas": RobotOrugas, "dron": Dron}
# caminos internos del campus; las calles públicas (residential, tertiary) quedan fuera.
# Las escaleras entran: sin ellas el campus queda partido (supuesto S8: hay rampa al lado)
TIPOS_SENDERO = {"footway", "pedestrian", "path", "service", "steps", "living_street"}


def cargar_campus(ruta: Path = RUTA_CAMPUS) -> tuple[dict[str, Ubicacion], Flota]:
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    red = crear_red_senderos(cargar_geometria())
    ubicaciones = {clave: Ubicacion(u["nombre"], u["lat"], u["lon"], Zona[u["zona"]])
                   for clave, u in datos["ubicaciones"].items()}
    flota = Flota()
    for r in datos["robots"]:
        extras = {k: v for k, v in r.items() if k not in ("tipo", "id", "ubicacion")}
        flota.agregar(TIPOS_ROBOT[r["tipo"]](r["id"], ubicaciones[r["ubicacion"]], red=red, **extras))
    return ubicaciones, flota


def cargar_geometria(ruta: Path = RUTA_GEOMETRIA) -> dict:
    """Perímetro, edificios (contorno y pisos) y caminos del campus, en coordenadas [lat, lon].

    Son datos de dibujo y de rutas, no del dominio: se leen del archivo, sin internet.
    """
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def crear_red_senderos(geometria: dict) -> RedSenderos:
    return RedSenderos([c["puntos"] for c in geometria["caminos"] if c["tipo"] in TIPOS_SENDERO])
