"""Tarjetas de la flota: una por robot, con batería y estado. Solo lee el estado de CentroControl."""
import customtkinter as ctk

COLOR_FRANJA = {"libre": "#2e8b57", "ocupado": "#e67e22", "falla": "#c0392b"}


def color_bateria(nivel: float) -> str:
    return "#2e8b57" if nivel > 50 else "#e6b800" if nivel > 25 else "#c0392b"


class PanelFlota(ctk.CTkScrollableFrame):

    def __init__(self, master):
        super().__init__(master, label_text="FLOTA", width=220)
        self._tarjetas = {}  # id del robot -> (barra, etiqueta de batería, etiqueta de estado)

    def _crear_tarjeta(self, robot: dict) -> tuple:
        tarjeta = ctk.CTkFrame(self)
        tarjeta.pack(fill="x", pady=4)
        ctk.CTkLabel(tarjeta, text=f"{robot['id']}  ·  {robot['tipo']}",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(8, 0))
        barra = ctk.CTkProgressBar(tarjeta)
        barra.pack(fill="x", padx=10, pady=(6, 0))
        bateria = ctk.CTkLabel(tarjeta, text="", font=ctk.CTkFont(size=11))
        bateria.pack(anchor="w", padx=10)
        estado = ctk.CTkLabel(tarjeta, text="", font=ctk.CTkFont(size=12, weight="bold"))
        estado.pack(anchor="w", padx=10, pady=(0, 8))
        return barra, bateria, estado

    def refrescar(self, estado: dict) -> None:
        for robot in estado["robots"]:
            if robot["id"] not in self._tarjetas:
                self._tarjetas[robot["id"]] = self._crear_tarjeta(robot)
            barra, bateria, etiqueta = self._tarjetas[robot["id"]]
            barra.set(robot["bateria"] / 100)
            barra.configure(progress_color=color_bateria(robot["bateria"]))
            bateria.configure(text=f"Batería {robot['bateria']:.0f} %")
            etiqueta.configure(text=robot["estado"].capitalize(), text_color=COLOR_FRANJA[robot["franja"]])
