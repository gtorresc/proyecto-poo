"""Mapa del campus: solo dibuja lo que dice el dominio, no decide nada."""
from types import SimpleNamespace

import customtkinter as ctk
import requests
import tkintermapview
from tkintermapview import map_widget

from flota.dominio.robot import Dron, RobotOrugas
from flota.dominio.ubicacion import Zona

USER_AGENT = "FlotaRobotsUdeM/1.0 (proyecto academico de POO)"


def _get_con_user_agent(url, **kwargs):
    # OSM bloquea el User-Agent fijo de tkintermapview; su política pide uno que identifique la app
    kwargs["headers"] = {"User-Agent": USER_AGENT}
    return requests.get(url, **kwargs)


map_widget.requests = SimpleNamespace(get=_get_con_user_agent, exceptions=requests.exceptions)  # solo dentro de ese módulo

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
        for marcador in self._marcadores_robots:
            marcador.delete()
        self._marcadores_robots = [
            self.mapa.set_marker(r.ubicacion.latitud, r.ubicacion.longitud, text=r.id,
                                 marker_color_circle=color_robot(r), marker_color_outside="#222222",
                                 text_color=color_robot(r), font=("Segoe UI", 10, "bold"))
            for r in self._flota.robots
        ]
