"""Clima del campus: semáforo de drones e interruptor Simulado / Open-Meteo en vivo."""
import threading

import customtkinter as ctk

from flota.servicios.clima_open_meteo import ServicioClimaOpenMeteo
from flota.servicios.clima_simulado import ServicioClimaSimulado

SIMULADO, REAL = "Simulado", "Open-Meteo"


class PanelClima(ctk.CTkFrame):

    def __init__(self, master, asignador, ubicacion_referencia, al_cambiar, real: bool = False):
        super().__init__(master)
        self._asignador = asignador
        self._ubicacion = ubicacion_referencia
        self._al_cambiar = al_cambiar
        self._simulado = ServicioClimaSimulado(umbrales=asignador.proveedor_clima.umbrales)
        self._real = ServicioClimaOpenMeteo(umbrales=asignador.proveedor_clima.umbrales)
        self._reporte = None  # lo escribe el hilo de red y lo pinta refrescar()

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

        nombre = REAL if real else SIMULADO
        self._selector.set(nombre)
        self._aplicar(nombre)

    def _deslizador(self, texto, minimo, maximo, inicial):
        ctk.CTkLabel(self, text=texto, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)
        d = ctk.CTkSlider(self, from_=minimo, to=maximo, command=lambda _: self._configurar_simulado())
        d.set(inicial)
        d.pack(fill="x", padx=10)
        return d

    def _elegir(self, nombre: str) -> None:
        self._aplicar(nombre)
        self._al_cambiar()

    def _aplicar(self, nombre: str) -> None:
        """La prueba en vivo del PRD: se cambia el proveedor sin tocar la asignación."""
        simulado = nombre == SIMULADO
        self._asignador.cambiar_proveedor_clima(self._simulado if simulado else self._real)
        for control in (self._viento, self._lluvia, self._dia):
            control.configure(state="normal" if simulado else "disabled")
        self._leer_reporte()

    def _configurar_simulado(self) -> None:
        viento = self._viento.get()
        self._simulado.configurar(viento, viento * 1.3, self._lluvia.get(), bool(self._dia.get()))
        self._leer_reporte()
        self._al_cambiar()

    def _leer_reporte(self) -> None:
        proveedor = self._asignador.proveedor_clima
        if proveedor is self._simulado:
            self._reporte = proveedor.obtener_reporte(self._ubicacion)
        else:  # la red puede tardar hasta el timeout: no congelar la ventana
            self._reporte = None
            threading.Thread(target=self._reporte_en_hilo, args=(proveedor,), daemon=True).start()

    def _reporte_en_hilo(self, proveedor) -> None:
        reporte = proveedor.obtener_reporte(self._ubicacion)
        if proveedor is self._asignador.proveedor_clima:  # ignora respuestas de un proveedor ya cambiado
            self._reporte = reporte

    def refrescar(self) -> None:
        r = self._reporte
        if r is None:
            self._datos.configure(text="Consultando...")
            self._semaforo.configure(text="")
            return
        if not r.disponible:
            self._datos.configure(text="Sin datos del clima")
        else:
            self._datos.configure(text=f"Viento {r.viento_kmh:.0f} km/h · Ráfagas {r.rafagas_kmh:.0f} km/h\n"
                                       f"Lluvia {r.prob_lluvia_pct:.0f} % · {'Día' if r.es_de_dia else 'Noche'}")
        favorable, motivo = r.es_favorable(self._asignador.proveedor_clima.umbrales)
        self._semaforo.configure(text="DRONES AUTORIZADOS" if favorable else f"DRONES NO: {motivo}",
                                 text_color="#2e8b57" if favorable else "#c0392b")
