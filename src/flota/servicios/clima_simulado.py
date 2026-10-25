"""Clima controlado a mano: sirve para demos, tests y la GUI sin internet."""
from typing import Optional

from flota.dominio.ubicacion import Ubicacion
from flota.servicios.proveedor_clima import ProveedorClima, ReporteClima, UmbralesClima


class ServicioClimaSimulado(ProveedorClima):

    def __init__(self, umbrales: Optional[UmbralesClima] = None, viento_kmh: float = 10,
                 rafagas_kmh: float = 15, prob_lluvia_pct: float = 10, es_de_dia: bool = True):
        super().__init__(umbrales)
        self.configurar(viento_kmh, rafagas_kmh, prob_lluvia_pct, es_de_dia)

    def configurar(self, viento: float, rafagas: float, lluvia: float, dia: bool,
                   visibilidad: float = 10_000, tormenta: bool = False,
                   humedad: float = 70, direccion: float = 180) -> None:
        self._reporte = ReporteClima(viento, rafagas, lluvia, dia, visibilidad_m=visibilidad,
                                     tormenta=tormenta, humedad_pct=humedad,
                                     direccion_viento_grados=direccion)  # valida los rangos

    def obtener_reporte(self, ubicacion: Ubicacion) -> ReporteClima:
        return self._reporte
