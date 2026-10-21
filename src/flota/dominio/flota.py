"""Flota: agrega robots que existen por sí mismos (agregación, no composición)."""
from typing import Optional

from flota.dominio.estado_robot import EstadoRobot
from flota.dominio.robot import Robot


class Flota:

    def __init__(self):
        self._robots: list[Robot] = []

    @property
    def robots(self) -> list[Robot]:
        return list(self._robots)  # copia: la lista interna solo cambia con agregar/quitar

    def agregar(self, robot: Robot) -> None:
        if not isinstance(robot, Robot):
            raise TypeError("Solo se pueden agregar robots")
        if self.buscar(robot.id) is not None:
            raise ValueError(f"Ya existe un robot con id {robot.id}")
        self._robots.append(robot)

    def quitar(self, id_robot: str) -> None:
        robot = self.buscar(id_robot)
        if robot is None:
            raise ValueError(f"No existe el robot {id_robot}")
        if robot.estado is EstadoRobot.EN_RUTA:
            raise ValueError(f"{id_robot} está en ruta y no se puede quitar")
        self._robots.remove(robot)

    def buscar(self, id_robot: str) -> Optional[Robot]:
        return next((r for r in self._robots if r.id == id_robot), None)

    def disponibles(self) -> list[Robot]:
        return [r for r in self._robots if r.estado is EstadoRobot.DISPONIBLE]
