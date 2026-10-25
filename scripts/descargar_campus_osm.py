"""Descarga una sola vez la geometría del campus UdeM desde OpenStreetMap (Overpass).

Escribe src/flota/campus_osm.json con el perímetro del campus, los edificios (contorno y pisos)
y los caminos. El programa lee ese archivo y no consulta Overpass al ejecutarse: el mapa
funciona sin internet. Volver a correrlo solo si cambian los datos de OSM.

    python scripts/descargar_campus_osm.py
"""
import json
from datetime import date
from pathlib import Path

import requests

URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "FlotaRobotsUdeM/1.0 (proyecto academico de POO)"
ID_CAMPUS = 218900163  # way "Universidad de Medellín" (amenity=university)
# perímetro del campus más ~90 m alrededor, para que el mapa muestre algo de ciudad
SUR, OESTE, NORTE, ESTE = 6.2279, -75.6161, 6.2341, -75.6089
SALIDA = Path(__file__).resolve().parent.parent / "src" / "flota" / "campus_osm.json"

# Bloques con puntos de entrega que OSM no tiene: contorno aproximado, trazado sobre la imagen
# satelital de Esri World Imagery (2026-10-25). Si alguien los mapea en OSM, se pueden borrar.
TRAZADOS_A_MANO = [
    {"nombre": "Bloque 4 - Ingenierías", "contorno": [
        [6.230467, -75.6122643], [6.2304492, -75.6120855], [6.2303905, -75.6120855],
        [6.2303337, -75.6116027], [6.230147, -75.6116116], [6.2301737, -75.6122643]]},
    {"nombre": "Bloque 3 - Centro de Laboratorios", "contorno": [
        [6.2304225, -75.6115848], [6.2304137, -75.611254], [6.230307, -75.611254],
        [6.2303781, -75.6109768], [6.230387, -75.6107444], [6.2302092, -75.6107265],
        [6.2300937, -75.6115758]]},
    {"nombre": "Bloque 12 - Posgrados", "contorno": [
        [6.2320313, -75.6118619], [6.2320046, -75.6114775], [6.2318002, -75.6114954],
        [6.2318357, -75.6118709]]},
]

CONSULTA = f"""
[out:json][timeout:60];
(
  way({ID_CAMPUS});
  way["building"]({SUR},{OESTE},{NORTE},{ESTE});
  way["highway"]({SUR},{OESTE},{NORTE},{ESTE});
);
out tags geom;
"""


def _puntos(elemento: dict) -> list[list[float]]:
    return [[round(p["lat"], 7), round(p["lon"], 7)] for p in elemento["geometry"]]


def _niveles(etiquetas: dict):
    try:
        return int(float(etiquetas["building:levels"]))
    except (KeyError, ValueError):
        return None  # desconocido: el mapa usa una altura por defecto


def convertir(datos: dict) -> dict:
    perimetro, edificios, caminos = [], [], []
    for e in datos["elements"]:
        etiquetas = e.get("tags", {})
        if e["id"] == ID_CAMPUS:
            perimetro = _puntos(e)
        elif "building" in etiquetas:
            edificios.append({"nombre": etiquetas.get("name"), "tipo": etiquetas["building"],
                              "niveles": _niveles(etiquetas), "contorno": _puntos(e)})
        elif "highway" in etiquetas:
            caminos.append({"tipo": etiquetas["highway"], "puntos": _puntos(e)})
    if not perimetro:
        raise ValueError("Overpass no devolvió el perímetro del campus")
    edificios += [{"nombre": b["nombre"], "tipo": "trazado_a_mano", "niveles": None,
                   "contorno": b["contorno"]} for b in TRAZADOS_A_MANO]
    return {
        "fuente": "© OpenStreetMap contributors, ODbL (https://www.openstreetmap.org/copyright)",
        "descargado": date.today().isoformat(),
        "limites": {"sur": SUR, "oeste": OESTE, "norte": NORTE, "este": ESTE},
        "perimetro": perimetro, "edificios": edificios, "caminos": caminos,
    }


def a_texto(geometria: dict) -> str:
    """JSON con un edificio o camino por línea: se puede corregir a mano (p. ej. los pisos)."""
    def compacto(valor):
        return json.dumps(valor, ensure_ascii=False, separators=(",", ":"))

    lineas = [f' "{clave}": {compacto(geometria[clave])},'
              for clave in ("fuente", "descargado", "limites", "perimetro")]
    for clave in ("edificios", "caminos"):
        filas = ",\n  ".join(compacto(x) for x in geometria[clave])
        lineas.append(f' "{clave}": [\n  {filas}\n ],')
    return "{\n" + "\n".join(lineas).rstrip(",") + "\n}\n"


def main() -> None:
    respuesta = requests.post(URL, data={"data": CONSULTA}, headers={"User-Agent": USER_AGENT},
                              timeout=90)
    respuesta.raise_for_status()
    geometria = convertir(respuesta.json())
    SALIDA.write_text(a_texto(geometria), encoding="utf-8")
    print(f"{len(geometria['edificios'])} edificios y {len(geometria['caminos'])} caminos en {SALIDA}")


if __name__ == "__main__":
    main()
