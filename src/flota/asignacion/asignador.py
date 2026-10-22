"""Asignador: elige el robot compatible más barato y consulta el clima solo si hace falta."""
from flota.dominio.bitacora import Bitacora, TipoEvento
from flota.dominio.flota import Flota
from flota.dominio.solicitud import SolicitudEntrega
from flota.servicios.proveedor_clima import ProveedorClima


class AsignadorEntregas:

    def __init__(self, flota: Flota, proveedor_clima: ProveedorClima, bitacora: Bitacora):
        self._flota = flota
        self._proveedor_clima = proveedor_clima
        self._bitacora = bitacora

    def cambiar_proveedor_clima(self, proveedor: ProveedorClima) -> None:
        if not isinstance(proveedor, ProveedorClima):
            raise TypeError("El proveedor debe ser un ProveedorClima")
        self._proveedor_clima = proveedor

    def asignar(self, solicitud: SolicitudEntrega) -> bool:
        """True si un robot quedó asignado; si no, False (el motivo queda en la bitácora)."""
        reporte = None  # se pide una sola vez, y solo si un dron llega a ser el siguiente más barato
        aptos = [(r.calcular_costo(solicitud.origen, solicitud.destino, solicitud.carga), r)
                 for r in self._flota.disponibles() if r.puede_atender(solicitud)]
        elegido = None
        for costo, robot in sorted(aptos, key=lambda c: c[0]):
            if robot.requiere_clima():
                if reporte is None:
                    reporte = self._proveedor_clima.obtener_reporte(solicitud.destino)
                favorable, motivo = reporte.es_favorable(self._proveedor_clima.umbrales)
                if not favorable:
                    self._bitacora.registrar(TipoEvento.RECHAZO_CLIMA,
                                             f"Solicitud {solicitud.id}: {motivo}", robot.id)
                    continue
            elegido = costo, robot
            break
        if elegido is None:
            return False
        costo, robot = elegido
        tiempo = (robot.calcular_tiempo_min(robot.ubicacion, solicitud.origen)
                  + robot.calcular_tiempo_min(solicitud.origen, solicitud.destino))
        robot.cargar(solicitud.carga, solicitud.origen)
        solicitud.asignar(robot, costo, tiempo)
        return True
