"""El clima dibujado sobre el mapa de escritorio: luces de noche, nubes, lluvia, niebla y relámpagos.

Lee estado()["ambiente"] y la geometría de CentroControl; no decide nada del dominio.
"""
import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageTk

ALTURA_NUBES_M = 70
EXAGERAR_VIENTO = 4      # el viento real movería las nubes demasiado lento para verlo
MARGEN_NUBES_M = 150     # las nubes salen y entran por fuera del área visible
GOTAS_MAX = 160
CAIDA_PX_S = 650


def posicion_nube(nube: dict, viento: list[float], t: float, limites: list[float]) -> tuple[float, float]:
    """La nube avanza con el viento y, al salir del área, vuelve a entrar por el lado contrario."""
    x0, y0, x1, y1 = (limites[0] - MARGEN_NUBES_M, limites[1] - MARGEN_NUBES_M,
                      limites[2] + MARGEN_NUBES_M, limites[3] + MARGEN_NUBES_M)
    x = x0 + (nube["x"] - x0 + viento[0] * EXAGERAR_VIENTO * t) % (x1 - x0)
    y = y0 + (nube["y"] - y0 + viento[1] * EXAGERAR_VIENTO * t) % (y1 - y0)
    return x, y


def gotas(cantidad: int, ancho: int, alto: int, viento_px: float, t: float) -> list[tuple[float, float]]:
    """Posición de cada gota en pantalla: caen y se corren con el viento; vuelven a salir arriba."""
    azar = random.Random(3)
    puntos = []
    for _ in range(cantidad):
        u, v, rapidez = azar.random(), azar.random(), azar.uniform(0.8, 1.2)
        y = (v * alto + t * CAIDA_PX_S * rapidez) % alto
        x = (u * ancho + t * viento_px * rapidez) % ancho
        puntos.append((x, y))
    return puntos


def sprite_nube(semilla: int, ancho_px: int, alto_px: int, opacidad: float) -> Image.Image:
    """Nube algodonosa: varios círculos claros juntos y difuminados."""
    azar = random.Random(semilla)
    lado = max(8, ancho_px)
    img = Image.new("L", (lado, lado))
    d = ImageDraw.Draw(img)
    for _ in range(9):
        r = azar.uniform(0.12, 0.2) * lado  # lejos del borde: el difuminado no debe quedar cortado
        cx, cy = azar.uniform(0.35, 0.65) * lado, azar.uniform(0.38, 0.62) * lado
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    img = img.filter(ImageFilter.GaussianBlur(lado / 14)).resize((lado, max(4, alto_px)))
    color = Image.new("RGBA", img.size, (222, 233, 234, 0))
    color.putalpha(img.point(lambda a: int(a * opacidad)))
    return color


class CapaClima:

    def __init__(self, canvas, geo: dict):
        self._canvas, self._geo = canvas, geo
        self._sprites = {}  # (nube, opacidad) -> imagen, solo para el zoom actual
        self._escala_sprites = None
        self._velos = {}

    def luces(self, camara) -> None:
        """Ventanas encendidas de noche. No se mueven: van en la capa del fondo, que solo se redibuja
        cuando cambia la cámara."""
        c = self._canvas
        for x, y, z in self._geo["luces"]:
            sx, sy = camara.proyectar(x, y, z if camara.modo == "3D" else 0)
            c.create_oval(sx - 4, sy - 4, sx + 4, sy + 4, fill="#6b5a24", outline="", tags="fondo")
            c.create_oval(sx - 2, sy - 2, sx + 2, sy + 2, fill="#ffd36b", outline="", tags="fondo")

    def encima(self, ambiente: dict, camara, t: float) -> None:
        """Nubes, lluvia, niebla y relámpagos, encima de los robots."""
        c, ancho, alto = self._canvas, camara.ancho, camara.alto
        opacidad = round(ambiente["nubes"] * 0.6, 1)
        escala = (round(camara.escala, 2), camara.modo)
        if escala != self._escala_sprites:  # cambió el zoom: las imágenes viejas ya no sirven
            self._sprites.clear()
            self._escala_sprites = escala
        aplastar = 0.62 if camara.modo == "3D" else 1.0
        for i, nube in enumerate(self._geo["nubes"][:round(len(self._geo["nubes"]) * ambiente["nubes"])]):
            clave = (i, opacidad)
            if clave not in self._sprites:
                lado = int(nube["radio"] * 2 * camara.escala)
                self._sprites[clave] = ImageTk.PhotoImage(
                    sprite_nube(nube["semilla"], lado, int(lado * aplastar), opacidad))
            x, y = posicion_nube(nube, ambiente["viento"], t, self._geo["limites"])
            sx, sy = camara.proyectar(x, y, ALTURA_NUBES_M if camara.modo == "3D" else 0)
            c.create_image(sx, sy, image=self._sprites[clave], tags="vivo")
        if ambiente["lluvia"] > 0:
            viento_px = ambiente["viento"][0] * 25
            color = "#7fa8b0" if ambiente["noche"] else "#d4f1ee"
            largo = 14
            inclinacion = max(-0.8, min(0.8, viento_px / CAIDA_PX_S))
            for x, y in gotas(int(GOTAS_MAX * ambiente["lluvia"]), ancho, alto, viento_px, t):
                c.create_line(x, y, x + inclinacion * largo, y + largo, fill=color, tags="vivo")
        oscuro = round(ambiente["lluvia"] * 0.3 + ambiente["niebla"] * 0.45, 1)
        if oscuro > 0:  # cielo cargado y niebla: un velo encima de todo
            gris = (205, 218, 218) if ambiente["niebla"] > ambiente["lluvia"] else (6, 18, 24)
            c.create_image(0, 0, image=self._velo(ancho, alto, gris, oscuro), anchor="nw", tags="vivo")
        if ambiente["tormenta"] and int(t * 10) % 61 in (0, 2):  # un destello cada ~6 s
            c.create_image(0, 0, image=self._velo(ancho, alto, (235, 245, 255), 0.35), anchor="nw", tags="vivo")

    def _velo(self, ancho: int, alto: int, color: tuple, opacidad: float):
        clave = (ancho, alto, color, opacidad)
        if clave not in self._velos:
            self._velos[clave] = ImageTk.PhotoImage(Image.new("RGBA", (max(ancho, 1), max(alto, 1)),
                                                             (*color, int(255 * opacidad))))
        return self._velos[clave]
