"""Clima del campus: semáforo de drones e interruptor Simulado / Open-Meteo en vivo."""
import customtkinter as ctk

SIMULADO, REAL = "Simulado", "Open-Meteo"


class PanelClima(ctk.CTkFrame):

    def __init__(self, master, centro, al_cambiar):
        super().__init__(master)
        self._centro = centro
        self._al_cambiar = al_cambiar

        ctk.CTkLabel(self, text="CLIMA DEL CAMPUS", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(8, 2))
        self._selector = ctk.CTkSegmentedButton(self, values=[SIMULADO, REAL], command=self._elegir)
        self._selector.pack(fill="x", padx=10, pady=4)
        self._datos = ctk.CTkLabel(self, text="", justify="left")
        self._datos.pack(anchor="w", padx=10)
        self._semaforo = ctk.CTkLabel(self, text="", font=ctk.CTkFont(weight="bold"))
        self._semaforo.pack(anchor="w", padx=10, pady=(2, 4))
        self._viento = self._deslizador("Viento (km/h)", 0, 80, 10)
        self._lluvia = self._deslizador("Lluvia (%)", 0, 100, 10)
        self._dia = ctk.CTkSwitch(self, text="Es de día", command=self._configurar_simulado)
        self._dia.select()
        self._dia.pack(anchor="w", padx=10, pady=(2, 8))
        self._selector.set(REAL if centro.estado()["clima"]["proveedor"] == REAL else SIMULADO)
        self._habilitar_controles()

    def _deslizador(self, texto, minimo, maximo, inicial):
        ctk.CTkLabel(self, text=texto, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)
        d = ctk.CTkSlider(self, from_=minimo, to=maximo, command=lambda _: self._configurar_simulado())
        d.set(inicial)
        d.pack(fill="x", padx=10)
        return d

    def _elegir(self, nombre: str) -> None:
        self._centro.usar_clima(nombre == REAL)  # la prueba en vivo del PRD
        self._habilitar_controles()
        self._al_cambiar()

    def _habilitar_controles(self) -> None:
        estado = "normal" if self._selector.get() == SIMULADO else "disabled"
        for control in (self._viento, self._lluvia, self._dia):
            control.configure(state=estado)

    def _configurar_simulado(self) -> None:
        self._centro.configurar_clima(self._viento.get(), self._lluvia.get(), bool(self._dia.get()))
        self._al_cambiar()

    def refrescar(self, estado: dict) -> None:
        c = estado["clima"]
        if c["consultando"]:
            self._datos.configure(text="Consultando...")
            self._semaforo.configure(text="")
            return
        if not c["disponible"]:
            self._datos.configure(text="Sin datos del clima")
        else:
            self._datos.configure(text=f"Viento {c['viento']:.0f} km/h · Ráfagas {c['rafagas']:.0f} km/h\n"
                                       f"Lluvia {c['lluvia']:.0f} % · {'Día' if c['es_de_dia'] else 'Noche'}")
        self._semaforo.configure(
            text="DRONES AUTORIZADOS" if c["drones_autorizados"] else f"DRONES NO: {c['motivo']}",
            text_color="#2e8b57" if c["drones_autorizados"] else "#c0392b")
