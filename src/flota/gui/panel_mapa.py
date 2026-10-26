"""Mapa del campus: solo dibuja lo que dice el dominio, no decide nada."""
import time
from types import SimpleNamespace

import customtkinter as ctk
import requests
import tkintermapview
from requests.adapters import HTTPAdapter
from tkintermapview import map_widget

from flota.dominio.robot import Dron, RobotOrugas
from flota.dominio.ubicacion import Zona

USER_AGENT = "FlotaRobotsUdeM/1.0 (proyecto academico de POO)"
TIMEOUT_TILE_S = 10


class _AdaptadorIPv4(HTTPAdapter):
    """Fuerza IPv4: con IPv6 bloqueado, requests espera ~20 s por tile antes de probar IPv4."""

    def init_poolmanager(self, *args, **kwargs):
        kwargs["source_address"] = ("0.0.0.0", 0)
        super().init_poolmanager(*args, **kwargs)


_sesion = requests.Session()
_sesion.mount("https://", _AdaptadorIPv4(pool_maxsize=32))  # tkintermapview baja tiles con ~25 hilos
_sesion.mount("http://", _AdaptadorIPv4(pool_maxsize=32))


def _get_para_tiles(url, **kwargs):
    # OSM bloquea el User-Agent fijo de tkintermapview (su política pide uno que identifique la app)
    # y la librería no pone timeout: sin él un tile colgado deja un hilo esperando para siempre
    kwargs["headers"] = {"User-Agent": USER_AGENT}
    kwargs.setdefault("timeout", TIMEOUT_TILE_S)
    return _sesion.get(url, **kwargs)


# solo dentro del módulo de tkintermapview; el requests global no cambia
map_widget.requests = SimpleNamespace(get=_get_para_tiles, exceptions=requests.exceptions)

INTERVALO_MS = 50
SEGUNDOS_POR_MINUTO = 6  # 1 min de viaje simulado = 6 s en pantalla
MIN_VIAJE_S = 3          # los tramos de 0,2 km durarían menos de un parpadeo
CENTRO_CAMPUS = (6.2316146, -75.6111419)  # Plaza de Prometeo
COLOR_ZONA = {Zona.EDIFICIO: "#1f6aa5", Zona.AZOTEA: "#8e44ad", Zona.ZONA_VERDE: "#2e8b57"}


def color_robot(robot) -> str:
    if isinstance(robot, Dron):  # solo presentación: el dominio no sabe de colores
        return "#e67e22"
    return "#8d6e63" if isinstance(robot, RobotOrugas) else "#c0392b"


class PanelMapa(ctk.CTkFrame):
    """Dibuja los robots y los mueve de origen a destino; al llegar, completa la entrega."""

    def __init__(self, master, ubicaciones: dict, flota, asignador, al_completar, reloj=time.monotonic):
        super().__init__(master)
        self._flota, self._asignador, self._al_completar, self._reloj = flota, asignador, al_completar, reloj
        self._marcadores = {}   # id del robot -> marcador
        self._viajes = {}       # id de la solicitud -> (inicio, duración en s, línea de ruta)
        self.mapa = tkintermapview.TkinterMapView(self, corner_radius=0)  # tiles de OpenStreetMap
        self.mapa.pack(fill="both", expand=True)
        self.mapa.set_position(*CENTRO_CAMPUS)
        self.mapa.set_zoom(18)
        for u in ubicaciones.values():
            self.mapa.set_marker(u.latitud, u.longitud, text=u.nombre,
                                 marker_color_circle=COLOR_ZONA[u.zona],
                                 marker_color_outside=COLOR_ZONA[u.zona], font=("Segoe UI", 9))
        self._ciclo()

    def _ciclo(self) -> None:
        try:
            self.refrescar()
        finally:  # un error en una entrega no debe detener la animación ni las siguientes entregas
            self.after(INTERVALO_MS, self._ciclo)

    def refrescar(self) -> None:
        ahora = self._reloj()
        for solicitud in self._asignador.en_curso:
            if solicitud.id not in self._viajes:
                self._iniciar_viaje(solicitud, ahora)
        llegadas = [s for s in self._asignador.en_curso if self._progreso(s, ahora) >= 1]
        for solicitud in llegadas:
            self._viajes.pop(solicitud.id)[2].delete()
            self._asignador.completar_entrega(solicitud)  # el robot pasa a estar en el destino
        if llegadas:
            self._al_completar()
        self._dibujar_robots(ahora)

    def _iniciar_viaje(self, solicitud, ahora: float) -> None:
        o, d, robot = solicitud.origen, solicitud.destino, solicitud.robot
        # la duración sale del propio robot: un dron llega antes que unas orugas
        duracion = max(MIN_VIAJE_S, robot.calcular_tiempo_min(o, d) * SEGUNDOS_POR_MINUTO)
        ruta = self.mapa.set_path([(o.latitud, o.longitud), (d.latitud, d.longitud)],
                                  color=color_robot(robot), width=3)
        self._viajes[solicitud.id] = (ahora, duracion, ruta)

    def _progreso(self, solicitud, ahora: float) -> float:
        inicio, duracion, _ = self._viajes[solicitud.id]
        return (ahora - inicio) / duracion

    def _dibujar_robots(self, ahora: float) -> None:
        en_viaje = {s.robot.id: s for s in self._asignador.en_curso}
        for robot in self._flota.robots:
            solicitud = en_viaje.get(robot.id)
            if solicitud is None:
                lat, lon = robot.ubicacion.latitud, robot.ubicacion.longitud
            else:  # interpolación lineal entre origen y destino
                t = min(1.0, self._progreso(solicitud, ahora))
                o, d = solicitud.origen, solicitud.destino
                lat, lon = o.latitud + (d.latitud - o.latitud) * t, o.longitud + (d.longitud - o.longitud) * t
            marcador = self._marcadores.get(robot.id)
            if marcador is None:
                self._marcadores[robot.id] = self.mapa.set_marker(
                    lat, lon, text=robot.id, marker_color_circle=color_robot(robot),
                    marker_color_outside="#222222", text_color=color_robot(robot),
                    font=("Segoe UI", 10, "bold"))
            elif marcador.position != (lat, lon):
                marcador.set_position(lat, lon)
