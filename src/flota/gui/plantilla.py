"""Plantilla de robots (fila de tarjetas, como el roster de Dispatch) y ficha con el radar."""
import math
import threading

import customtkinter as ctk

from flota.gui import tema
from flota.gui.retratos import icono, retrato

LADO_RETRATO = 92
EJES = [("velocidad", "VEL"), ("carga", "CARGA"), ("autonomia", "AUTON"), ("economia", "ECON"),
        ("alcance", "ALCANCE")]


def puntos_radar(valores: dict, cx: float, cy: float, radio: float) -> list[tuple[float, float]]:
    """Vértices del pentágono: un eje por atributo, empezando arriba y en sentido horario."""
    puntos = []
    for i, (eje, _) in enumerate(EJES):
        angulo = -math.pi / 2 + i * 2 * math.pi / len(EJES)
        r = radio * max(0.05, min(1.0, valores[eje]))  # 0.05: que un eje vacío no colapse el dibujo
        puntos.append((cx + r * math.cos(angulo), cy + r * math.sin(angulo)))
    return puntos


class TarjetaRobot(ctk.CTkFrame):

    def __init__(self, master, robot: dict, al_elegir):
        super().__init__(master, fg_color="#20393c", border_width=2, border_color="#3d5a5e", corner_radius=3)
        self.id = robot["id"]
        self._franja = ctk.CTkLabel(self, text="", height=20, corner_radius=0, font=tema.fuente(13, True),
                                    text_color="#ffffff")
        self._franja.pack(fill="x", padx=2, pady=(2, 0))
        self._imagen = ctk.CTkImage(icono(robot["tipo"]), size=(LADO_RETRATO, LADO_RETRATO))
        self._foto = ctk.CTkLabel(self, image=self._imagen, text="", fg_color="#2f5a58", corner_radius=0)
        self._foto.pack(fill="x", padx=2)
        ctk.CTkLabel(self, text=robot["id"], font=tema.fuente(18, True), text_color="#f3efe4").pack(pady=(2, 0))
        ctk.CTkLabel(self, text=robot["tipo"].upper(), font=tema.fuente(11), text_color=tema.TEXTO_BARRA,
                     height=12).pack()
        self._bateria = ctk.CTkProgressBar(self, height=6, width=110)
        self._bateria.pack(padx=8, pady=(4, 8))
        for widget in (self, self._franja, self._foto):
            widget.bind("<Button-1>", lambda _: al_elegir(self.id))

    def poner_retrato(self, imagen) -> None:
        self._imagen.configure(light_image=imagen, dark_image=imagen)

    def refrescar(self, robot: dict, elegida: bool) -> None:
        self._franja.configure(text=tema.ETIQUETA_FRANJA[robot["franja"]], fg_color=tema.FRANJA[robot["franja"]])
        self._bateria.set(robot["bateria"] / 100)
        self._bateria.configure(progress_color=tema.bateria_color(robot["bateria"]))
        self.configure(border_color=tema.ALERTA if elegida else "#3d5a5e")


class Plantilla(ctk.CTkFrame):
    """Una tarjeta por robot. Un clic avisa a la ventana, que despacha o abre la ficha del robot."""

    def __init__(self, master, al_elegir):
        super().__init__(master, fg_color="transparent")
        self._al_elegir = al_elegir
        self._tarjetas: dict[str, TarjetaRobot] = {}
        self._retratos_listos: dict[str, object] = {}  # los escribe un hilo; se aplican en refrescar
        self.elegido = None

    def refrescar(self, estado: dict) -> None:
        for robot in estado["robots"]:
            if robot["id"] not in self._tarjetas:  # también los robots que se agreguen en vivo
                tarjeta = TarjetaRobot(self, robot, self._al_elegir)
                tarjeta.pack(side="left", padx=6, pady=4)
                self._tarjetas[robot["id"]] = tarjeta
                threading.Thread(target=self._cargar_retrato, args=(robot["id"], robot["tipo"]),
                                 daemon=True).start()
            if robot["id"] in self._retratos_listos:
                self._tarjetas[robot["id"]].poner_retrato(self._retratos_listos.pop(robot["id"]))
            self._tarjetas[robot["id"]].refrescar(robot, robot["id"] == self.elegido)

    def _cargar_retrato(self, id_robot: str, tipo: str) -> None:
        self._retratos_listos[id_robot] = retrato(id_robot, tipo)


class FichaRobot(ctk.CTkFrame):
    """Ficha de papel con el radar pentagonal del robot elegido."""

    def __init__(self, master, al_cerrar):
        super().__init__(master, fg_color=tema.PAPEL, corner_radius=2, border_width=2, border_color="#3d5a5e")
        self._titulo = ctk.CTkLabel(self, text="", height=26, corner_radius=0, font=tema.fuente(16, True),
                                    text_color="#ffffff", anchor="w")
        self._titulo.pack(fill="x", padx=2, pady=(2, 0))
        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(padx=10, pady=6)
        self._radar = ctk.CTkCanvas(cuerpo, width=190, height=180, bg=tema.PAPEL, highlightthickness=0)
        self._radar.pack(side="left")
        self._datos = ctk.CTkLabel(cuerpo, text="", justify="left", anchor="nw", text_color=tema.TINTA,
                                   font=tema.fuente(13), width=170)
        self._datos.pack(side="left", fill="y", padx=(8, 0))
        ctk.CTkButton(self, text="[ESC] CERRAR", height=24, width=120, font=tema.fuente(12),
                      command=al_cerrar).pack(anchor="e", padx=10, pady=(0, 8))

    def mostrar(self, robot: dict) -> None:
        self._titulo.configure(text=f"  {robot['id']} · {robot['tipo'].upper()}",
                               fg_color=tema.FRANJA[robot["franja"]])
        mision = robot["mision"]
        detalle = (f"Destino:\n{mision['destino']}\nCarga: {mision['carga']}\n"
                   f"Avance: {mision['progreso'] * 100:.0f} %") if mision else "Sin misión"
        self._datos.configure(text=f"Estado: {robot['estado']}\nBatería: {robot['bateria']:.0f} %\n"
                                   f"{'Vuela' if robot['es_aereo'] else 'Por senderos'}\n\n{detalle}")
        self._dibujar_radar(robot["radar"])

    def _dibujar_radar(self, valores: dict) -> None:
        c = self._radar
        c.delete("all")
        cx, cy, radio = 95, 92, 62
        lleno = {eje: 1 for eje, _ in EJES}
        for escala in (1, 0.66, 0.33):  # anillos de referencia
            borde = puntos_radar({e: escala for e in lleno}, cx, cy, radio)
            c.create_polygon(*sum(borde, ()), fill="", outline="#b9a98a")
        for (x, y), (_, nombre) in zip(puntos_radar(lleno, cx, cy, radio + 16), EJES):
            c.create_text(x, y, text=nombre, fill=tema.TINTA, font=(tema.MONO, 9))
        figura = puntos_radar(valores, cx, cy, radio)
        c.create_polygon(*sum(figura, ()), fill="#f5b77a", outline=tema.ALERTA, width=2)


class FichaSolicitud(ctk.CTkFrame):
    """Ficha de una llamada: el operador la despacha en AUTO o eligiendo un robot de la plantilla."""

    def __init__(self, master, al_auto, al_cerrar):
        super().__init__(master, fg_color=tema.PAPEL, corner_radius=2, border_width=2, border_color="#3d5a5e")
        self.id = None
        self._titulo = ctk.CTkLabel(self, text="", height=26, corner_radius=0, font=tema.fuente(16, True),
                                    text_color="#ffffff", fg_color=tema.ALERTA, anchor="w")
        self._titulo.pack(fill="x", padx=2, pady=(2, 0))
        self._datos = ctk.CTkLabel(self, text="", justify="left", anchor="w", text_color=tema.TINTA,
                                   font=tema.fuente(13), width=330, wraplength=330)
        self._datos.pack(padx=12, pady=(6, 2))
        self._resultado = ctk.CTkLabel(self, text="", justify="left", anchor="w", font=tema.fuente(13, True),
                                       width=330, wraplength=330)
        self._resultado.pack(padx=12)
        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(fill="x", padx=12, pady=(4, 10))
        ctk.CTkButton(botones, text="[A] AUTO", width=110, height=26, font=tema.fuente(13, True),
                      command=lambda: al_auto(self.id)).pack(side="left")
        ctk.CTkButton(botones, text="[ESC] CERRAR", width=110, height=26, font=tema.fuente(12),
                      command=al_cerrar).pack(side="right")

    def mostrar(self, baliza: dict) -> None:
        nuevo = baliza["id"] != self.id
        self.id = baliza["id"]
        self._titulo.configure(text=f"  LLAMADA #{baliza['id']} · {baliza['carga'].upper()}")
        espera = "en reintento automático" if baliza["automatica"] else "esperando robot"
        self._datos.configure(text=f"De: {baliza['origen']}\nA:  {baliza['destino']}\n"
                                   f"Peso: {baliza['peso']:g} kg · {espera}\n"
                                   "Elige un robot en la plantilla o pulsa AUTO.")
        if nuevo:  # al abrirla muestra por qué espera; después, el resultado del último despacho
            self.anunciar(baliza["motivo"], ok=False)

    def anunciar(self, texto: str, ok: bool) -> None:
        self._resultado.configure(text=texto, text_color="#2c7a4b" if ok else tema.FALLA)
