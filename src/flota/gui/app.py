"""Ventana principal: el centro de control. No tiene reglas de negocio: todo pasa por CentroControl."""
import customtkinter as ctk

from flota.gui.centro_control import CentroControl, crear_centro
from flota.gui.panel_bitacora import PanelBitacora
from flota.gui.panel_clima import PanelClima
from flota.gui.panel_flota import PanelFlota
from flota.gui.panel_mapa import PanelMapa
from flota.gui.panel_solicitud import PanelSolicitud


class App(ctk.CTk):

    def __init__(self, centro: CentroControl):
        super().__init__()
        self.title("Centro de Control - Flota de Reparto UdeM")
        self.geometry("1280x800")
        self.minsize(1000, 650)
        self.centro = centro

        self.columnconfigure(1, weight=1)  # el mapa se estira; las columnas laterales no
        self.rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text="Centro de Control - Flota de Reparto UdeM",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=16, pady=10)

        self.panel_flota = PanelFlota(self)
        self.panel_flota.grid(row=1, column=0, sticky="ns", padx=(10, 5), pady=5)
        self.col_lateral = ctk.CTkFrame(self, width=340)
        self.col_lateral.grid(row=1, column=2, sticky="ns", padx=(5, 10), pady=5)
        self.panel_clima = PanelClima(self.col_lateral, centro, self.actualizar)
        self.panel_clima.pack(fill="x", padx=8, pady=(8, 4))
        PanelSolicitud(self.col_lateral, centro, self.actualizar).pack(fill="x", padx=8, pady=4)
        self.panel_bitacora = PanelBitacora(self, centro)
        self.panel_bitacora.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(5, 10))

        self.panel_mapa = PanelMapa(self, centro, self.actualizar)
        self.panel_mapa.grid(row=1, column=1, sticky="nsew", pady=5)
        self._ciclo()

    def actualizar(self) -> None:
        """Lee el estado una sola vez y se lo pasa a cada panel."""
        estado = self.centro.estado()
        self.panel_flota.refrescar(estado)
        self.panel_clima.refrescar(estado)
        self.panel_bitacora.refrescar(estado)

    def _ciclo(self) -> None:
        self.actualizar()
        self.after(1000, self._ciclo)  # el clima real llega desde otro hilo


def main(real: bool = False) -> None:
    App(crear_centro(real)).mainloop()
