"""Mapa del campus: solo dibuja lo que dice el dominio, no decide nada."""
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

CENTRO_CAMPUS = (6.2316146, -75.6111419)  # Plaza de Prometeo
COLOR_ZONA = {Zona.EDIFICIO: "#1f6aa5", Zona.AZOTEA: "#8e44ad", Zona.ZONA_VERDE: "#2e8b57"}


def color_robot(robot) -> str:
    if isinstance(robot, Dron):  # solo presentación: el dominio no sabe de colores
        return "#e67e22"
    return "#8d6e63" if isinstance(robot, RobotOrugas) else "#c0392b"


class PanelMapa(ctk.CTkFrame):

    def __init__(self, master, ubicaciones: dict, flota):
        super().__init__(master)
        self._flota = flota
        self._marcadores_robots = []
        self._posiciones = None
        self.mapa = tkintermapview.TkinterMapView(self, corner_radius=0)  # tiles de OpenStreetMap
        self.mapa.pack(fill="both", expand=True)
        self.mapa.set_position(*CENTRO_CAMPUS)
        self.mapa.set_zoom(18)
        for u in ubicaciones.values():
            self.mapa.set_marker(u.latitud, u.longitud, text=u.nombre,
                                 marker_color_circle=COLOR_ZONA[u.zona],
                                 marker_color_outside=COLOR_ZONA[u.zona], font=("Segoe UI", 9))
        self.refrescar()

    def refrescar(self) -> None:
        """Vuelve a dibujar los robots en su ubicación actual."""
        posiciones = [(r.id, r.ubicacion) for r in self._flota.robots]
        if posiciones == self._posiciones:
            return  # nada se movió: evita redibujar cada segundo
        self._posiciones = posiciones
        for marcador in self._marcadores_robots:
            marcador.delete()
        self._marcadores_robots = [
            self.mapa.set_marker(r.ubicacion.latitud, r.ubicacion.longitud, text=r.id,
                                 marker_color_circle=color_robot(r), marker_color_outside="#222222",
                                 text_color=color_robot(r), font=("Segoe UI", 10, "bold"))
            for r in self._flota.robots
        ]
