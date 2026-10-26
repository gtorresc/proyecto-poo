"""Asignador: elige el robot compatible más barato y consulta el clima solo si hace falta."""
import time
from typing import Callable

from flota.dominio.bitacora import Bitacora, TipoEvento
from flota.dominio.flota import Flota
from flota.dominio.solicitud import EstadoSolicitud, SolicitudEntrega
from flota.servicios.proveedor_clima import ProveedorClima

DURACION_MANTENIMIENTO_S = 30.0  # tiempo de recarga antes de volver a la flota


class AsignadorEntregas:

    def __init__(self, flota: Flota, proveedor_clima: ProveedorClima, bitacora: Bitacora,
                 reloj: Callable[[], float] = time.monotonic):
        self._flota = flota
        self._proveedor_clima = proveedor_clima
        self._bitacora = bitacora
        self._reloj = reloj
        self._pendientes: dict[int, SolicitudEntrega] = {}  # id -> solicitud, en orden de llegada
        self._en_curso: dict[int, SolicitudEntrega] = {}    # asignadas y aún sin entregar
        self._en_mantenimiento: dict[str, float] = {}       # id del robot -> instante en que sale

    @property
    def proveedor_clima(self) -> ProveedorClima:
        return self._proveedor_clima

    def cambiar_proveedor_clima(self, proveedor: ProveedorClima) -> None:
        if not isinstance(proveedor, ProveedorClima):
            raise TypeError("El proveedor debe ser un ProveedorClima")
        self._proveedor_clima = proveedor

    @property
    def pendientes(self) -> tuple[SolicitudEntrega, ...]:
        return tuple(self._pendientes.values())

    @property
    def en_curso(self) -> tuple[SolicitudEntrega, ...]:
        return tuple(self._en_curso.values())

    def asignar(self, solicitud: SolicitudEntrega) -> bool:
        """True si un robot quedó asignado; si no, la solicitud queda pendiente y se reintentará."""
        if solicitud.estado is not EstadoSolicitud.PENDIENTE:  # antes de tocar ningún robot
            raise ValueError(f"Solicitud {solicitud.id} ya está {solicitud.estado.value}")
        asignada, motivo = self._intentar(solicitud)
        if asignada:
            self._pendientes.pop(solicitud.id, None)
        elif solicitud.id not in self._pendientes:
            solicitud.marcar_pendiente(motivo)
            self._pendientes[solicitud.id] = solicitud
            self._bitacora.registrar(TipoEvento.SOLICITUD_PENDIENTE,
                                     f"Solicitud {solicitud.id}: {motivo}")
        return asignada

    def completar_entrega(self, solicitud: SolicitudEntrega) -> None:
        robot = solicitud.robot
        if solicitud.estado is not EstadoSolicitud.ASIGNADA:
            raise ValueError(f"Solicitud {solicitud.id} no está asignada")
        robot.entregar(solicitud.destino)
        solicitud.marcar_entregada()
        del self._en_curso[solicitud.id]
        self._bitacora.registrar(TipoEvento.ENTREGA_EXITOSA,
                                 f"Solicitud {solicitud.id} entregada en {solicitud.destino.nombre}",
                                 robot.id)
        if robot.necesita_mantenimiento():
            robot.enviar_a_mantenimiento()
            self._en_mantenimiento[robot.id] = self._reloj() + DURACION_MANTENIMIENTO_S
            self._bitacora.registrar(TipoEvento.MANTENIMIENTO,
                                     "Batería bajo la reserva: enviado a recargar", robot.id)
        self.reintentar_pendientes()

    def reintentar_pendientes(self) -> int:
        """Devuelve cuántas pendientes lograron asignarse."""
        self.liberar_mantenimientos()
        logradas = 0
        for solicitud in list(self._pendientes.values()):
            if self._intentar(solicitud)[0]:
                del self._pendientes[solicitud.id]
                logradas += 1
        return logradas

    def liberar_mantenimientos(self) -> int:
        """Devuelve a la flota los robots que ya cumplieron su recarga; dice cuántos salieron."""
        ahora = self._reloj()
        listos = [id_robot for id_robot, salida in self._en_mantenimiento.items() if salida <= ahora]
        for id_robot in listos:
            del self._en_mantenimiento[id_robot]
            robot = self._flota.buscar(id_robot)
            if robot is not None:  # pudo quitarse de la flota mientras se recargaba
                robot.terminar_mantenimiento()
                self._bitacora.registrar(TipoEvento.MANTENIMIENTO, "Recargado: vuelve a la flota", id_robot)
        return len(listos)

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
        self._en_curso[solicitud.id] = solicitud
        return True, ""
