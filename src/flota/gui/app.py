"""Ventana principal: el monitor de UdeM·DESPACHO. No tiene reglas de negocio: todo pasa por CentroControl."""
import time

import customtkinter as ctk

from flota.gui import tema
from flota.gui.centro_control import CentroControl, crear_centro
from flota.gui.panel_bitacora import PanelBitacora
from flota.gui.panel_clima import PanelClima, WidgetClima
from flota.gui.panel_mapa import PanelMapa
from flota.gui.panel_solicitud import PanelSolicitud
from flota.gui.plantilla import FichaRobot, Plantilla

CREDITOS = "© OpenStreetMap contributors · Open-Meteo · Nager.Date · retratos RoboHash (CC-BY)"


class App(ctk.CTk):

    def __init__(self, centro: CentroControl):
        super().__init__()
        self.title("UdeM·DESPACHO - Flota de reparto")
        self.geometry("1366x860")
        self.minsize(1100, 720)
        self.centro = centro
        self._inicio = time.monotonic()

        # el "monitor": un marco con bisel alrededor de toda la pantalla
        pantalla = ctk.CTkFrame(self, corner_radius=14, border_width=2, border_color="#2f4b4f", fg_color="#0f1d1f")
        pantalla.pack(fill="both", expand=True, padx=14, pady=14)
        pantalla.columnconfigure(0, weight=1)
        pantalla.rowconfigure(1, weight=1)

        self._barra_superior = self._barra(pantalla, row=0, pady=(10, 4))
        self.panel_mapa = PanelMapa(pantalla, centro, self.actualizar)
        self.panel_mapa.grid(row=1, column=0, sticky="nsew", padx=(14, 6))
        self.widget_clima = WidgetClima(self.panel_mapa)
        self.widget_clima.place(relx=1, x=-12, y=12, anchor="ne")
        self.ficha = FichaRobot(self.panel_mapa, lambda: self._elegir(None))

        lateral = ctk.CTkFrame(pantalla, fg_color="transparent", width=340)
        lateral.grid(row=1, column=1, rowspan=2, sticky="ns", padx=(6, 14))
        PanelSolicitud(lateral, centro, self.actualizar).pack(fill="x", pady=(0, 6))
        PanelClima(lateral, centro, self.actualizar).pack(fill="x", pady=6)
        self.panel_bitacora = PanelBitacora(lateral, centro)
        self.panel_bitacora.pack(fill="both", expand=True, pady=(6, 0))

        self.plantilla = Plantilla(pantalla, self._elegir)
        self.plantilla.grid(row=2, column=0, sticky="ew", padx=14, pady=(8, 0))
        self._barra_inferior = self._barra(pantalla, row=3, pady=(4, 10))
        self.bind("<Escape>", lambda _: self._elegir(None))
        self._ciclo()

    def _barra(self, master, row: int, pady) -> ctk.CTkLabel:
        barra = ctk.CTkLabel(master, text="", anchor="w", font=tema.fuente(12), text_color=tema.TEXTO_BARRA,
                             height=18)
        barra.grid(row=row, column=0, columnspan=2, sticky="ew", padx=18, pady=pady)
        return barra

    def _elegir(self, id_robot) -> None:
        self.plantilla.elegido = id_robot
        if id_robot is None:
            self.ficha.place_forget()
        else:
            self.ficha.place(x=12, rely=1, y=-12, anchor="sw")
        self.actualizar()

    def actualizar(self) -> None:
        """Lee el estado una sola vez y se lo pasa a cada parte de la pantalla."""
        estado = self.centro.estado()
        self.plantilla.refrescar(estado)
        self.widget_clima.refrescar(estado)
        self.panel_bitacora.refrescar(estado)
        if self.plantilla.elegido:
            self.ficha.mostrar(next(r for r in estado["robots"] if r["id"] == self.plantilla.elegido))
        r, c, cal = estado["resumen"], estado["clima"], estado["calendario"]
        minutos, segundos = divmod(int(time.monotonic() - self._inicio), 60)
        self._barra_superior.configure(text=(
            f"UdeM·DESPACHO   |   {r['robots']} robots   |   {r['en_ruta']} en ruta   |   "
            f"{r['esperando']} en espera   |   turno {minutos:02d}:{segundos:02d}   |   "
            f"{time.strftime('%H:%M')}"))
        self._barra_inferior.configure(text=(
            f"Flota sincronizada {r['disponibles']}/{r['robots']}   |   clima: {c['proveedor']}   |   "
            f"calendario: {cal['proveedor']} · festivo: {cal['festivo'] or 'no'}   |   "
            f"mantenimiento: {r['mantenimiento']}   |   {CREDITOS}"))

    def _ciclo(self) -> None:
        self.actualizar()
        self.after(1000, self._ciclo)  # el clima real llega desde otro hilo


def main(real: bool = False) -> None:
    tema.aplicar_tema()  # fuentes y colores antes de crear la ventana
    App(crear_centro(real)).mainloop()
