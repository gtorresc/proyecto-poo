"""Mapa vectorial del campus en 2D (cenital) o 3D (oblicua, como Dispatch), sin tiles ni internet.

Dibuja la geometría de OSM que entrega CentroControl y lo que dice estado(): robots, rutas y balizas.
No decide nada: un clic en una baliza o un robot solo avisa a la ventana.
"""
import math

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from flota.gui import tema
from flota.gui.retratos import CARPETA

INTERVALO_MS = 50
ZOOM_MIN, ZOOM_MAX = 1.0, 4.0  # el mapa nunca sale del campus
INCLINACION_3D = (0.62, 0.78)  # cuánto se aplasta el suelo y cuánto sube la altura en la vista oblicua
LADO_RETRATO = 30
RADIO_CLIC = 18
ESPERA_ANILLO_S = 90  # el anillo de la baliza se vacía en este tiempo
CALLES = {"residential", "tertiary", "unclassified", "living_street"}
RESALTADO = (tema.RESALTADO["edificio"], tema.RESALTADO["pared"], tema.RESALTADO["arista"])


class Camara:
    """Proyecta metros del campus (x este, y norte, z altura) a píxeles de la pantalla."""

    def __init__(self, limites: list[float], campus: list[list[float]]):
        self._limites = limites  # [x_min, y_min, x_max, y_max] del área descargada
        xs, ys = [p[0] for p in campus], [p[1] for p in campus]
        self._tamano_campus = max(max(xs) - min(xs), max(ys) - min(ys))
        self.centro = [(max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2]
        self.modo, self.giro, self.zoom = "3D", 0, 1.0
        self.ancho, self.alto = 800, 600

    @property
    def _inclinacion(self) -> tuple[float, float]:
        return INCLINACION_3D if self.modo == "3D" else (1.0, 0.0)

    @property
    def escala(self) -> float:
        """Píxeles por metro: con zoom 1 entra todo el campus."""
        return self.zoom * min(self.ancho, self.alto / self._inclinacion[0]) / self._tamano_campus

    def rotar(self, x: float, y: float) -> tuple[float, float]:
        """Coordenadas relativas al centro, giradas como las ve la cámara."""
        a = math.radians(self.giro)
        dx, dy = x - self.centro[0], y - self.centro[1]
        return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)

    def proyectar(self, x: float, y: float, z: float = 0) -> tuple[float, float]:
        xr, yr = self.rotar(x, y)
        suelo, altura = self._inclinacion
        return self.ancho / 2 + xr * self.escala, self.alto / 2 - (yr * suelo + z * altura) * self.escala

    def profundidad(self, x: float, y: float) -> float:
        """Más grande = más lejos (arriba en pantalla): se dibuja primero."""
        return self.rotar(x, y)[1]

    def mover(self, dx_px: float, dy_px: float) -> None:
        """Arrastrar el mapa; el centro no sale del área del campus."""
        a = math.radians(self.giro)
        xr, yr = -dx_px / self.escala, dy_px / (self.escala * self._inclinacion[0])
        x = self.centro[0] + xr * math.cos(a) + yr * math.sin(a)
        y = self.centro[1] - xr * math.sin(a) + yr * math.cos(a)
        x_min, y_min, x_max, y_max = self._limites
        self.centro = [min(max(x, x_min), x_max), min(max(y, y_min), y_max)]

    def acercar(self, factor: float) -> None:
        self.zoom = min(max(self.zoom * factor, ZOOM_MIN), ZOOM_MAX)

    def girar(self) -> None:
        self.giro = (self.giro + 90) % 360

    def alternar(self) -> None:
        self.modo = "2D" if self.modo == "3D" else "3D"


def caras_visibles(contorno: list, rotado: list) -> list[tuple]:
    """Paredes que miran a la cámara (normal exterior hacia abajo en pantalla), de la más lejana a la más cercana."""
    area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(rotado, rotado[1:] + rotado[:1]))
    caras = []
    for (a, b), (ra, rb) in zip(zip(contorno, contorno[1:] + contorno[:1]), zip(rotado, rotado[1:] + rotado[:1])):
        normal_y = -(rb[0] - ra[0]) if area > 0 else rb[0] - ra[0]
        if normal_y < 0:
            caras.append(((ra[1] + rb[1]) / 2, a, b))
    return [(a, b) for _, a, b in sorted(caras, reverse=True)]


def _retrato_redondo(id_robot: str, color: str):
    """Retrato circular con aro de color, o None si todavía no está guardado (el mapa no usa la red)."""
    archivo = CARPETA / f"{id_robot}.png"
    if not archivo.exists():
        return None
    lado = LADO_RETRATO
    img = Image.new("RGBA", (lado, lado))
    ImageDraw.Draw(img).ellipse((0, 0, lado - 1, lado - 1), fill="#2f5a58", outline=color, width=3)
    cara = Image.open(archivo).convert("RGBA").resize((lado - 6, lado - 6))
    mascara = Image.new("L", cara.size)
    ImageDraw.Draw(mascara).ellipse((0, 0, *cara.size), fill=255)
    img.paste(cara, (3, 3), Image.composite(cara, Image.new("RGBA", cara.size), mascara))
    return ImageTk.PhotoImage(img)


class PanelMapa(ctk.CTkFrame):

    def __init__(self, master, centro, al_completar, al_elegir_baliza, al_elegir_robot):
        super().__init__(master, fg_color=tema.BISEL, corner_radius=4)
        self._centro, self._al_completar = centro, al_completar
        self._al_elegir_baliza, self._al_elegir_robot = al_elegir_baliza, al_elegir_robot
        self._geo = centro.geometria()
        self.camara = Camara(self._geo["limites"], self._geo["perimetro"])
        self._paleta, self._resaltados = tema.DIA, frozenset()
        self._retratos, self._en_pantalla = {}, {"balizas": [], "robots": []}
        self._arrastre, self._lineas = None, None
        self.canvas = ctk.CTkCanvas(self, bg=tema.DIA["fondo_mapa"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)
        self._botones()
        self.canvas.bind("<Configure>", self._al_redimensionar)
        self.canvas.bind("<ButtonPress-1>", lambda e: setattr(self, "_arrastre", (e.x, e.y, e.x, e.y)))
        self.canvas.bind("<B1-Motion>", self._arrastrar)
        self.canvas.bind("<ButtonRelease-1>", self._soltar)
        self.canvas.bind("<MouseWheel>", lambda e: self._camara(self.camara.acercar, 1.2 if e.delta > 0 else 1 / 1.2))
        self._ciclo()

    def _botones(self) -> None:
        columna = ctk.CTkFrame(self, fg_color="transparent")
        columna.place(relx=1, rely=1, x=-12, y=-12, anchor="se")
        for texto, accion in [("[TAB] 2D/3D", self.alternar), ("[R] GIRAR", self.girar),
                              ("+", lambda: self._camara(self.camara.acercar, 1.4)),
                              ("-", lambda: self._camara(self.camara.acercar, 1 / 1.4))]:
            ctk.CTkButton(columna, text=texto, width=110, height=26, font=tema.fuente(12),
                          command=accion).pack(pady=2)

    # --- Cámara ------------------------------------------------------------------
    def alternar(self) -> None:
        self._camara(self.camara.alternar)

    def girar(self) -> None:
        self._camara(self.camara.girar)

    def _camara(self, accion, *args) -> None:
        accion(*args)
        self._dibujar_fondo()

    def _al_redimensionar(self, evento) -> None:
        self.camara.ancho, self.camara.alto = evento.width, evento.height
        self._lineas = self._scanlines(evento.width, evento.height)
        self._dibujar_fondo()

    def _arrastrar(self, e) -> None:
        x0, y0, xa, ya = self._arrastre
        self.camara.mover(e.x - xa, e.y - ya)
        self._arrastre = (x0, y0, e.x, e.y)
        self._dibujar_fondo()

    def _soltar(self, e) -> None:
        x0, y0, _, _ = self._arrastre
        if math.dist((x0, y0), (e.x, e.y)) < 5:  # fue un clic, no un arrastre
            self._clic(e.x, e.y)

    def _clic(self, sx: float, sy: float) -> None:
        for tipo, avisar in (("balizas", self._al_elegir_baliza), ("robots", self._al_elegir_robot)):
            cerca = [(math.dist((sx, sy), pos), ident) for ident, pos in self._en_pantalla[tipo]]
            if cerca and min(cerca)[0] <= RADIO_CLIC:
                avisar(min(cerca)[1])
                return

    # --- Fondo: suelo, caminos y edificios (solo cuando cambia la cámara o el resaltado) ------
    def _dibujar_fondo(self) -> None:
        c, cam, p = self.canvas, self.camara, self._paleta
        c.delete("fondo")
        c.configure(bg=p["fondo_mapa"])
        plano = lambda puntos: [v for x, y in puntos for v in cam.proyectar(x, y)]
        c.create_polygon(plano(self._geo["perimetro"]), fill=p["campus"], outline=p["sendero"], width=2,
                         tags="fondo")
        for camino in self._geo["caminos"]:
            calle = camino["tipo"] in CALLES
            c.create_line(plano(camino["puntos"]), fill=p["calle"] if calle else p["sendero"],
                          width=max(1, cam.escala * (6 if calle else 1.6)), capstyle="round", tags="fondo")
        edificios = self._geo["edificios"]
        for i in sorted(range(len(edificios)), reverse=True, key=lambda i: cam.profundidad(*edificios[i]["contorno"][0])):
            self._dibujar_edificio(edificios[i], i in self._resaltados)
        c.create_text(cam.ancho - 8, 8, text=self._geo["fuente"].split(",")[0], anchor="ne",
                      fill=p["arista"], font=(tema.MONO, 9), tags="fondo")
        c.tag_lower("fondo")

    def _dibujar_edificio(self, edificio: dict, resaltado: bool) -> None:
        c, cam, p = self.canvas, self.camara, self._paleta
        techo, pared, arista = (RESALTADO if resaltado else
                                (p["edificio"], p["pared"], p["arista"]) if edificio["en_campus"]
                                else (p["ciudad"], p["pared_ciudad"], p["arista_ciudad"]))
        contorno, alto = edificio["contorno"], edificio["altura"] if cam.modo == "3D" else 0
        if alto:
            for a, b in caras_visibles(contorno, [cam.rotar(x, y) for x, y in contorno]):
                c.create_polygon(*cam.proyectar(*a), *cam.proyectar(*b), *cam.proyectar(*b, alto),
                                 *cam.proyectar(*a, alto), fill=pared, outline=arista, tags="fondo")
        c.create_polygon([v for x, y in contorno for v in cam.proyectar(x, y, alto)], fill=techo, outline=arista,
                         width=1.5 if edificio["en_campus"] else 1, tags="fondo")

    @staticmethod
    def _scanlines(ancho: int, alto: int):
        """Líneas finas semitransparentes encima de todo, como un monitor CRT."""
        img = Image.new("RGBA", (max(ancho, 1), max(alto, 1)))
        dibujo = ImageDraw.Draw(img)
        for y in range(0, alto, 3):
            dibujo.line((0, y, ancho, y), fill=(0, 0, 0, 34))
        return ImageTk.PhotoImage(img)

    # --- Capa viva: robots, rutas y balizas (cada 50 ms) ----------------------------------
    def _ciclo(self) -> None:
        if self._centro.tick():
            self._al_completar()
        estado = self._centro.estado()
        paleta = tema.NOCHE if estado["clima"].get("es_de_dia") is False else tema.DIA
        resaltados = frozenset(b["edificio"] for b in estado["balizas"] if b["edificio"] is not None)
        if paleta is not self._paleta or resaltados != self._resaltados:
            self._paleta, self._resaltados = paleta, resaltados
            self._dibujar_fondo()
        self._dibujar_vivo(estado)
        self.after(INTERVALO_MS, self._ciclo)

    def _dibujar_vivo(self, estado: dict) -> None:
        c, cam = self.canvas, self.camara
        c.delete("vivo")
        for r in estado["robots"]:
            if len(r["recorrido"]) >= 2:
                c.create_line([v for x, y in r["recorrido"] for v in cam.proyectar(x, y)],
                              fill=tema.FRANJA[r["franja"]], width=3, dash=(6, 4), tags="vivo")
        self._en_pantalla = {"balizas": [], "robots": []}
        for b in estado["balizas"]:
            alto = self._geo["edificios"][b["edificio"]]["altura"] if b["edificio"] is not None else 0
            sx, sy = cam.proyectar(b["x"], b["y"], (alto if cam.modo == "3D" else 0) + 4)
            queda = max(0.0, 1 - b["espera_s"] / ESPERA_ANILLO_S)
            c.create_oval(sx - 15, sy - 15, sx + 15, sy + 15, fill=tema.PANEL, outline="", tags="vivo")
            if queda > 0:
                c.create_arc(sx - 15, sy - 15, sx + 15, sy + 15, start=90, extent=-359.9 * queda, style="arc",
                             outline="#f3efe4", width=3, tags="vivo")
            c.create_oval(sx - 11, sy - 11, sx + 11, sy + 11, fill=tema.ALERTA, outline="", tags="vivo")
            c.create_text(sx, sy, text="!", fill="#ffffff", font=(tema.TITULO, 14), tags="vivo")
            self._en_pantalla["balizas"].append((b["id"], (sx, sy)))
        for r in sorted(estado["robots"], key=lambda r: -cam.profundidad(r["x"], r["y"])):
            z = r["z"] if cam.modo == "3D" else 0
            if z:  # sombra en el suelo: así se nota que el dron vuela
                gx, gy = cam.proyectar(r["x"], r["y"])
                c.create_oval(gx - 8, gy - 3, gx + 8, gy + 3, fill="#0b2a28", outline="", tags="vivo")
            sx, sy = cam.proyectar(r["x"], r["y"], z)
            self._dibujar_robot(r, sx, sy)
            self._en_pantalla["robots"].append((r["id"], (sx, sy)))
        if self._lineas:
            c.create_image(0, 0, image=self._lineas, anchor="nw", tags="vivo")

    def _dibujar_robot(self, r: dict, sx: float, sy: float) -> None:
        c, color = self.canvas, tema.FRANJA[r["franja"]]
        clave = (r["id"], color)
        if self._retratos.get(clave) is None:
            self._retratos[clave] = _retrato_redondo(r["id"], color)  # None: aún no está guardado
        if self._retratos[clave] is None:
            c.create_oval(sx - 10, sy - 10, sx + 10, sy + 10, fill=color, outline="#f3efe4", width=2, tags="vivo")
        else:
            c.create_image(sx, sy, image=self._retratos[clave], tags="vivo")
        c.create_text(sx, sy + LADO_RETRATO / 2 + 7, text=r["id"], fill="#f3efe4", font=(tema.TITULO, 10),
                      tags="vivo")
