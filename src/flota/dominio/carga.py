"""Tipos de carga: cada uno decide su recargo y con qué robots es compatible."""
from abc import ABC, abstractmethod


class Carga(ABC):

    def __init__(self, descripcion: str, peso_kg: float):
        if not descripcion or not descripcion.strip():
            raise ValueError("La carga necesita una descripción")
        if peso_kg <= 0:
            raise ValueError("El peso debe ser mayor que 0")
        self._descripcion = descripcion.strip()
        self._peso_kg = float(peso_kg)

    @property
    def descripcion(self) -> str:
        return self._descripcion

    @property
    def peso_kg(self) -> float:
        return self._peso_kg

    @abstractmethod
    def recargo(self) -> float:
        """Multiplicador sobre el costo de la entrega."""

    def es_compatible_con(self, robot) -> bool:
        # Se consultan capacidades del robot, nunca su subclase (decisión D4)
        return True

    def requiere_cafeteria(self) -> bool:
        """Si sale de la cafetería, que cierra en festivos."""
        return False

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._descripcion!r}, {self._peso_kg} kg)"


class Documento(Carga):
    def recargo(self) -> float:
        return 1.0


class Alimento(Carga):

    def __init__(self, descripcion: str, peso_kg: float, temperatura_c: float):
        super().__init__(descripcion, peso_kg)
        self._temperatura_c = float(temperatura_c)

    @property
    def temperatura_c(self) -> float:
        return self._temperatura_c

    def recargo(self) -> float:
        return 1.2

    def es_compatible_con(self, robot) -> bool:
        return robot.tiene_control_temperatura

    def requiere_cafeteria(self) -> bool:
        return True


class Fragil(Carga):
    def recargo(self) -> float:
        return 1.3

    def es_compatible_con(self, robot) -> bool:
        return not robot.terreno_irregular()


class MaterialPeligroso(Carga):

    def __init__(self, descripcion: str, peso_kg: float, nivel_riesgo: int):
        super().__init__(descripcion, peso_kg)
        if nivel_riesgo not in (1, 2, 3):
            raise ValueError("El nivel de riesgo va de 1 a 3")
        self._nivel_riesgo = nivel_riesgo

    @property
    def nivel_riesgo(self) -> int:
        return self._nivel_riesgo

    def recargo(self) -> float:
        return 1.5

    def es_compatible_con(self, robot) -> bool:
        return not robot.es_aereo()  # supuesto S6: nunca en dron
