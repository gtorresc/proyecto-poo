"""Clima: píldoras sobre el mapa y el simulador con el interruptor real/simulado."""
import customtkinter as ctk

from flota.gui import tema

SIMULADO, REAL, NAGER = "Simulado", "Open-Meteo", "Nager.Date"
RUMBOS = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]


def rumbo(grados: float) -> str:
    """De dónde viene el viento, en 8 rumbos: 235° -> SO."""
    return RUMBOS[round(grados / 45) % 8]


def texto_clima(c: dict) -> str:
    if c["consultando"]:
        return "consultando clima..."
    if not c["disponible"]:
        return "clima no disponible"
    partes = [f"{c['temperatura']:.0f}°C" if c["temperatura"] is not None else None,
              f"humedad {c['humedad']:.0f}%" if c["humedad"] is not None else None,
              f"viento {c['viento']:.0f} km/h"
              + (f" {rumbo(c['direccion'])} {c['direccion']:.0f}°" if c["direccion"] is not None else ""),
              f"lluvia {c['lluvia']:.0f}%"]
    return "  |  ".join(p for p in partes if p)


class WidgetClima(ctk.CTkFrame):
    """Píldoras de clima y semáforo de drones; se coloca encima del mapa."""

    def __init__(self, master):
        super().__init__(master, fg_color="#0c1a1c", border_width=1, border_color="#46f0b4", corner_radius=3)
        self._datos = ctk.CTkLabel(self, text="", font=tema.fuente(13), text_color="#b9fff2", height=22)
        self._datos.pack(padx=10, pady=(4, 0))
        self._semaforo = ctk.CTkLabel(self, text="", font=tema.fuente(13, True), height=22)
        self._semaforo.pack(padx=10, pady=(0, 4))

    def refrescar(self, estado: dict) -> None:
        c = estado["clima"]
        self._datos.configure(text=texto_clima(c))
        if c["consultando"]:
            self._semaforo.configure(text="")
        elif c["drones_autorizados"]:
            self._semaforo.configure(text="DRONES AUTORIZADOS", text_color="#46f0b4")
        else:
            self._semaforo.configure(text=f"DRONES EN TIERRA: {c['motivo']}", text_color=tema.ALERTA)


class PanelClima(ctk.CTkFrame):
    """Simulador de clima y calendario, y el cambio en vivo a las APIs reales."""

    def __init__(self, master, centro, al_cambiar):
        super().__init__(master)
        self._centro = centro
        self._al_cambiar = al_cambiar
        ctk.CTkLabel(self, text="CLIMA Y CALENDARIO", font=tema.fuente(17, True)).pack(
            anchor="w", padx=10, pady=(6, 0))
        self._selector = ctk.CTkSegmentedButton(self, values=[SIMULADO, REAL], command=self._elegir_clima)
        self._selector.pack(fill="x", padx=10, pady=4)
        self._viento = self._deslizador("viento km/h", 0, 80, 10)
        self._lluvia = self._deslizador("lluvia %", 0, 100, 10)
        self._visibilidad = self._deslizador("visibilidad m", 0, 10_000, 10_000)
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x", padx=10, pady=(4, 2))
        self._dia = self._interruptor(fila, "día")
        self._dia.select()
        self._tormenta = self._interruptor(fila, "tormenta")
        self._calendario = ctk.CTkSegmentedButton(self, values=[SIMULADO, NAGER],
                                                  command=self._elegir_calendario)
        self._calendario.pack(fill="x", padx=10, pady=(6, 2))
        self._festivo = self._interruptor(self, "festivo (cafetería cerrada)", self._configurar_festivo)
        self._festivo.pack_configure(padx=10, pady=(2, 8))
        estado = centro.estado()
        self._selector.set(REAL if estado["clima"]["proveedor"] == REAL else SIMULADO)
        self._calendario.set(NAGER if estado["calendario"]["proveedor"] == NAGER else SIMULADO)
        self._habilitar_controles()

    def _deslizador(self, texto, minimo, maximo, inicial):
        fila = ctk.CTkFrame(self, fg_color="transparent")
        fila.pack(fill="x", padx=10)
        ctk.CTkLabel(fila, text=texto, font=tema.fuente(12), width=100, anchor="w").pack(side="left")
        d = ctk.CTkSlider(fila, from_=minimo, to=maximo, command=lambda _: self._configurar_clima())
        d.set(inicial)
        d.pack(side="left", fill="x", expand=True)
        return d

    def _interruptor(self, master, texto, comando=None):
        s = ctk.CTkSwitch(master, text=texto, font=tema.fuente(12), command=comando or self._configurar_clima)
        s.pack(side="left", padx=(0, 12))
        return s

    def _elegir_clima(self, nombre: str) -> None:
        self._centro.usar_clima(nombre == REAL)  # la prueba en vivo del PRD
        self._habilitar_controles()
        self._al_cambiar()

    def _elegir_calendario(self, nombre: str) -> None:
        self._centro.usar_calendario(nombre == NAGER)
        self._habilitar_controles()
        self._al_cambiar()

    def _habilitar_controles(self) -> None:
        simulado = self._selector.get() == SIMULADO
        for control in (self._viento, self._lluvia, self._visibilidad, self._dia, self._tormenta):
            control.configure(state="normal" if simulado else "disabled")
        self._festivo.configure(state="normal" if self._calendario.get() == SIMULADO else "disabled")

    def _configurar_clima(self) -> None:
        self._centro.configurar_clima(self._viento.get(), self._lluvia.get(), bool(self._dia.get()),
                                      self._visibilidad.get(), bool(self._tormenta.get()))
        self._al_cambiar()

    def _configurar_festivo(self) -> None:
        self._centro.configurar_festivo("Festivo simulado" if self._festivo.get() else None)
        self._al_cambiar()
