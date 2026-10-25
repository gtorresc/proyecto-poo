"""Asignador: elige el robot compatible más barato y consulta el clima solo si hace falta."""
from datetime import date
from typing import Optional

from flota.dominio.bitacora import Bitacora, TipoEvento
from flota.dominio.flota import Flota
from flota.dominio.solicitud import EstadoSolicitud, SolicitudEntrega
from flota.servicios.proveedor_calendario import ProveedorCalendario
from flota.servicios.proveedor_clima import ProveedorClima


class AsignadorEntregas:

    def __init__(self, flota: Flota, proveedor_clima: ProveedorClima, bitacora: Bitacora,
                 calendario: Optional[ProveedorCalendario] = None):
        self._flota = flota
        self._proveedor_clima = proveedor_clima
        self._bitacora = bitacora
        self._calendario = calendario  # sin calendario no se aplica la regla de festivos
        self._pendientes: list[SolicitudEntrega] = []
        self._en_curso: list[SolicitudEntrega] = []  # asignadas y aún sin entregar

    @property
    def proveedor_clima(self) -> ProveedorClima:
        return self._proveedor_clima

    def cambiar_proveedor_clima(self, proveedor: ProveedorClima) -> None:
        if not isinstance(proveedor, ProveedorClima):
            raise TypeError("El proveedor debe ser un ProveedorClima")
        self._proveedor_clima = proveedor

    @property
    def calendario(self) -> Optional[ProveedorCalendario]:
        return self._calendario

    def cambiar_calendario(self, calendario: Optional[ProveedorCalendario]) -> None:
        if calendario is not None and not isinstance(calendario, ProveedorCalendario):
            raise TypeError("El calendario debe ser un ProveedorCalendario")
        self._calendario = calendario

    @property
    def pendientes(self) -> tuple[SolicitudEntrega, ...]:
        return tuple(self._pendientes)

    @property
    def en_curso(self) -> tuple[SolicitudEntrega, ...]:
        return tuple(self._en_curso)

    def asignar(self, solicitud: SolicitudEntrega) -> bool:
        """True si un robot quedó asignado; si no, la solicitud queda pendiente y se reintentará."""
        asignada, motivo = self._intentar(solicitud)
        if not asignada and solicitud not in self._pendientes:
            solicitud.marcar_pendiente(motivo)
            self._pendientes.append(solicitud)
            self._bitacora.registrar(TipoEvento.SOLICITUD_PENDIENTE,
                                     f"Solicitud {solicitud.id}: {motivo}")
        return asignada

    def despachar(self, solicitud: SolicitudEntrega, robot) -> tuple[bool, str]:
        """Despacho manual: el operador elige el robot y el sistema valida las mismas reglas.

        Si no se puede, devuelve el motivo y la solicitud sigue esperando al operador
        (no entra a la cola de reintentos automáticos)."""
        if self._flota.buscar(robot.id) is not robot:
            raise ValueError(f"{robot.id} no pertenece a la flota")
        motivo = self._motivo_festivo(solicitud) or robot.motivo_rechazo(solicitud)
        if motivo is None and robot.requiere_clima():
            reporte = self._proveedor_clima.obtener_reporte(solicitud.destino)
            favorable, detalle = reporte.es_favorable(self._proveedor_clima.umbrales)
            if not favorable:
                self._bitacora.registrar(TipoEvento.RECHAZO_CLIMA,
                                         f"Solicitud {solicitud.id}: {detalle}", robot.id)
                motivo = f"clima desfavorable: {detalle}"
        if motivo is not None:
            solicitud.marcar_pendiente(motivo)
            self._bitacora.registrar(TipoEvento.DESPACHO_RECHAZADO,
                                     f"Solicitud {solicitud.id}: {motivo}", robot.id)
            return False, motivo
        self._asignar_a(solicitud, robot)
        if solicitud in self._pendientes:  # el operador puede despachar una que esperaba reintento
            self._pendientes.remove(solicitud)
        return True, ""

    def completar_entrega(self, solicitud: SolicitudEntrega) -> None:
        robot = solicitud.robot
        if solicitud.estado is not EstadoSolicitud.ASIGNADA:
            raise ValueError(f"Solicitud {solicitud.id} no está asignada")
        robot.entregar(solicitud.destino)
        solicitud.marcar_entregada()
        self._en_curso.remove(solicitud)
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

    def _motivo_festivo(self, solicitud: SolicitudEntrega) -> Optional[str]:
        if solicitud.carga.requiere_cafeteria() and self._calendario is not None:
            festivo = self._calendario.festivo(date.today())
            if festivo:
                return f"cafetería cerrada (festivo: {festivo})"
        return None

    def _intentar(self, solicitud: SolicitudEntrega) -> tuple[bool, str]:
        motivo = self._motivo_festivo(solicitud)
        if motivo:
            return False, motivo
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
        self._asignar_a(solicitud, elegido[1], elegido[0])
        return True, ""

    def _asignar_a(self, solicitud: SolicitudEntrega, robot, costo: Optional[float] = None) -> None:
        if costo is None:
            costo = robot.calcular_costo(solicitud.origen, solicitud.destino, solicitud.carga)
        tiempo = (robot.calcular_tiempo_min(robot.ubicacion, solicitud.origen)
                  + robot.calcular_tiempo_min(solicitud.origen, solicitud.destino))
        robot.cargar(solicitud.carga, solicitud.origen)
        solicitud.asignar(robot, costo, tiempo)
        self._en_curso.append(solicitud)
