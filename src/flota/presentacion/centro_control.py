"""Modelo de presentación: lo que la interfaz web muestra y pide.

No sabe de HTML ni de JavaScript. Traduce el dominio a datos simples (dicts, listas, números) y
convierte los clics del operador en llamadas al dominio. Las reglas siguen en el dominio.
"""
import math
import random
import threading
import time
from datetime import date

from flota.asignacion.asignador import AsignadorEntregas
from flota.campus import cargar_campus, cargar_geometria
from flota.dominio.bitacora import Bitacora
from flota.dominio.carga import Alimento, Documento, Fragil, MaterialPeligroso
from flota.dominio.estado_robot import EstadoRobot
from flota.dominio.solicitud import SolicitudEntrega
from flota.servicios.calendario_nager_date import CalendarioNagerDate
from flota.servicios.calendario_simulado import CalendarioSimulado
from flota.servicios.clima_open_meteo import ServicioClimaOpenMeteo
from flota.servicios.clima_simulado import ServicioClimaSimulado

CENTRO_CAMPUS = (6.2316146, -75.6111419)  # Plaza de Prometeo: el (0, 0) del mapa en metros
METROS_POR_GRADO_LAT = 110_574
METROS_POR_GRADO_LON = 111_320 * math.cos(math.radians(CENTRO_CAMPUS[0]))
METROS_POR_PISO = 3.5
PISOS_POR_DEFECTO = 2  # OSM solo trae los pisos de unos pocos edificios
SEGUNDOS_POR_MINUTO = 6  # 1 min de viaje simulado = 6 s en pantalla
MIN_VIAJE_S = 3  # los tramos cortos durarían menos de un parpadeo
ALTURA_VUELO_M = 30
SEPARACION_M = 24  # robots quietos en el mismo lugar se dibujan en ronda, para que no se tapen
EVENTOS_VISIBLES = 50
NUBES = 10  # cuántas nubes cruzan el mapa como máximo
REFRESCO_CLIMA_S = 300  # el clima real se vuelve a leer cada 5 min (la píldora no queda con el dato del arranque)

TIPOS_CARGA = {  # clave -> (nombre en pantalla, fábrica a partir del peso)
    "documento": ("Documento", lambda peso: Documento("Documento", peso)),
    "alimento": ("Alimento", lambda peso: Alimento("Alimento", peso, 60)),
    "fragil": ("Frágil", lambda peso: Fragil("Carga frágil", peso)),
    "peligroso": ("Material peligroso", lambda peso: MaterialPeligroso("Material peligroso", peso, 2)),
}
FRANJA_ESTADO = {EstadoRobot.DISPONIBLE: "libre", EstadoRobot.EN_RUTA: "ocupado",
                 EstadoRobot.MANTENIMIENTO: "falla"}  # claves de color de la guía de estilo


def a_metros(lat: float, lon: float) -> tuple[float, float]:
    """(x hacia el este, y hacia el norte) en metros desde el centro del campus."""
    return ((lon - CENTRO_CAMPUS[1]) * METROS_POR_GRADO_LON,
            (lat - CENTRO_CAMPUS[0]) * METROS_POR_GRADO_LAT)


def dentro(punto, poligono) -> bool:
    """Punto en polígono por cruce de rayos; sirve igual en grados o en metros."""
    y, x = punto
    adentro = False
    for (y1, x1), (y2, x2) in zip(poligono, poligono[1:] + poligono[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            adentro = not adentro
    return adentro


def punto_en_recorrido(puntos: list, t: float) -> tuple[float, float]:
    """Posición a una fracción t (0 a 1) de la longitud de una polilínea."""
    tramos = [math.dist(a, b) for a, b in zip(puntos, puntos[1:])]
    falta = max(0.0, min(1.0, t)) * sum(tramos)
    for (a, b), largo in zip(zip(puntos, puntos[1:]), tramos):
        if falta <= largo and largo > 0:
            f = falta / largo
            return a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        falta -= largo
    return tuple(puntos[-1])


class CentroControl:

    def __init__(self, ubicaciones: dict, flota, asignador: AsignadorEntregas, bitacora: Bitacora,
                 geometria: dict, clima_real=None, calendario_real=None, reloj=time.monotonic):
        self._ubicaciones, self._flota = ubicaciones, flota
        self._asignador, self._bitacora, self._reloj = asignador, bitacora, reloj
        umbrales = asignador.proveedor_clima.umbrales
        self._clima_simulado = ServicioClimaSimulado(umbrales=umbrales)
        self._clima_real = clima_real or ServicioClimaOpenMeteo(umbrales=umbrales)
        self._calendario_simulado = CalendarioSimulado()
        self._calendario_real = calendario_real or CalendarioNagerDate()
        self._reporte = None   # lo escribe un hilo si el clima es real
        self._clima_leido = reloj()
        self._festivo = None   # nombre del festivo de hoy, o None
        self._bandeja: list[SolicitudEntrega] = []  # creadas, esperando que el operador las despache
        self._creada_en: dict[int, float] = {}
        self._viajes: dict[int, tuple[float, float, list]] = {}  # id solicitud -> (inicio, duración, puntos en m)
        # dónde estaba cada robot antes de su viaje: al asignarlo, el dominio ya lo deja en el origen
        self._de_donde: dict[str, object] = {r.id: r.ubicacion for r in flota.robots}
        self._geometria = self._preparar_geometria(geometria)

    # --- Datos fijos -------------------------------------------------------
    def _preparar_geometria(self, geo: dict) -> dict:
        metros = lambda puntos: [list(a_metros(*p)) for p in puntos]
        edificios = [{"nombre": e["nombre"], "contorno": metros(e["contorno"]),
                      "altura": (e["niveles"] or PISOS_POR_DEFECTO) * METROS_POR_PISO,
                      "en_campus": dentro(e["contorno"][0], geo["perimetro"])}
                     for e in geo["edificios"]]
        ubicaciones = []
        self._edificio_de = {}  # nombre de la ubicación -> índice de su edificio, para resaltarlo
        for clave, u in self._ubicaciones.items():
            x, y = a_metros(u.latitud, u.longitud)
            edificio = next((i for i, e in enumerate(geo["edificios"])
                             if dentro((u.latitud, u.longitud), e["contorno"])), None)
            self._edificio_de[u.nombre] = edificio
            ubicaciones.append({"clave": clave, "nombre": u.nombre, "zona": u.zona.value,
                                "x": x, "y": y, "edificio": edificio})
        sur_oeste = a_metros(geo["limites"]["sur"], geo["limites"]["oeste"])
        norte_este = a_metros(geo["limites"]["norte"], geo["limites"]["este"])
        azar = random.Random(7)  # fijo: las luces y las nubes salen igual en cada arranque
        nubes = [{"x": azar.uniform(sur_oeste[0], norte_este[0]), "y": azar.uniform(sur_oeste[1], norte_este[1]),
                  "radio": azar.uniform(70, 140), "semilla": azar.randrange(10_000)} for _ in range(NUBES)]
        return {"fuente": geo["fuente"], "limites": [*sur_oeste, *norte_este],
                "luces": [luz for e in edificios if e["en_campus"] for luz in _luces(e, azar)], "nubes": nubes,
                "perimetro": metros(geo["perimetro"]), "edificios": edificios,
                "caminos": [{"tipo": c["tipo"], "puntos": metros(c["puntos"])} for c in geo["caminos"]],
                "ubicaciones": ubicaciones,
                "tipos_carga": [{"clave": k, "nombre": v[0]} for k, v in TIPOS_CARGA.items()]}

    def geometria(self) -> dict:
        """Edificios (contorno en metros y altura), caminos, perímetro y puntos de entrega."""
        return self._geometria

    # --- Comandos del operador --------------------------------------------
    def crear_solicitud(self, origen: str, destino: str, tipo_carga: str, peso_kg: float) -> int:
        """La deja en la bandeja como baliza; todavía no la asigna. ValueError si los datos no sirven."""
        if tipo_carga not in TIPOS_CARGA:
            raise ValueError(f"Tipo de carga desconocido: {tipo_carga}")
        if origen not in self._ubicaciones or destino not in self._ubicaciones:
            raise ValueError("Origen o destino desconocido")
        carga = TIPOS_CARGA[tipo_carga][1](float(peso_kg))
        solicitud = SolicitudEntrega(self._ubicaciones[origen], self._ubicaciones[destino], carga)
        self._bandeja.append(solicitud)
        self._creada_en[solicitud.id] = self._reloj()
        return solicitud.id

    def despachar(self, id_solicitud: int, id_robot: str) -> tuple[bool, str]:
        """Despacho manual: el operador elige el robot."""
        solicitud = self._buscar_solicitud(id_solicitud)
        robot = self._flota.buscar(id_robot)
        if robot is None:
            raise ValueError(f"No existe el robot {id_robot}")
        ok, motivo = self._asignador.despachar(solicitud, robot)
        if ok and solicitud in self._bandeja:
            self._bandeja.remove(solicitud)
        return ok, motivo

    def despachar_auto(self, id_solicitud: int) -> tuple[bool, str]:
        """El asignador elige el robot más barato; si no puede, la solicitud se reintenta sola."""
        solicitud = self._buscar_solicitud(id_solicitud)
        if solicitud in self._bandeja:
            self._bandeja.remove(solicitud)
        ok = self._asignador.asignar(solicitud)
        return ok, "" if ok else solicitud.motivo

    def usar_clima(self, real: bool) -> None:
        """La prueba en vivo del PRD: cambia el proveedor sin tocar la asignación."""
        self._asignador.cambiar_proveedor_clima(self._clima_real if real else self._clima_simulado)
        self._leer_clima()
        self._asignador.reintentar_pendientes()  # un clima mejor puede liberar solicitudes

    def configurar_clima(self, viento: float, lluvia: float, dia: bool,
                         visibilidad: float = 10_000, tormenta: bool = False) -> None:
        self._clima_simulado.configurar(viento, viento * 1.3, lluvia, dia, visibilidad, tormenta)
        if self._asignador.proveedor_clima is self._clima_simulado:
            self._leer_clima()
            self._asignador.reintentar_pendientes()

    def usar_calendario(self, real: bool) -> None:
        self._asignador.cambiar_calendario(self._calendario_real if real else self._calendario_simulado)
        self._leer_festivo()
        self._asignador.reintentar_pendientes()

    def configurar_festivo(self, nombre) -> None:
        """Nombre del festivo simulado, o None para un día hábil."""
        self._calendario_simulado.configurar(nombre or None)
        if self._asignador.calendario is self._calendario_simulado:
            self._leer_festivo()
            self._asignador.reintentar_pendientes()

    def exportar_bitacora(self) -> str:
        return self._bitacora.generar_reporte()

    def _buscar_solicitud(self, id_solicitud: int) -> SolicitudEntrega:
        for s in (*self._bandeja, *self._asignador.pendientes):
            if s.id == id_solicitud:
                return s
        raise ValueError(f"No hay una solicitud {id_solicitud} esperando robot")

    # --- Lecturas de la red en segundo plano --------------------------------
    def _leer_clima(self) -> None:
        self._clima_leido = self._reloj()
        proveedor = self._asignador.proveedor_clima
        if proveedor is self._clima_simulado:
            self._reporte = proveedor.obtener_reporte(self._punto_clima())
            return
        self._reporte = None  # la red puede tardar hasta el timeout: no congelar la ventana

        def leer():
            reporte = proveedor.obtener_reporte(self._punto_clima())
            if proveedor is self._asignador.proveedor_clima:  # ignora un proveedor ya cambiado
                self._reporte = reporte
        threading.Thread(target=leer, daemon=True).start()

    def _leer_festivo(self) -> None:
        calendario = self._asignador.calendario
        if calendario is self._calendario_simulado:
            self._festivo = calendario.festivo(date.today())
            return

        def leer():
            festivo = calendario.festivo(date.today())
            if calendario is self._asignador.calendario:
                self._festivo = festivo
        threading.Thread(target=leer, daemon=True).start()

    def _punto_clima(self):
        return next(iter(self._ubicaciones.values()))  # el campus mide unos 450 m: un punto basta

    # --- Reloj de la simulación --------------------------------------------
    def tick(self) -> bool:
        """Avanza los viajes y el mantenimiento. True si algo terminó (para refrescar la vista)."""
        ahora = self._reloj()
        ocupados = {s.robot.id for s in self._asignador.en_curso}
        for robot in self._flota.robots:
            if robot.id not in ocupados:
                self._de_donde[robot.id] = robot.ubicacion
        for solicitud in self._asignador.en_curso:
            if solicitud.id not in self._viajes:
                self._iniciar_viaje(solicitud, ahora)
        llegadas = [s for s in self._asignador.en_curso if self._progreso(s.id, ahora) >= 1]
        for solicitud in llegadas:
            del self._viajes[solicitud.id]
            self._de_donde[solicitud.robot.id] = solicitud.destino  # por si se reasigna en este mismo tick
            self._asignador.completar_entrega(solicitud)  # el robot queda en el destino
        if self._asignador.proveedor_clima is self._clima_real and ahora - self._clima_leido >= REFRESCO_CLIMA_S:
            self._leer_clima()
        listos = self._asignador.liberar_mantenimientos()  # la recarga la cronometra el dominio
        if listos:
            self._asignador.reintentar_pendientes()
        return bool(llegadas or listos)

    def _iniciar_viaje(self, solicitud, ahora: float) -> None:
        """El viaje va de donde estaba el robot al origen, y del origen al destino.

        El recorrido sale del propio robot (el dron vuela recto) y la duración es el mismo tiempo
        estimado que muestra la ficha."""
        o, d, robot = solicitud.origen, solicitud.destino, solicitud.robot
        antes = self._de_donde.get(robot.id, o)
        tramos = ([] if antes is o else list(robot.trazar_ruta(antes, o).puntos)) + list(robot.trazar_ruta(o, d).puntos)
        duracion = max(MIN_VIAJE_S, solicitud.tiempo_min * SEGUNDOS_POR_MINUTO)
        self._viajes[solicitud.id] = (ahora, duracion, [a_metros(*p) for p in tramos])

    def _progreso(self, id_solicitud: int, ahora: float) -> float:
        inicio, duracion, _ = self._viajes[id_solicitud]
        return (ahora - inicio) / duracion

    # --- Lo que se dibuja ----------------------------------------------------
    def estado(self) -> dict:
        ahora = self._reloj()
        clima = self._clima()
        return {"robots": self._robots(ahora), "balizas": self._balizas(ahora),
                "clima": clima, "ambiente": ambiente(clima), "calendario": self._calendario(),
                "bitacora": self._eventos(), "resumen": self._resumen()}

    def _robots(self, ahora: float) -> list[dict]:
        en_curso = {s.robot.id: s for s in self._asignador.en_curso}
        radar = self._radar()
        quietos: dict[int, list[str]] = {}  # ubicación -> ids de los robots quietos ahí
        for robot in self._flota.robots:
            if robot.id not in en_curso:
                quietos.setdefault(id(robot.ubicacion), []).append(robot.id)
        robots = []
        for robot in self._flota.robots:
            solicitud = en_curso.get(robot.id)
            viaje = self._viajes.get(solicitud.id) if solicitud else None
            if viaje is None:  # quieto, o asignado pero el viaje empieza en el próximo tick
                lugar = self._de_donde.get(robot.id, robot.ubicacion) if solicitud else robot.ubicacion
                x, y = a_metros(lugar.latitud, lugar.longitud)
                vecinos = quietos.get(id(robot.ubicacion), [robot.id])
                if len(vecinos) > 1:
                    angulo = 2 * math.pi * vecinos.index(robot.id) / len(vecinos)
                    x, y = x + SEPARACION_M * math.cos(angulo), y + SEPARACION_M * math.sin(angulo)
                z, recorrido, t = 0, [], 0.0
            else:
                t = min(1.0, self._progreso(solicitud.id, ahora))
                recorrido = viaje[2]
                x, y = punto_en_recorrido(recorrido, t)
                z = ALTURA_VUELO_M * math.sin(math.pi * t) if robot.es_aereo() else 0  # despega y aterriza
            mision = None if solicitud is None else {
                "solicitud": solicitud.id, "destino": solicitud.destino.nombre,
                "carga": solicitud.carga.descripcion, "progreso": t,
                "costo": solicitud.costo, "tiempo_min": solicitud.tiempo_min}
            robots.append({"id": robot.id, "tipo": type(robot).__name__.removeprefix("Robot"),
                           "estado": robot.estado.value, "franja": FRANJA_ESTADO[robot.estado],
                           "bateria": robot.nivel_bateria, "es_aereo": robot.es_aereo(),
                           "x": x, "y": y, "z": z,
                           "recorrido": [list(p) for p in recorrido], "mision": mision,
                           "radar": radar[robot.id]})
        return robots

    def _radar(self) -> dict[str, dict]:
        """Cinco ejes del pentágono, cada uno salido de un método que el subtipo redefine."""
        crudo = {r.id: {"velocidad": r.velocidad_kmh, "carga": r.carga_maxima_kg,
                        "autonomia": 1 / r.consumo_por_km(), "economia": 1 / r.costo_por_km(),
                        "alcance": len(r.zonas_accesibles())} for r in self._flota.robots}
        maximos = {eje: max(v[eje] for v in crudo.values()) for eje in next(iter(crudo.values()), {})}
        return {rid: {eje: v / maximos[eje] for eje, v in ejes.items()} for rid, ejes in crudo.items()}

    def _balizas(self, ahora: float) -> list[dict]:
        balizas = []
        for solicitud, automatica in [*((s, False) for s in self._bandeja),
                                      *((s, True) for s in self._asignador.pendientes)]:
            o = solicitud.origen
            x, y = a_metros(o.latitud, o.longitud)
            balizas.append({"id": solicitud.id, "origen": o.nombre, "destino": solicitud.destino.nombre,
                            "carga": solicitud.carga.descripcion, "peso": solicitud.carga.peso_kg,
                            "x": x, "y": y, "edificio": self._edificio_de.get(o.nombre),
                            "motivo": solicitud.motivo, "automatica": automatica,
                            "espera_s": ahora - self._creada_en.get(solicitud.id, ahora)})
        return balizas

    def _clima(self) -> dict:
        r = self._reporte
        real = self._asignador.proveedor_clima is self._clima_real
        datos = {"proveedor": "Open-Meteo" if real else "simulado", "consultando": r is None}
        if r is None:
            return datos
        favorable, motivo = r.es_favorable(self._asignador.proveedor_clima.umbrales)
        return {**datos, "disponible": r.disponible, "temperatura": r.temperatura_c,
                "humedad": r.humedad_pct, "viento": r.viento_kmh, "rafagas": r.rafagas_kmh,
                "direccion": r.direccion_viento_grados, "lluvia": r.prob_lluvia_pct,
                "visibilidad": r.visibilidad_m, "tormenta": r.tormenta, "es_de_dia": r.es_de_dia,
                "drones_autorizados": favorable, "motivo": motivo}

    def _calendario(self) -> dict:
        real = self._asignador.calendario is self._calendario_real
        return {"proveedor": "Nager.Date" if real else "simulado", "festivo": self._festivo}

    def _eventos(self) -> dict:
        eventos = self._bitacora.eventos()
        return {"total": len(eventos), "ultimos": [
            {"hora": e.fecha.strftime("%H:%M:%S"), "tipo": e.tipo.name, "nombre": e.tipo.value,
             "robot": e.robot_id, "mensaje": e.mensaje} for e in eventos[-EVENTOS_VISIBLES:]]}

    def _resumen(self) -> dict:
        robots = self._flota.robots
        cuenta = lambda estado: sum(r.estado is estado for r in robots)
        return {"robots": len(robots), "disponibles": cuenta(EstadoRobot.DISPONIBLE),
                "en_ruta": cuenta(EstadoRobot.EN_RUTA), "mantenimiento": cuenta(EstadoRobot.MANTENIMIENTO),
                "esperando": len(self._bandeja) + len(self._asignador.pendientes)}


def _luces(edificio: dict, azar: random.Random) -> list[list[float]]:
    """Ventanas encendidas de noche: puntos sobre el techo, entre el centro y las esquinas."""
    contorno = edificio["contorno"]
    cx = sum(p[0] for p in contorno) / len(contorno)
    cy = sum(p[1] for p in contorno) / len(contorno)
    luces = [[cx, cy, edificio["altura"]]]
    for x, y in azar.sample(contorno, min(2, len(contorno))):
        f = azar.uniform(0.3, 0.6)
        luces.append([x + (cx - x) * f, y + (cy - y) * f, edificio["altura"]])
    return luces


def ambiente(clima: dict) -> dict:
    """Cuánto se nota cada efecto del clima en el mapa (0 a 1). La web solo lo dibuja."""
    if clima.get("consultando") or not clima.get("disponible"):
        return {"nubes": 0.2, "lluvia": 0.0, "niebla": 0.0, "tormenta": False, "noche": False, "viento": [0.0, 0.0]}
    tormenta, prob = clima["tormenta"], clima["lluvia"] / 100
    lluvia = max(0.0, (prob - 0.4) / 0.6) if prob >= 0.5 else 0.0
    visibilidad = clima["visibilidad"]
    rumbo = math.radians((clima["direccion"] if clima["direccion"] is not None else 270) + 180)  # hacia donde va
    velocidad = clima["viento"] / 3.6  # m/s
    return {"nubes": min(1.0, 0.2 + prob * 0.8 + (0.3 if tormenta else 0)),
            "lluvia": max(lluvia, 0.8) if tormenta else lluvia,
            "niebla": 0.0 if visibilidad is None else max(0.0, min(1.0, (2000 - visibilidad) / 2000)),
            "tormenta": tormenta, "noche": not clima["es_de_dia"],
            "viento": [velocidad * math.sin(rumbo), velocidad * math.cos(rumbo)]}


def crear_centro(real: bool = False) -> CentroControl:
    """Arma el campus, la flota y el asignador que usa la web."""
    ubicaciones, flota = cargar_campus()
    bitacora = Bitacora()
    asignador = AsignadorEntregas(flota, ServicioClimaSimulado(), bitacora)
    centro = CentroControl(ubicaciones, flota, asignador, bitacora, cargar_geometria())
    centro.usar_clima(real)
    centro.usar_calendario(real)
    return centro
