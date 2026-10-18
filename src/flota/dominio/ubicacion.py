"""Ubicaciones del campus y zonas a las que pueden llegar los robots."""
from enum import Enum
from math import asin, cos, radians, sin, sqrt

RADIO_TIERRA_KM = 6371.0


class Zona(Enum):
    """Tipo de lugar del campus; define qué robots pueden llegar."""
    EDIFICIO = "edificio"
    ZONA_VERDE = "zona verde"
    AZOTEA = "azotea"


class Ubicacion:
    """Punto de entrega del campus con sus coordenadas y su zona."""

    def __init__(self, nombre: str, latitud: float, longitud: float, zona: Zona):
        if not nombre or not nombre.strip():
            raise ValueError("La ubicación necesita un nombre")
        if not -90 <= latitud <= 90:
            raise ValueError(f"Latitud fuera de rango: {latitud}")
        if not -180 <= longitud <= 180:
            raise ValueError(f"Longitud fuera de rango: {longitud}")
        if not isinstance(zona, Zona):
            raise TypeError("La zona debe ser un valor de Zona")
        self._nombre = nombre.strip()
        self._latitud = latitud
        self._longitud = longitud
        self._zona = zona

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def latitud(self) -> float:
        return self._latitud

    @property
    def longitud(self) -> float:
        return self._longitud

    @property
    def zona(self) -> Zona:
        return self._zona

    def distancia_km(self, otra: "Ubicacion") -> float:
        """Distancia en línea recta (fórmula de Haversine)."""
        lat1, lon1 = radians(self._latitud), radians(self._longitud)
        lat2, lon2 = radians(otra.latitud), radians(otra.longitud)
        a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
        return 2 * RADIO_TIERRA_KM * asin(sqrt(a))

    def __repr__(self) -> str:
        return f"Ubicacion({self._nombre!r}, {self._zona.value})"
