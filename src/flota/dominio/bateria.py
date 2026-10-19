"""Batería de un robot: protege su nivel entre 0 % y 100 %."""

NIVEL_MAXIMO = 100.0


class Bateria:
    """Cada robot crea y contiene su propia batería (composición)."""

    def __init__(self, nivel: float = NIVEL_MAXIMO, reserva_minima: float = 15.0):
        if not 0 <= nivel <= NIVEL_MAXIMO:
            raise ValueError(f"Nivel de batería fuera de rango: {nivel}")
        if not 0 <= reserva_minima < NIVEL_MAXIMO:
            raise ValueError(f"Reserva mínima fuera de rango: {reserva_minima}")
        self._nivel = float(nivel)
        self._reserva_minima = float(reserva_minima)

    @property
    def nivel(self) -> float:
        return self._nivel

    @property
    def reserva_minima(self) -> float:
        return self._reserva_minima

    def consumir(self, porcentaje: float) -> None:
        """Descuenta energía; no permite quedar por debajo de 0 %."""
        if porcentaje < 0:
            raise ValueError("No se puede consumir un porcentaje negativo")
        if porcentaje > self._nivel:
            raise ValueError(
                f"Batería insuficiente: se piden {porcentaje:.1f} % y quedan {self._nivel:.1f} %"
            )
        self._nivel -= porcentaje

    def recargar(self) -> None:
        self._nivel = NIVEL_MAXIMO

    def alcanza_para(self, porcentaje: float) -> bool:
        """True si tras consumir `porcentaje` queda al menos la reserva mínima."""
        return self._nivel - porcentaje >= self._reserva_minima

    def __repr__(self) -> str:
        return f"Bateria({self._nivel:.1f} %)"
