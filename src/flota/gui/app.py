"""Ventana principal: el centro de control. No tiene reglas de negocio."""
import customtkinter as ctk

from flota.asignacion.asignador import AsignadorEntregas
from flota.campus import cargar_campus
from flota.dominio.bitacora import Bitacora
from flota.gui.panel_bitacora import PanelBitacora
from flota.gui.panel_clima import PanelClima
from flota.gui.panel_flota import PanelFlota
from flota.gui.panel_mapa import PanelMapa
from flota.gui.panel_solicitud import PanelSolicitud
from flota.servicios.clima_simulado import ServicioClimaSimulado


class App(ctk.CTk):

    def __init__(self, ubicaciones: dict, flota, asignador: AsignadorEntregas, bitacora: Bitacora,
                 real: bool = False):
        super().__init__()
        self.title("Centro de Control - Flota de Reparto UdeM")
        self.geometry("1280x800")
        self.minsize(1000, 650)
        self.ubicaciones, self.flota, self.asignador, self.bitacora = ubicaciones, flota, asignador, bitacora

        self.columnconfigure(1, weight=1)  # el mapa se estira; las columnas laterales no
        self.rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text="Centro de Control - Flota de Reparto UdeM",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=16, pady=10)

        self.panel_flota = PanelFlota(self, flota)
        self.panel_flota.grid(row=1, column=0, sticky="ns", padx=(10, 5), pady=5)
        self.col_lateral = ctk.CTkFrame(self, width=340)
        self.col_lateral.grid(row=1, column=2, sticky="ns", padx=(5, 10), pady=5)
        self.panel_clima = PanelClima(self.col_lateral, asignador, ubicaciones["biblioteca"],
                                      self._clima_cambio, real)
        self.panel_clima.pack(fill="x", padx=8, pady=(8, 4))
        PanelSolicitud(self.col_lateral, ubicaciones, asignador, self.actualizar).pack(
            fill="x", padx=8, pady=4)
        self.panel_bitacora = PanelBitacora(self, bitacora)
        self.panel_bitacora.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(5, 10))

        self.panel_mapa = PanelMapa(self, ubicaciones, flota, asignador, self.actualizar)
        self.panel_mapa.grid(row=1, column=1, sticky="nsew", pady=5)
        self._ciclo()

    def actualizar(self) -> None:
        """Vuelve a leer el dominio; lo llaman los paneles que lo modifican."""
        self.panel_flota.refrescar()
        self.panel_clima.refrescar()
        self.panel_bitacora.refrescar()

    def _clima_cambio(self) -> None:
        self.asignador.reintentar_pendientes()  # un clima mejor puede liberar solicitudes pendientes
        self.actualizar()

    def _ciclo(self) -> None:
        self.actualizar()
        self.after(1000, self._ciclo)  # por si el dominio cambia sin que la GUI lo sepa


def main(real: bool = False) -> None:
    ubicaciones, flota = cargar_campus()
    bitacora = Bitacora()
    asignador = AsignadorEntregas(flota, ServicioClimaSimulado(), bitacora)  # el panel de clima lo cambia
    App(ubicaciones, flota, asignador, bitacora, real).mainloop()
