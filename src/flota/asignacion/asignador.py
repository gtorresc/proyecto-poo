"""Asignador: elige el robot compatible más barato y consulta el clima solo si hace falta."""
from flota.dominio.bitacora import Bitacora, TipoEvento
from flota.dominio.flota import Flota
from flota.dominio.solicitud import EstadoSolicitud, SolicitudEntrega
from flota.servicios.proveedor_clima import ProveedorClima


class AsignadorEntregas:

    def __init__(self, flota: Flota, proveedor_clima: ProveedorClima, bitacora: Bitacora):
        self._flota = flota
        self._proveedor_clima = proveedor_clima
        self._bitacora = bitacora
        self._pendientes: list[SolicitudEntrega] = []

    def cambiar_proveedor_clima(self, proveedor: ProveedorClima) -> None:
        if not isinstance(proveedor, ProveedorClima):
            raise TypeError("El proveedor debe ser un ProveedorClima")
        self._proveedor_clima = proveedor

    @property
    def pendientes(self) -> tuple[SolicitudEntrega, ...]:
        return tuple(self._pendientes)

    def asignar(self, solicitud: SolicitudEntrega) -> bool:
        """True si un robot quedó asignado; si no, la solicitud queda pendiente y se reintentará."""
        asignada, motivo = self._intentar(solicitud)
        if not asignada and solicitud not in self._pendientes:
            solicitud.marcar_pendiente(motivo)
            self._pendientes.append(solicitud)
            self._bitacora.registrar(TipoEvento.SOLICITUD_PENDIENTE,
                                     f"Solicitud {solicitud.id}: {motivo}")
        return asignada

    def completar_entrega(self, solicitud: SolicitudEntrega) -> None:
        robot = solicitud.robot
        if solicitud.estado is not EstadoSolicitud.ASIGNADA:
            raise ValueError(f"Solicitud {solicitud.id} no está asignada")
        robot.entregar(solicitud.destino)
        solicitud.marcar_entregada()
        self._bitacora.registrar(TipoEvento.ENTREGA_EXITOSA,
                                 f"Solicitud {solicitud.id} entregada en {solicitud.destino.nombre}",
                                 robot.id)
        if robot.necesita_mantenimiento():
            robot.enviar_a_mantenimiento()
            self._bitacora.registrar(TipoEvento.MANTENIMIENTO,
                                     "Batería bajo la reserva: enviado a recargar", robot.id)
        self.reintentar_pendientes()

    def reintentar_pendientes(self) -> int:
        """Devuelve cuántas pendientes lograron asignarse."""
        logradas = 0
        for solicitud in list(self._pendientes):
            if self._intentar(solicitud)[0]:
                self._pendientes.remove(solicitud)
                logradas += 1
        return logradas

    def _intentar(self, solicitud: SolicitudEntrega) -> tuple[bool, str]:
        reporte = None  # se pide una sola vez, y solo si un dron llega a ser el siguiente más barato
        aptos = [(r.calcular_costo(solicitud.origen, solicitud.destino, solicitud.carga), r)
                 for r in self._flota.disponibles() if r.puede_atender(solicitud)]
        elegido, rechazada_por_clima = None, False
        for costo, robot in sorted(aptos, key=lambda c: c[0]):
            if robot.requiere_clima():
                if reporte is None:
                    reporte = self._proveedor_clima.obtener_reporte(solicitud.destino)
                favorable, motivo = reporte.es_favorable(self._proveedor_clima.umbrales)
                if not favorable:
                    self._bitacora.registrar(TipoEvento.RECHAZO_CLIMA,
                                             f"Solicitud {solicitud.id}: {motivo}", robot.id)
                    rechazada_por_clima = True
                    continue
            elegido = costo, robot
            break
        if elegido is None:
            return False, ("clima desfavorable para el dron" if rechazada_por_clima
                           else "ningún robot disponible puede atenderla")
        costo, robot = elegido
        tiempo = (robot.calcular_tiempo_min(robot.ubicacion, solicitud.origen)
                  + robot.calcular_tiempo_min(solicitud.origen, solicitud.destino))
        robot.cargar(solicitud.carga, solicitud.origen)
        solicitud.asignar(robot, costo, tiempo)
        return True, ""
