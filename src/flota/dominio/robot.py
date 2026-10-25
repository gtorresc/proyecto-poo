"""Robots de la flota: una clase abstracta y un subtipo por forma de moverse."""
from abc import ABC, abstractmethod
from typing import Optional

from flota.dominio.bateria import Bateria
from flota.dominio.estado_robot import EstadoRobot
from flota.dominio.ruta import RedSenderos, Ruta
from flota.dominio.ubicacion import Ubicacion, Zona

MARGEN_MANTENIMIENTO = 10  # puntos de batería sobre la reserva que disparan el mantenimiento
FACTOR_RODEO_TERRESTRE = 1.3  # supuesto S5: rodeo estimado cuando no hay red de senderos


class Robot(ABC):
    """Lo común a todos los robots. Cada subtipo define zonas, costo y consumo."""

    def __init__(self, id_robot: str, ubicacion: Ubicacion, carga_maxima_kg: float,
                 velocidad_kmh: float, tiene_control_temperatura: bool = False,
                 nivel_bateria: float = 100.0, red: Optional[RedSenderos] = None):
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
        self._red = red  # asociación: todos los robots comparten la misma red del campus

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
    def trazar_ruta(self, origen: Ubicacion, destino: Ubicacion) -> Ruta:
        """Por tierra: el camino más corto por los senderos. Sin red (o sin camino), se estima el rodeo."""
        ruta = self._red.ruta(origen, destino) if self._red is not None else None
        return ruta or Ruta.linea_recta(origen, destino, self.factor_ruta())

    def _distancia_ruta_km(self, origen: Ubicacion, destino: Ubicacion) -> float:
        return self.trazar_ruta(origen, destino).distancia_km

    def calcular_tiempo_min(self, origen: Ubicacion, destino: Ubicacion) -> float:
        return self._distancia_ruta_km(origen, destino) / self._velocidad_kmh * 60

    def calcular_costo(self, origen: Ubicacion, destino: Ubicacion, carga) -> float:
        return self._distancia_ruta_km(origen, destino) * self.costo_por_km() * carga.recargo()

    def _consumo_viaje(self, hasta: Ubicacion) -> float:
        return self._distancia_ruta_km(self._ubicacion, hasta) * self.consumo_por_km()

    def puede_atender(self, solicitud) -> bool:
        """Estado, peso, zonas, tipo de carga y batería (ida al origen + entrega con reserva)."""
        carga = solicitud.carga
        zonas = self.zonas_accesibles()
        consumo = (self._consumo_viaje(solicitud.origen)
                   + self._distancia_ruta_km(solicitud.origen, solicitud.destino) * self.consumo_por_km())
        return (self._estado is EstadoRobot.DISPONIBLE
                and carga.peso_kg <= self._carga_maxima_kg
                and solicitud.origen.zona in zonas
                and solicitud.destino.zona in zonas
                and carga.es_compatible_con(self)
                and self._bateria.alcanza_para(consumo))

    # --- Operación: cada método cambia el estado del robot -----------------
    def cargar(self, carga, origen: Optional[Ubicacion] = None) -> None:
        """Recoge la carga; si se da `origen`, el robot viaja allí primero y gasta batería."""
        if self._estado is not EstadoRobot.DISPONIBLE:
            raise ValueError(f"{self._id} no está disponible ({self._estado.value})")
        if carga.peso_kg > self._carga_maxima_kg:
            raise ValueError(f"{self._id} no soporta {carga.peso_kg} kg")
        if not carga.es_compatible_con(self):
            raise ValueError(f"{self._id} no es compatible con {carga!r}")
        if origen is not None:
            self._bateria.consumir(self._consumo_viaje(origen))
            self._ubicacion = origen
        self._carga_actual = carga
        self._estado = EstadoRobot.EN_RUTA

    def entregar(self, destino: Ubicacion) -> None:
        if self._estado is not EstadoRobot.EN_RUTA or self._carga_actual is None:
            raise ValueError(f"{self._id} no lleva ninguna carga")
        self._bateria.consumir(self._consumo_viaje(destino))
        self._ubicacion = destino
        self._carga_actual = None
        self._estado = EstadoRobot.DISPONIBLE

    def enviar_a_mantenimiento(self) -> None:
        """Recarga la batería; el robot no recibe entregas hasta `terminar_mantenimiento`."""
        if self._estado is EstadoRobot.EN_RUTA:
            raise ValueError(f"{self._id} lleva una carga y no puede entrar a mantenimiento")
        self._bateria.recargar()
        self._estado = EstadoRobot.MANTENIMIENTO

    def necesita_mantenimiento(self) -> bool:
        # puede_atender ya garantiza que nunca baje de la reserva, así que se recarga al acercarse
        return self._bateria.nivel <= self._bateria.reserva_minima + MARGEN_MANTENIMIENTO

    def terminar_mantenimiento(self) -> None:
        if self._estado is not EstadoRobot.MANTENIMIENTO:
            raise ValueError(f"{self._id} no está en mantenimiento")
        self._estado = EstadoRobot.DISPONIBLE

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
                 nivel_bateria: float = 100.0, red: Optional[RedSenderos] = None):
        super().__init__(id_robot, ubicacion, carga_maxima_kg, velocidad_kmh,
                         tiene_control_temperatura, nivel_bateria, red)

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
                 nivel_bateria: float = 100.0, red: Optional[RedSenderos] = None):
        super().__init__(id_robot, ubicacion, carga_maxima_kg, velocidad_kmh,
                         tiene_control_temperatura, nivel_bateria, red)

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
                 nivel_bateria: float = 100.0, red: Optional[RedSenderos] = None):
        super().__init__(id_robot, ubicacion, carga_maxima_kg, velocidad_kmh,
                         tiene_control_temperatura, nivel_bateria, red)

    def zonas_accesibles(self) -> set[Zona]:
        return {Zona.EDIFICIO, Zona.ZONA_VERDE, Zona.AZOTEA}

    def costo_por_km(self) -> float:
        return 4000

    def consumo_por_km(self) -> float:
        return 10

    def trazar_ruta(self, origen: Ubicacion, destino: Ubicacion) -> Ruta:
        return Ruta.linea_recta(origen, destino)  # vuela: no sigue senderos

    def requiere_clima(self) -> bool:
        return True

    def es_aereo(self) -> bool:
        return True
