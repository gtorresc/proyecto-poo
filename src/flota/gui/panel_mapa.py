"""Mapa del campus en 2D (cenital) o 3D (oblicua), en tres vistas: DESPACHO, CALLES y SATÉLITE.

DESPACHO se dibuja con la geometría de OSM, sin internet. CALLES y SATÉLITE ponen debajo un mosaico
de imágenes reales (gui/mosaico.py). Encima va lo que dice estado(): robots, rutas y balizas.
No decide nada: un clic en una baliza o un robot solo avisa a la ventana.
"""
import math
import threading
import time

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageEnhance, ImageTk

from flota.gui import tema
from flota.gui.capa_clima import CapaClima
from flota.gui.centro_control import dentro
from flota.gui.mosaico import CAPAS, color_techo, mascara_bordes, mosaico
from flota.gui.retratos import CARPETA

INTERVALO_MS = 50
ZOOM_MIN, ZOOM_MAX = 1.0, 4.0  # el mapa nunca sale del campus
INCLINACION_3D = (0.62, 0.78)  # cuánto se aplasta el suelo y cuánto sube la altura en la vista oblicua
LADO_RETRATO = 30
RADIO_CLIC = 18
ESPERA_ANILLO_S = 90  # el anillo de la baliza se vacía en este tiempo
CALLES = {"residential", "tertiary", "unclassified", "living_street"}
RESALTADO = (tema.RESALTADO["edificio"], tema.RESALTADO["pared"], tema.RESALTADO["arista"])
VISTAS = ["despacho", "calles", "satelite"]
NOMBRE_VISTA = {"despacho": "DESPACHO", "calles": "CALLES", "satelite": "SATÉLITE"}
EDIFICIO_CALLES = ("#ece9e4", "#d3cdc4", "#b3ab9f")  # techo, pared y arista, como los edificios 3D de un mapa
AVISO_S = 4
ZOOM_MIN_REAL = 1.4   # en las vistas realistas no se aleja tanto: el mosaico solo cubre el campus
PANEO_REAL = 0.6      # y el centro solo se mueve dentro del 60 % central del mosaico


class Camara:
    """Proyecta metros del campus (x este, y norte, z altura) a píxeles de la pantalla."""

    def __init__(self, limites: list[float], campus: list[list[float]]):
        self._limites = limites  # [x_min, y_min, x_max, y_max] del área descargada
        self.limites_paneo = limites  # por dónde puede ir el centro; las vistas realistas lo achican
        self.zoom_min = ZOOM_MIN
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
        self.centro = [x, y]
        self._limitar()

    def acercar(self, factor: float) -> None:
        self.zoom = min(max(self.zoom * factor, self.zoom_min), ZOOM_MAX)

    def restringir(self, caja=None) -> None:
        """Sin caja: los límites de siempre. Con la caja del mosaico: zoom mínimo más alto y paneo al centro."""
        if caja is None:
            self.limites_paneo, self.zoom_min = self._limites, ZOOM_MIN
        else:
            x0, y0, x1, y1 = caja
            mx, my = (x1 - x0) * (1 - PANEO_REAL) / 2, (y1 - y0) * (1 - PANEO_REAL) / 2
            self.limites_paneo, self.zoom_min = [x0 + mx, y0 + my, x1 - mx, y1 - my], ZOOM_MIN_REAL
        self.zoom = max(self.zoom, self.zoom_min)
        self._limitar()

    def _limitar(self) -> None:
        x_min, y_min, x_max, y_max = self.limites_paneo
        self.centro = [min(max(self.centro[0], x_min), x_max), min(max(self.centro[1], y_min), y_max)]

    def girar(self) -> None:
        self.giro = (self.giro + 90) % 360

    def alternar(self) -> None:
        self.modo = "2D" if self.modo == "3D" else "3D"

    def afin_suelo(self, caja: list[float], tamano: tuple[int, int]) -> tuple:
        """Coeficientes de Image.transform(AFFINE): de cada píxel de pantalla al píxel del mosaico.

        El suelo (z = 0) se proyecta con una transformación afín, así que la foto se puede deformar
        a la vista 2D, a la 3D o girada sin perder la alineación con los edificios."""
        x0, y0, x1, y1 = caja

        def pantalla(u, v):
            return self.proyectar(x0 + u * (x1 - x0) / tamano[0], y1 - v * (y1 - y0) / tamano[1])
        s0, su, sv = pantalla(0, 0), pantalla(1, 0), pantalla(0, 1)
        ux, uy, vx, vy = su[0] - s0[0], su[1] - s0[1], sv[0] - s0[0], sv[1] - s0[1]
        det = ux * vy - vx * uy
        a, b, d, e = vy / det, -vx / det, -uy / det, ux / det
        return a, b, -(a * s0[0] + b * s0[1]), d, e, -(d * s0[0] + e * s0[1])


def caras_visibles(contorno: list, rotado: list) -> list[tuple]:
    """Paredes que miran a la cámara (normal exterior hacia abajo en pantalla), de la más lejana a la más cercana."""
    area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(rotado, rotado[1:] + rotado[:1]))
    caras = []
    for (a, b), (ra, rb) in zip(zip(contorno, contorno[1:] + contorno[:1]), zip(rotado, rotado[1:] + rotado[:1])):
        normal_y = -(rb[0] - ra[0]) if area > 0 else rb[0] - ra[0]
        if normal_y < 0:
            caras.append(((ra[1] + rb[1]) / 2, a, b))
    return [(a, b) for _, a, b in sorted(caras, reverse=True)]


def edificio_bajo(camara: Camara, edificios: list[dict], sx: float, sy: float):
    """Índice del edificio cuyo techo está bajo el punto de pantalla; el más cercano a la cámara gana."""
    for i in sorted(range(len(edificios)), key=lambda i: camara.profundidad(*edificios[i]["contorno"][0])):
        z = edificios[i]["altura"] if camara.modo == "3D" else 0
        techo = [camara.proyectar(x, y, z)[::-1] for x, y in edificios[i]["contorno"]]  # dentro() usa (y, x)
        if dentro((sy, sx), techo):
            return i
    return None


def oscurecer(color: str, factor: float) -> str:
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{int(v * factor):02x}" for v in (r, g, b))


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
        self.vista = "despacho"         # la que pidió el operador
        self._mosaicos = {}             # capa -> (imagen, caja, colores de techo), o None si no se pudo bajar
        self._aviso = None              # (texto, hasta) en la esquina del mapa
        self._foto_suelo = None
        self._vista_dibujada = None
        self.canvas = ctk.CTkCanvas(self, bg=tema.DIA["fondo_mapa"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)
        self._botones()
        self._clima = CapaClima(self.canvas, self._geo)
        self.canvas.bind("<Configure>", self._al_redimensionar)
        self.canvas.bind("<Motion>", self._sobre)
        self.canvas.bind("<Leave>", lambda _: self.canvas.delete("etiqueta"))
        self.canvas.bind("<ButtonPress-1>", lambda e: setattr(self, "_arrastre", (e.x, e.y, e.x, e.y)))
        self.canvas.bind("<B1-Motion>", self._arrastrar)
        self.canvas.bind("<ButtonRelease-1>", self._soltar)
        self.canvas.bind("<MouseWheel>", lambda e: self._camara(self.camara.acercar, 1.2 if e.delta > 0 else 1 / 1.2))
        self._ciclo()

    def _botones(self) -> None:
        columna = ctk.CTkFrame(self, fg_color="transparent")
        columna.place(relx=1, rely=1, x=-12, y=-12, anchor="se")
        for texto, accion in [("[V] VISTA", self.cambiar_vista), ("[TAB] 2D/3D", self.alternar),
                              ("[R] GIRAR", self.girar),
                              ("+", lambda: self._camara(self.camara.acercar, 1.4)),
                              ("-", lambda: self._camara(self.camara.acercar, 1 / 1.4))]:
            ctk.CTkButton(columna, text=texto, width=110, height=26, font=tema.fuente(12),
                          command=accion).pack(pady=2)

    # --- Cámara ------------------------------------------------------------------
    def alternar(self) -> None:
        self._camara(self.camara.alternar)

    def girar(self) -> None:
        self._camara(self.camara.girar)

    # --- Vistas -----------------------------------------------------------------
    def cambiar_vista(self) -> None:
        """DESPACHO, CALLES y SATÉLITE en ronda. El mosaico se baja en un hilo la primera vez."""
        self.vista = VISTAS[(VISTAS.index(self.vista) + 1) % len(VISTAS)]
        if self.vista != "despacho" and self.vista not in self._mosaicos:
            self._avisar("cargando mapa...")
            threading.Thread(target=self._bajar_mosaico, args=(self.vista,), daemon=True).start()
        else:
            self._avisar(f"vista {NOMBRE_VISTA[self.vista]}")
        self._dibujar_fondo()

    def _bajar_mosaico(self, capa: str) -> None:
        resultado = mosaico(capa)
        if resultado is not None:
            imagen, caja = resultado
            colores = [color_techo(imagen, caja, e["contorno"]) for e in self._geo["edificios"]]
            difuminada = imagen.convert("RGBA")
            difuminada.putalpha(mascara_bordes(imagen.size))  # los bordes se pierden en la neblina
            resultado = (difuminada, caja, colores)
        self._mosaicos[capa] = resultado  # el ciclo de la ventana lo nota y redibuja

    def _vista_activa(self) -> str:
        """Hasta que el mosaico esté listo (o si no se pudo bajar) se ve DESPACHO."""
        return self.vista if self._mosaicos.get(self.vista) else "despacho"

    def _ajustar_camara(self, vista: str) -> None:
        self.camara.restringir(self._mosaicos[vista][1] if vista != "despacho" else None)

    def _avisar(self, texto: str) -> None:
        self._aviso = (texto, time.monotonic() + AVISO_S)

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
        vista = self._vista_activa()
        if vista != "despacho":
            self._dibujar_fondo_real(vista)
            c.tag_lower("fondo")
            return
        c.configure(bg=p["fondo_mapa"])
        plano = lambda puntos: [v for x, y in puntos for v in cam.proyectar(x, y)]
        c.create_polygon(plano(self._geo["perimetro"]), fill=p["campus"], outline=p["sendero"], width=2,
                         tags="fondo")
        for camino in self._geo["caminos"]:
            calle = camino["tipo"] in CALLES
            c.create_line(plano(camino["puntos"]), fill=p["calle"] if calle else p["sendero"],
                          width=max(1, cam.escala * (6 if calle else 1.6)), capstyle="round", tags="fondo")
        edificios = self._geo["edificios"]
        for i in self._orden_edificios():
            e = edificios[i]
            colores = (RESALTADO if i in self._resaltados else
                       (p["edificio"], p["pared"], p["arista"]) if e["en_campus"]
                       else (p["ciudad"], p["pared_ciudad"], p["arista_ciudad"]))
            self._dibujar_edificio(e, colores, 1.5 if e["en_campus"] else 1)
        self._credito(self._geo["fuente"].split(",")[0], p["arista"])
        if p is tema.NOCHE:
            self._clima.luces(cam)
        c.tag_lower("fondo")

    def _orden_edificios(self) -> list[int]:
        edificios, cam = self._geo["edificios"], self.camara
        return sorted(range(len(edificios)), reverse=True,
                      key=lambda i: cam.profundidad(*edificios[i]["contorno"][0]))

    def _credito(self, texto: str, color: str) -> None:
        self.canvas.create_text(self.camara.ancho - 8, 8, text=texto, anchor="ne", fill=color,
                                font=(tema.MONO, 9), tags="fondo")

    def _dibujar_fondo_real(self, vista: str) -> None:
        """La foto (o el mapa de calles) deformada a la cámara y, en 3D, los edificios con su color real."""
        c, cam = self.canvas, self.camara
        imagen, caja, colores = self._mosaicos[vista]
        noche = self._paleta is tema.NOCHE
        neblina = tema.NEBLINA[vista][1 if noche else 0]
        c.configure(bg=neblina)
        tamano = (max(1, cam.ancho), max(1, cam.alto))
        foto = imagen.transform(tamano, Image.AFFINE, cam.afin_suelo(caja, imagen.size), resample=Image.BILINEAR,
                                fillcolor=(0, 0, 0, 0))
        suelo = Image.alpha_composite(Image.new("RGBA", tamano, neblina), foto).convert("RGB")
        if noche:  # de noche la foto se oscurece y se enfría, para que se vean las luces
            suelo = Image.blend(ImageEnhance.Brightness(suelo).enhance(0.4),
                                Image.new("RGB", suelo.size, "#0b1a33"), 0.25)
        self._foto_suelo = ImageTk.PhotoImage(suelo)
        c.create_image(0, 0, image=self._foto_suelo, anchor="nw", tags="fondo")
        edificios = self._geo["edificios"]
        for i in self._orden_edificios():
            if cam.modo == "2D":
                if i in self._resaltados:  # en 2D la imagen ya muestra los edificios: solo el contorno naranja
                    c.create_polygon([v for x, y in edificios[i]["contorno"] for v in cam.proyectar(x, y)],
                                     fill="", outline=tema.ALERTA, width=3, tags="fondo")
                continue
            if i in self._resaltados:
                tono = RESALTADO
            else:
                tono = ((colores[i], oscurecer(colores[i], 0.72), oscurecer(colores[i], 0.5)) if vista == "satelite"
                        else EDIFICIO_CALLES)
                if noche:
                    tono = tuple(oscurecer(t, 0.45) for t in tono)
            self._dibujar_edificio(edificios[i], tono, 1)
        self._credito(CAPAS[vista]["credito"], "#f3efe4")
        if noche:
            self._clima.luces(cam)

    def _dibujar_edificio(self, edificio: dict, colores: tuple, grosor: float) -> None:
        c, cam = self.canvas, self.camara
        techo, pared, arista = colores
        contorno, alto = edificio["contorno"], edificio["altura"] if cam.modo == "3D" else 0
        if alto:
            for a, b in caras_visibles(contorno, [cam.rotar(x, y) for x, y in contorno]):
                c.create_polygon(*cam.proyectar(*a), *cam.proyectar(*b), *cam.proyectar(*b, alto),
                                 *cam.proyectar(*a, alto), fill=pared, outline=arista, tags="fondo")
        c.create_polygon([v for x, y in contorno for v in cam.proyectar(x, y, alto)], fill=techo, outline=arista,
                         width=grosor, tags="fondo")

    def _sobre(self, e) -> None:
        """Al pasar el mouse por un edificio con nombre, lo muestra en una etiqueta junto al cursor."""
        c = self.canvas
        c.delete("etiqueta")
        i = edificio_bajo(self.camara, self._geo["edificios"], e.x, e.y)
        nombre = self._geo["edificios"][i]["nombre"] if i is not None else None
        if not nombre:  # fuera de los edificios, o un edificio sin nombre en OSM
            return
        texto = c.create_text(e.x + 14, e.y - 16, text=nombre, anchor="sw", fill="#f3efe4",
                              font=(tema.MONO, 11), tags="etiqueta")
        x0, y0, x1, y1 = c.bbox(texto)
        if x1 + 8 > self.camara.ancho:  # no se sale por la derecha: va al otro lado del cursor
            c.move(texto, -(x1 - x0) - 28, 0)
            x0, y0, x1, y1 = c.bbox(texto)
        c.create_rectangle(x0 - 6, y0 - 3, x1 + 6, y1 + 3, fill="#0c1a1c", outline=tema.ALERTA, tags="etiqueta")
        c.tag_raise(texto)

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
        try:
            self._refrescar()
        finally:  # un error en un cuadro no debe detener la animación ni las siguientes entregas
            self.after(INTERVALO_MS, self._ciclo)

    def _refrescar(self) -> None:
        if self._centro.tick():
            self._al_completar()
        estado = self._centro.estado()
        paleta = tema.NOCHE if estado["clima"].get("es_de_dia") is False else tema.DIA
        resaltados = frozenset(b["edificio"] for b in estado["balizas"] if b["edificio"] is not None)
        if self.vista in self._mosaicos and self._mosaicos[self.vista] is None:
            del self._mosaicos[self.vista]  # se reintenta la próxima vez que se pida
            self.vista = "despacho"
            self._avisar("vista realista sin conexion: se usa DESPACHO")
        vista = self._vista_activa()
        if paleta is not self._paleta or resaltados != self._resaltados or vista != self._vista_dibujada:
            if vista != self._vista_dibujada:
                self._ajustar_camara(vista)
            self._paleta, self._resaltados, self._vista_dibujada = paleta, resaltados, vista
            self._dibujar_fondo()
        self._dibujar_vivo(estado)

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
        self._clima.encima(estado["ambiente"], cam, time.monotonic())
        if self._aviso and time.monotonic() < self._aviso[1]:
            c.create_text(12, 12, text=self._aviso[0].upper(), anchor="nw", fill=tema.ALERTA,
                          font=(tema.TITULO, 13), tags="vivo")
        if self._lineas:
            c.create_image(0, 0, image=self._lineas, anchor="nw", tags="vivo")
        c.tag_raise("etiqueta")

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
