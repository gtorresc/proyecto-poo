"""Robots de la flota: una clase abstracta y un subtipo por forma de moverse."""
from abc import ABC, abstractmethod
from typing import Optional

from flota.dominio.bateria import Bateria
from flota.dominio.estado_robot import EstadoRobot
from flota.dominio.ubicacion import Ubicacion, Zona

FACTOR_RODEO_TERRESTRE = 1.3  # supuesto S5: los robots terrestres siguen senderos


class Robot(ABC):
    """Lo común a todos los robots. Cada subtipo define zonas, costo y consumo."""

    def __init__(self, id_robot: str, ubicacion: Ubicacion, carga_maxima_kg: float,
                 velocidad_kmh: float, tiene_control_temperatura: bool = False,
                 nivel_bateria: float = 100.0):
        if not id_robot or not id_robot.strip():
            raise ValueError("El robot necesita un identificador")
        if not isinstance(ubicacion, Ubicacion):
            raise TypeError("La ubicación debe ser una Ubicacion")
        if carga_maxima_kg <= 0:
            raise ValueError("La carga máxima debe ser mayor que 0")
        if velocidad_kmh <= 0:
            raise ValueError("La velocidad debe ser mayor que 0")
        self._id = id_robot.strip()
        self._ubicacion = ubicacion
        self._carga_maxima_kg = float(carga_maxima_kg)
        self._velocidad_kmh = float(velocidad_kmh)
        self._tiene_control_temperatura = tiene_control_temperatura
        self._bateria = Bateria(nivel_bateria)  # composición: nace con el robot
        self._estado = EstadoRobot.DISPONIBLE
        self._carga_actual = None

    # --- Lo que cada subtipo debe definir ---------------------------------
    @abstractmethod
    def zonas_accesibles(self) -> set[Zona]:
        ...

    @abstractmethod
    def costo_por_km(self) -> float:
        ...

    @abstractmethod
    def consumo_por_km(self) -> float:
        """Porcentaje de batería que gasta por kilómetro."""

    # --- Comportamiento por defecto (los subtipos lo redefinen si cambia) --
    def factor_ruta(self) -> float:
        return FACTOR_RODEO_TERRESTRE

    def requiere_clima(self) -> bool:
        return False

    def es_aereo(self) -> bool:
        return False

    def terreno_irregular(self) -> bool:
        return False

    # --- Cálculos comunes -------------------------------------------------
    def _distancia_ruta_km(self, origen: Ubicacion, destino: Ubicacion) -> float:
        return origen.distancia_km(destino) * self.factor_ruta()

    def calcular_tiempo_min(self, origen: Ubicacion, destino: Ubicacion) -> float:
        return self._distancia_ruta_km(origen, destino) / self._velocidad_kmh * 60

    # --- Consultas (solo lectura) -----------------------------------------
    @property
    def id(self) -> str:
        return self._id

    @property
    def ubicacion(self) -> Ubicacion:
        return self._ubicacion

    @property
    def carga_maxima_kg(self) -> float:
        return self._carga_maxima_kg

    @property
    def velocidad_kmh(self) -> float:
        return self._velocidad_kmh

    @property
    def tiene_control_temperatura(self) -> bool:
        return self._tiene_control_temperatura

    @property
    def nivel_bateria(self) -> float:
        return self._bateria.nivel

    @property
    def estado(self) -> EstadoRobot:
        return self._estado

    @property
    def carga_actual(self) -> Optional[object]:
        return self._carga_actual

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._id!r}, {self._estado.value}, {self.nivel_bateria:.0f} %)"


class RobotRuedas(Robot):
    """Rápido y económico; solo circula entre edificios."""

    def __init__(self, id_robot: str, ubicacion: Ubicacion, carga_maxima_kg: float = 20,
                 velocidad_kmh: float = 12, tiene_control_temperatura: bool = False,
                 nivel_bateria: float = 100.0):
        super().__init__(id_robot, ubicacion, carga_maxima_kg, velocidad_kmh,
                         tiene_control_temperatura, nivel_bateria)

    def zonas_accesibles(self) -> set[Zona]:
        return {Zona.EDIFICIO}

    def costo_por_km(self) -> float:
        return 1500

    def consumo_por_km(self) -> float:
        return 4


class RobotOrugas(Robot):
    """Lleva más peso y entra a zonas verdes, pero es lento y su terreno es irregular."""

    def __init__(self, id_robot: str, ubicacion: Ubicacion, carga_maxima_kg: float = 40,
                 velocidad_kmh: float = 6, tiene_control_temperatura: bool = False,
                 nivel_bateria: float = 100.0):
        super().__init__(id_robot, ubicacion, carga_maxima_kg, velocidad_kmh,
                         tiene_control_temperatura, nivel_bateria)

    def zonas_accesibles(self) -> set[Zona]:
        return {Zona.EDIFICIO, Zona.ZONA_VERDE}

    def costo_por_km(self) -> float:
        return 2500

    def consumo_por_km(self) -> float:
        return 6

    def terreno_irregular(self) -> bool:
        return True


class Dron(Robot):
    """Vuela en línea recta y llega a azoteas; depende del clima."""

    def __init__(self, id_robot: str, ubicacion: Ubicacion, carga_maxima_kg: float = 3,
                 velocidad_kmh: float = 30, tiene_control_temperatura: bool = False,
                 nivel_bateria: float = 100.0):
        super().__init__(id_robot, ubicacion, carga_maxima_kg, velocidad_kmh,
                         tiene_control_temperatura, nivel_bateria)

    def zonas_accesibles(self) -> set[Zona]:
        return {Zona.EDIFICIO, Zona.ZONA_VERDE, Zona.AZOTEA}

    def costo_por_km(self) -> float:
        return 4000

    def consumo_por_km(self) -> float:
        return 10

    def factor_ruta(self) -> float:
        return 1.0

    def requiere_clima(self) -> bool:
        return True

    def es_aereo(self) -> bool:
        return True
