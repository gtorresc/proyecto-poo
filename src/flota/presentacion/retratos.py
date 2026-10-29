"""Retratos de los robots para la plantilla de la web: RoboHash (CC-BY), guardados en recursos/retratos.

Se descargan una vez por id. Sin internet, se dibuja un ícono por tipo de robot.
"""
from pathlib import Path

import requests
from PIL import Image, ImageDraw

from flota.presentacion.tema import RECURSOS

CARPETA = RECURSOS / "retratos"
URL = "https://robohash.org/{id}.png?set=set1&size=200x200"
TIMEOUT_S = 5
USER_AGENT = "FlotaRobotsUdeM/1.0 (proyecto academico de POO)"


def retrato(id_robot: str, tipo: str, carpeta: Path = CARPETA) -> Image.Image:
    """Llamar fuera del hilo de la página: la primera vez puede tardar hasta el timeout."""
    archivo = carpeta / f"{id_robot}.png"
    if not archivo.exists():
        try:
            respuesta = requests.get(URL.format(id=id_robot), timeout=TIMEOUT_S,
                                     headers={"User-Agent": USER_AGENT})
            respuesta.raise_for_status()
            if not respuesta.headers.get("content-type", "").startswith("image/"):
                raise ValueError("RoboHash no devolvió una imagen")
            carpeta.mkdir(parents=True, exist_ok=True)
            archivo.write_bytes(respuesta.content)
        except (requests.RequestException, ValueError):
            return icono(tipo)
    return Image.open(archivo).convert("RGBA")


def icono(tipo: str) -> Image.Image:
    """Silueta simple por tipo: ruedas, orugas o hélices."""
    img = Image.new("RGBA", (200, 200))
    d = ImageDraw.Draw(img)
    claro = "#b9fff2"
    d.rounded_rectangle((50, 60, 150, 130), 12, outline=claro, width=6)  # cuerpo
    d.ellipse((80, 80, 95, 95), fill=claro)
    d.ellipse((105, 80, 120, 95), fill=claro)
    if tipo == "Dron":
        for x in (30, 140):
            d.line((x, 45, x + 30, 45), fill=claro, width=6)
            d.line((x + 15, 45, x + 15, 65), fill=claro, width=4)
    elif tipo == "Orugas":
        d.rounded_rectangle((40, 140, 160, 170), 15, outline=claro, width=6)
    else:
        for x in (65, 135):
            d.ellipse((x - 16, 135, x + 16, 167), outline=claro, width=6)
    return img
