"""Asignador: elige el robot compatible más barato y consulta el clima solo si hace falta."""
import time
from datetime import date
from typing import Callable, Optional

from flota.dominio.bitacora import Bitacora, TipoEvento
from flota.dominio.flota import Flota
from flota.dominio.solicitud import EstadoSolicitud, SolicitudEntrega
from flota.servicios.proveedor_calendario import ProveedorCalendario
from flota.servicios.proveedor_clima import ProveedorClima

DURACION_MANTENIMIENTO_S = 30.0  # tiempo de recarga antes de volver a la flota


class AsignadorEntregas:

    def __init__(self, flota: Flota, proveedor_clima: ProveedorClima, bitacora: Bitacora,
                 calendario: Optional[ProveedorCalendario] = None,
                 reloj: Callable[[], float] = time.monotonic):
        self._flota = flota
        self._proveedor_clima = proveedor_clima
        self._bitacora = bitacora
        self._calendario = calendario  # sin calendario no se aplica la regla de festivos
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
    def calendario(self) -> Optional[ProveedorCalendario]:
        return self._calendario

    def cambiar_calendario(self, calendario: Optional[ProveedorCalendario]) -> None:
        if calendario is not None and not isinstance(calendario, ProveedorCalendario):
            raise TypeError("El calendario debe ser un ProveedorCalendario")
        self._calendario = calendario

    @property
    def pendientes(self) -> tuple[SolicitudEntrega, ...]:
        return tuple(self._pendientes.values())

    @property
    def en_curso(self) -> tuple[SolicitudEntrega, ...]:
        return tuple(self._en_curso.values())

    def asignar(self, solicitud: SolicitudEntrega) -> bool:
        """True si un robot quedó asignado. Si no, la solicitud queda pendiente y se reintentará,
        o falla si ningún robot de la flota podría atenderla nunca."""
        if solicitud.estado is not EstadoSolicitud.PENDIENTE:  # antes de tocar ningún robot
            raise ValueError(f"Solicitud {solicitud.id} ya está {solicitud.estado.value}")
        imposible = self._motivo_imposible(solicitud)
        if imposible:
            solicitud.marcar_fallida(imposible)
            self._pendientes.pop(solicitud.id, None)
            self._bitacora.registrar(TipoEvento.ENTREGA_FALLIDA, f"Solicitud {solicitud.id}: {imposible}")
            return False
        asignada, motivo = self._intentar(solicitud)
        if asignada:
            self._pendientes.pop(solicitud.id, None)
        elif solicitud.id not in self._pendientes:
            solicitud.marcar_pendiente(motivo)
            self._pendientes[solicitud.id] = solicitud
            self._bitacora.registrar(TipoEvento.SOLICITUD_PENDIENTE,
                                     f"Solicitud {solicitud.id}: {motivo}")
        return asignada

    def despachar(self, solicitud: SolicitudEntrega, robot) -> tuple[bool, str]:
        """Despacho manual: el operador elige el robot y el sistema valida las mismas reglas.

        Si no se puede, devuelve el motivo y la solicitud sigue esperando al operador
        (no entra a la cola de reintentos automáticos)."""
        if solicitud.estado is not EstadoSolicitud.PENDIENTE:  # antes de cargar el robot, como en asignar
            raise ValueError(f"Solicitud {solicitud.id} ya está {solicitud.estado.value}")
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
        self._pendientes.pop(solicitud.id, None)  # el operador puede despachar una que esperaba reintento
        return True, ""

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
            # el rechazo por clima ya quedó en la bitácora la primera vez: no se repite en cada intento
            asignada, motivo = self._intentar(solicitud, registrar=False)
            if asignada:
                del self._pendientes[solicitud.id]
                logradas += 1
            else:
                solicitud.marcar_pendiente(motivo)  # el motivo puede haber cambiado (clima, festivo...)
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

    def _motivo_imposible(self, solicitud: SolicitudEntrega) -> Optional[str]:
        """Si ningún robot de la flota la atendería aunque esperara (peso, zonas o tipo de carga), por qué."""
        motivos = [r.motivo_incapaz(solicitud) for r in self._flota.robots]
        if not motivos or None in motivos:  # sin robots todavía puede llegar uno: se espera
            return None
        return "ningún robot de la flota puede llevarla (" + "; ".join(motivos) + ")"

    def _motivo_festivo(self, solicitud: SolicitudEntrega) -> Optional[str]:
        if solicitud.carga.requiere_cafeteria() and self._calendario is not None:
            festivo = self._calendario.festivo(date.today())
            if festivo:
                return f"cafetería cerrada (festivo: {festivo})"
        return None

    def _intentar(self, solicitud: SolicitudEntrega, registrar: bool = True) -> tuple[bool, str]:
        motivo = self._motivo_festivo(solicitud)
        if motivo:
            return False, motivo
        reporte = None  # se pide una sola vez, y solo si un dron llega a ser el siguiente más barato
        aptos = [(r.calcular_costo(solicitud.origen, solicitud.destino, solicitud.carga), r)
                 for r in self._flota.disponibles() if r.puede_atender(solicitud)]
        elegido, rechazada_por_clima = None, False
        # a igual costo, el que llega antes al origen (el costo solo mide el tramo origen -> destino)
        cercania = lambda c: (c[0], c[1].calcular_tiempo_min(c[1].ubicacion, solicitud.origen))
        for costo, robot in sorted(aptos, key=cercania):
            if robot.requiere_clima():
                if reporte is None:
                    reporte = self._proveedor_clima.obtener_reporte(solicitud.destino)
                favorable, motivo = reporte.es_favorable(self._proveedor_clima.umbrales)
                if not favorable:
                    if registrar:
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
        self._en_curso[solicitud.id] = solicitud
