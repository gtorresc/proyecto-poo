"""Mapa del campus: solo dibuja lo que dice CentroControl, no decide nada."""
from types import SimpleNamespace

import customtkinter as ctk
import requests
import tkintermapview
from requests.adapters import HTTPAdapter
from tkintermapview import map_widget

from flota.gui.centro_control import CENTRO_CAMPUS, a_latlon

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
COLOR_ZONA = {"edificio": "#1f6aa5", "azotea": "#8e44ad", "zona verde": "#2e8b57"}
COLOR_TIPO = {"Ruedas": "#c0392b", "Orugas": "#8d6e63", "Dron": "#e67e22"}  # solo presentación


class PanelMapa(ctk.CTkFrame):
    """Dibuja los robots donde CentroControl dice que están; el avance lo lleva CentroControl."""

    def __init__(self, master, centro, al_completar):
        super().__init__(master)
        self._centro, self._al_completar = centro, al_completar
        self._marcadores = {}   # id del robot -> marcador
        self._rutas = {}        # id de la solicitud -> línea de la ruta
        self.mapa = tkintermapview.TkinterMapView(self, corner_radius=0)  # tiles de OpenStreetMap
        self.mapa.pack(fill="both", expand=True)
        self.mapa.set_position(*CENTRO_CAMPUS)
        self.mapa.set_zoom(18)
        for u in centro.geometria()["ubicaciones"]:
            self.mapa.set_marker(*a_latlon(u["x"], u["y"]), text=u["nombre"],
                                 marker_color_circle=COLOR_ZONA[u["zona"]],
                                 marker_color_outside=COLOR_ZONA[u["zona"]], font=("Segoe UI", 9))
        self._ciclo()

    def _ciclo(self) -> None:
        if self._centro.tick():
            self._al_completar()
        self._dibujar(self._centro.estado()["robots"])
        self.after(INTERVALO_MS, self._ciclo)

    def _dibujar(self, robots: list[dict]) -> None:
        activas = set()
        for r in robots:
            if r["recorrido"]:  # la ruta real: por senderos o en línea recta si es dron
                activas.add(r["mision"]["solicitud"])
                if r["mision"]["solicitud"] not in self._rutas:
                    self._rutas[r["mision"]["solicitud"]] = self.mapa.set_path(
                        [a_latlon(*p) for p in r["recorrido"]], color=COLOR_TIPO[r["tipo"]], width=3)
            marcador = self._marcadores.get(r["id"])
            if marcador is None:
                self._marcadores[r["id"]] = self.mapa.set_marker(
                    r["lat"], r["lon"], text=r["id"], marker_color_circle=COLOR_TIPO[r["tipo"]],
                    marker_color_outside="#222222", text_color=COLOR_TIPO[r["tipo"]],
                    font=("Segoe UI", 10, "bold"))
            elif marcador.position != (r["lat"], r["lon"]):
                marcador.set_position(r["lat"], r["lon"])
        for id_sol in set(self._rutas) - activas:
            self._rutas.pop(id_sol).delete()
