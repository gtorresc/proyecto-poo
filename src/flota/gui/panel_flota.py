"""Tarjetas de la flota: una por robot, con batería y estado. Solo lee el dominio."""
import customtkinter as ctk

from flota.dominio.estado_robot import EstadoRobot

COLOR_ESTADO = {EstadoRobot.DISPONIBLE: "#2e8b57", EstadoRobot.EN_RUTA: "#e67e22",
                EstadoRobot.MANTENIMIENTO: "#c0392b"}


def color_bateria(nivel: float) -> str:
    return "#2e8b57" if nivel > 50 else "#e6b800" if nivel > 25 else "#c0392b"


class PanelFlota(ctk.CTkScrollableFrame):

    def __init__(self, master, flota):
        super().__init__(master, label_text="FLOTA", width=220)
        self._flota = flota
        self._tarjetas = {}  # id del robot -> (barra, etiqueta de batería, etiqueta de estado)
        self.refrescar()

    def _crear_tarjeta(self, robot) -> tuple:
        tarjeta = ctk.CTkFrame(self)
        tarjeta.pack(fill="x", pady=4)
        ctk.CTkLabel(tarjeta, text=f"{robot.id}  ·  {type(robot).__name__.removeprefix('Robot')}",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 0))
        barra = ctk.CTkProgressBar(tarjeta)
        barra.pack(fill="x", padx=10, pady=(6, 0))
        bateria = ctk.CTkLabel(tarjeta, text="", font=ctk.CTkFont(size=11))
        bateria.pack(anchor="w", padx=10)
        estado = ctk.CTkLabel(tarjeta, text="", font=ctk.CTkFont(size=12, weight="bold"))
        estado.pack(anchor="w", padx=10, pady=(0, 8))
        return barra, bateria, estado

    def refrescar(self) -> None:
        for robot in self._flota.robots:
            if robot.id not in self._tarjetas:
                self._tarjetas[robot.id] = self._crear_tarjeta(robot)
            barra, bateria, estado = self._tarjetas[robot.id]
            barra.set(robot.nivel_bateria / 100)
            barra.configure(progress_color=color_bateria(robot.nivel_bateria))
            bateria.configure(text=f"Batería {robot.nivel_bateria:.0f} %")
            estado.configure(text=robot.estado.value.capitalize(),
                             text_color=COLOR_ESTADO[robot.estado])
