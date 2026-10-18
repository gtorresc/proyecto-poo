"""Estados posibles de un robot de la flota."""
from enum import Enum


class EstadoRobot(Enum):
    DISPONIBLE = "disponible"
    EN_RUTA = "en ruta"
    MANTENIMIENTO = "mantenimiento"
