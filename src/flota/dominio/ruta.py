"""Rutas dentro del campus: una línea recta o el camino más corto por los senderos reales."""
import heapq
from typing import Optional

from flota.dominio.ubicacion import Ubicacion, distancia_haversine_km

Punto = tuple[float, float]  # (latitud, longitud)


class Ruta:
    """Recorrido de un robot: los puntos por donde pasa y su longitud."""

    def __init__(self, puntos: list[Punto], distancia_km: float):
        if len(puntos) < 2:
            raise ValueError("Una ruta necesita al menos origen y destino")
        if distancia_km < 0:
            raise ValueError("La distancia no puede ser negativa")
        self._puntos = tuple(tuple(p) for p in puntos)
        self._distancia_km = float(distancia_km)

    @classmethod
    def linea_recta(cls, origen: Ubicacion, destino: Ubicacion, factor: float = 1.0) -> "Ruta":
        """De punto a punto; `factor` estima el rodeo cuando no se conoce el camino real."""
        return cls([(origen.latitud, origen.longitud), (destino.latitud, destino.longitud)],
                   origen.distancia_km(destino) * factor)

    @property
    def puntos(self) -> tuple[Punto, ...]:
        return self._puntos

    @property
    def distancia_km(self) -> float:
        return self._distancia_km

    def __repr__(self) -> str:
        return f"Ruta({len(self._puntos)} puntos, {self._distancia_km * 1000:.0f} m)"


class RedSenderos:
    """Grafo de los senderos del campus. Calcula el camino más corto con Dijkstra."""

    def __init__(self, caminos: list[list[Punto]]):
        self._vecinos: dict[Punto, dict[Punto, float]] = {}
        for camino in caminos:
            puntos = [tuple(p) for p in camino]
            for a, b in zip(puntos, puntos[1:]):  # los caminos de OSM se cruzan en puntos compartidos
                d = distancia_haversine_km(*a, *b)
                self._vecinos.setdefault(a, {})[b] = d
                self._vecinos.setdefault(b, {})[a] = d
        if not self._vecinos:
            raise ValueError("La red necesita al menos un sendero")
        self._cache: dict[tuple[Punto, Punto], Optional[Ruta]] = {}

    @property
    def cantidad_nodos(self) -> int:
        return len(self._vecinos)

    def _nodo_mas_cercano(self, u: Ubicacion) -> Punto:
        return min(self._vecinos, key=lambda p: distancia_haversine_km(u.latitud, u.longitud, *p))

    def ruta(self, origen: Ubicacion, destino: Ubicacion) -> Optional[Ruta]:
        """Camino más corto por los senderos, o None si no están conectados."""
        clave = ((origen.latitud, origen.longitud), (destino.latitud, destino.longitud))
        if clave[0] == clave[1]:
            return Ruta.linea_recta(origen, destino)  # ya está ahí: distancia 0
        if clave not in self._cache:
            self._cache[clave] = self._calcular(origen, destino)
        return self._cache[clave]

    def _calcular(self, origen: Ubicacion, destino: Ubicacion) -> Optional[Ruta]:
        inicio, fin = self._nodo_mas_cercano(origen), self._nodo_mas_cercano(destino)
        distancias, anterior = {inicio: 0.0}, {}
        pendientes = [(0.0, inicio)]
        while pendientes:
            d, nodo = heapq.heappop(pendientes)
            if nodo == fin:
                break
            if d > distancias[nodo]:
                continue  # entrada vieja: ya se encontró un camino más corto a este nodo
            for vecino, tramo in self._vecinos[nodo].items():
                nueva = d + tramo
                if nueva < distancias.get(vecino, float("inf")):
                    distancias[vecino], anterior[vecino] = nueva, nodo
                    heapq.heappush(pendientes, (nueva, vecino))
        if fin not in distancias:
            return None
        camino = [fin]
        while camino[-1] != inicio:
            camino.append(anterior[camino[-1]])
        camino.reverse()
        # del punto de entrega al sendero y del sendero al punto de entrega, en línea recta
        extremos = (distancia_haversine_km(origen.latitud, origen.longitud, *inicio)
                    + distancia_haversine_km(*fin, destino.latitud, destino.longitud))
        return Ruta([(origen.latitud, origen.longitud), *camino, (destino.latitud, destino.longitud)],
                    distancias[fin] + extremos)
