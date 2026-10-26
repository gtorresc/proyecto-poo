# Informe de auditoría técnica — `proyecto-poo`

Fecha: 2026-10-26 · Commit auditado: `162c232` (rama `claude/loving-wright-yvy3zr`) · Alcance: `main.py`, `src/flota/**`, `tests/**`.
Mapa del proyecto para futuras sesiones: [PROJECT_INDEX.md](PROJECT_INDEX.md). Grafo: [.context/architecture_graph.json](.context/architecture_graph.json).

## 1. Resumen ejecutivo

**Estado general: bueno (7,5/10).** El dominio está bien encapsulado: estado privado expuesto con `@property`,
validación en los constructores, ABC para `Robot`, `Carga` y `ProveedorClima`, polimorfismo por capacidades en lugar
de `isinstance`, inyección del proveedor de clima y ningún ciclo de imports. **No hay** `except: pass`, argumentos
mutables por defecto, archivos sin cerrar ni llamadas HTTP sin timeout.

Los defectos están en **la coordinación entre objetos** (`AsignadorEntregas` y la GUI), no en las entidades:

1. Un robot que entra a mantenimiento **no vuelve nunca**: nadie llama a `terminar_mantenimiento()` (H2).
2. `asignar()` sobre una solicitud que no está pendiente **modifica un robot antes de fallar** y lo deja `EN_RUTA` sin entrega (H1).
3. Con Open-Meteo, la GUI hace **peticiones HTTP bloqueantes en el hilo de Tkinter** desde tres sitios distintos (H3).
4. Mover el deslizador de viento llena la bitácora: **40 eventos `RECHAZO_CLIMA` por un solo arrastre** (H4).

Los tres primeros se reprodujeron con scripts y las correcciones propuestas en la §3 se probaron en una copia
aparte: las 110 pruebas siguen pasando y los cuatro escenarios quedan corregidos.

> **Estado (2026-10-26):** P1, P2 y P6 ya están aplicadas, con 4 pruebas de regresión nuevas en
> `tests/test_asignador.py` (114 pruebas en total). **H1, H2 y H5 están corregidos.** Los demás hallazgos siguen abiertos.
> Las líneas citadas abajo corresponden al commit auditado (`162c232`).

### Métricas

| Métrica | Valor | Herramienta |
|---|---|---|
| Líneas (`src/` + `main.py` / `tests/`) | 1 394 / 828 | `wc -l` |
| Módulos / clases (enums incluidos) | 25 / 32 | graphify |
| Nodos / aristas / comunidades del grafo | 304 / 605 / 13 (8 relevantes) en `162c232`; 306 / 610 / 14 tras las correcciones | graphify 0.9.80 |
| Ciclos de imports | 0 | graphify |
| Pruebas | **110 pasan** (0,5 s, sin red) | pytest |
| Cobertura de líneas | 65 % total · dominio/servicios/asignación 92-100 % · **gui 0 %** | pytest-cov |
| Complejidad ciclomática media / máxima | A (1,82) / B (9) en `AsignadorEntregas._intentar` | radon cc |
| Índice de mantenibilidad | A en los 25 módulos (mínimo 38,4: `robot.py`) | radon mi |
| Errores de tipos | 13 (7 por `Optional[object]`) | mypy `--check-untyped-defs` |
| Avisos de lint relevantes | 4 (DTZ005, PTH123, PLR0913 ×6 por los `__init__` de robot; S104 es falso positivo) | ruff `ALL` |
| Código muerto | 6 símbolos de la API pública que solo usan las pruebas | vulture + grep |
| Reducción de tokens con el grafo | 4,4× por consulta (20 266 → ~4 600 tokens) | `graphify benchmark` |

> **Herramientas.** `graphify` se instaló desde PyPI como `graphifyy==0.9.80` (proyecto Graphify-Labs; el paquete npm
> `graphify` es otro, un generador de grafos aleatorios). **No existe ningún paquete "ponytail" de revisión de código**:
> en PyPI es un `tail -F` para logs y en npm un gestor de sitios, y ninguno sirve aquí. La revisión "Ponytail" se hizo
> a mano siguiendo los cuatro ejes pedidos, con apoyo de ruff, vulture, radon, mypy y pytest-cov, y con scripts que
> reproducen cada hallazgo.

## 2. Hallazgos

Severidad: **Alta** = corrompe estado o rompe una función visible · **Media** = degrada la experiencia, el diagnóstico
o la mantenibilidad de forma medible · **Baja** = higiene, rendimiento a escala futura o decisión que conviene documentar.
"Reproducido" = confirmado ejecutando código.

### 2.1 Críticos y medios

| # | Sev. | Archivo:línea | Categoría | Descripción | Evidencia |
|---|---|---|---|---|---|
| H1 | **Alta** ✅ corregido (P1) | `src/flota/asignacion/asignador.py:34-42`, `:92-93` | Bug lógico / estado | `asignar()` no exige que la solicitud esté `PENDIENTE` y, si una pendiente se asigna llamándola otra vez, **sigue en `_pendientes`**. En el siguiente `reintentar_pendientes()`, `_intentar` ejecuta `robot.cargar()` (robot `EN_RUTA`, batería descontada) y *después* `solicitud.asignar()` lanza `ValueError` → queda un robot ocupado sin entrega y una excepción dentro de `completar_entrega`. Lo mismo pasa al llamar `asignar()` sobre una solicitud ya asignada. Hoy la GUI y `main.py` solo llaman una vez por solicitud, así que es latente, pero está expuesto en la API pública. | Reproducido: `ValueError: Solicitud 41: no se puede pasar de entregada` |
| H2 | **Alta** ✅ corregido (P2) | `src/flota/dominio/robot.py:122`, `asignador.py:54-57` | Bug funcional | `terminar_mantenimiento()` **no se llama en ningún sitio** de la app (solo en una prueba). Cada robot que llega al 25 % de batería pasa a `MANTENIMIENTO` y se queda ahí: en una sesión larga de la GUI la flota se va quedando sin robots. `docs/CAMBIOS_DISENO.md:20` dice que el método se añadió justamente para evitarlo. | Reproducido: tras 40 entregas, R-01 sigue en `mantenimiento` |
| H3 | Media | `asignador.py:76-77`, llamado desde `gui/panel_solicitud.py:51`, `gui/panel_mapa.py:85` y `gui/app.py:54` | Concurrencia / UX | `PanelClima` usa un hilo para no congelar la ventana, pero el asignador vuelve a pedir el clima **de forma síncrona en el hilo de Tkinter** al asignar, al completar una entrega (cada 50 ms en `PanelMapa.refrescar`) y al cambiar el clima. Cada reintento hace una petición por cada pendiente que dependa del dron: con la API caída son hasta 5 s × N pendientes con la ventana congelada. No hay caché entre llamadas. | Reproducido con un proveedor que tarda 0,2 s: 5 pendientes → 1,0 s bloqueado por reintento |
| H4 | Media | `gui/panel_clima.py:43`, `asignador.py:79-81` | Bug lógico / ruido | El deslizador llama a `_configurar_simulado` → `reintentar_pendientes()` en **cada** paso del arrastre, y cada reintento vuelve a registrar `RECHAZO_CLIMA`. La bitácora (y el reporte exportado) se llena de eventos repetidos. | Reproducido: 40 eventos por arrastrar de 40 a 80 km/h con una sola pendiente |
| H5 | Media ✅ corregido (P6) | `gui/panel_mapa.py:73-75`, `gui/app.py:57-59` | Robustez | Los bucles `_ciclo` se reprograman con `after` **después** de `refrescar()`. Si `refrescar()` lanza una excepción (p. ej. H1 dentro de `completar_entrega`), Tkinter la imprime y el bucle **se detiene para siempre**: se congelan la animación y la finalización de entregas, que solo hace `PanelMapa`. | Revisión de código |
| H6 | Media | `dominio/solicitud.py:59`, `dominio/robot.py:157`, `dominio/carga.py:27` | Tipado | `SolicitudEntrega.robot -> Optional[object]`, `Robot.carga_actual -> Optional[object]` y `es_compatible_con(self, robot)` sin tipo (para no importar en círculo). mypy marca 7 errores en `asignador.py`, `main.py` y `panel_solicitud.py`, y el IDE no autocompleta `solicitud.robot.`. Se arregla con `TYPE_CHECKING` sin crear el ciclo. | mypy: 13 errores, 7 por esta causa |
| H7 | Media | `gui/panel_mapa.py:40`, `requirements.txt` | Acoplamiento a terceros | Al importar `panel_mapa` se sustituye `tkintermapview.map_widget.requests` (detalle interno de la librería). Como `requirements.txt` solo fija mínimos (`>=`), una versión nueva de tkintermapview que deje de usar ese atributo rompe la descarga de tiles **sin dar ningún error**. | Revisión de código |
| H8 | Media | `asignador.py:69-95` | SRP / complejidad | `_intentar` (CC 9, la más alta del proyecto) mezcla cinco responsabilidades: filtrar candidatos, ordenar por costo, decidir el clima, registrar en la bitácora y mutar robot y solicitud. Por eso H1 y H4 viven en el mismo método. | radon: B (9) |

### 2.2 Bajos

| # | Archivo:línea | Categoría | Descripción |
|---|---|---|---|
| H9 | `asignador.py:63-66` | Lógica | `reintentar_pendientes` no actualiza `solicitud.motivo`: una pendiente por "ningún robot disponible" sigue mostrando ese motivo aunque ahora la bloquee el clima. |
| H10 | `asignador.py:71` vs `:90-91`; `robot.py:69-70` | Regla de negocio | El costo solo cuenta el tramo origen→destino, mientras que el tiempo y la batería incluyen la aproximación desde donde está el robot. "El más barato" puede ser un robot lejano. Vale como decisión, pero no está documentada. |
| H11 | `asignador.py:77` | Regla de negocio | El clima se consulta solo en el **destino**; el origen y el trayecto del dron no se evalúan (en un campus de 1 km la diferencia es mínima). |
| H12 | `gui/panel_bitacora.py:45` | Excepciones | `_exportar` no captura `OSError` (sin permisos, disco lleno): el error sale por consola y el usuario no ve nada. |
| H13 | `gui/panel_clima.py:76` | Concurrencia | La comprobación `proveedor is self._asignador.proveedor_clima` no distingue dos consultas del **mismo** proveedor (Real→Simulado→Real rápido): una respuesta vieja puede pisar a la nueva. Asignar `self._reporte` es atómico en CPython, así que no hay corrupción. |
| H14 | `gui/app.py:65`; `gui/panel_clima.py:19-20` | DIP / objeto muerto | `gui.app.main` crea un `ServicioClimaSimulado` que `PanelClima._aplicar` reemplaza enseguida. El panel construye sus propios proveedores concretos en vez de recibirlos. |
| H15 | `gui/panel_mapa.py:49-52`, `gui/panel_flota.py:25` | OCP | `color_robot` usa `isinstance(Dron/RobotOrugas)` y `PanelFlota` usa `type(robot).__name__`: un tipo de robot nuevo obliga a tocar la GUI. Se resuelve con un diccionario `{RobotRuedas: …}` en la capa de presentación. |
| H16 | `dominio/solicitud.py:97`, `dominio/bitacora.py:9`, `servicios/proveedor_clima.py:101`, `dominio/robot.py:157`, `dominio/flota.py:24`, `asignador.py:27` | Código muerto | Solo los usan las pruebas: `marcar_fallida`, `TipoEvento.ENTREGA_FALLIDA` (nunca se emite, así que el reporte siempre dice 0), `condiciones_favorables`, `carga_actual`, `Flota.quitar`, `pendientes`. Son API del UML v2: conviene mantenerlos y conectarlos (p. ej. fallo de batería en `entregar`), o quitarlos del diagrama. |
| H17 | `dominio/robot.py:164-212` | Duplicación | Los tres `__init__` de los subtipos repiten la firma de seis parámetros solo para cambiar dos valores por defecto (6 avisos PLR0913). Se puede reemplazar por atributos de clase (`CARGA_MAXIMA_KG = 20`) leídos en `Robot.__init__`. |
| H18 | `dominio/robot.py:79-80` vs `:72-73` | Duplicación | `puede_atender` reescribe a mano la fórmula de `_consumo_viaje` para el tramo origen→destino. Un helper `_consumo_entre(a, b)` deja la regla en un solo lugar. |
| H19 | `dominio/flota.py:32-33`; `asignador.py:37,50,65`; `dominio/bitacora.py:64`; `gui/panel_bitacora.py:31`; `gui/panel_mapa.py:79,82,103` | Rendimiento | Búsquedas lineales: `Flota.buscar` recorre la lista (cargar la flota es O(n²)), `in`/`remove` sobre listas en el asignador, `generar_reporte` es O(tipos × eventos), `PanelBitacora.refrescar` copia **toda** la bitácora cada segundo y `en_curso` se copia 3 veces cada 50 ms. Con 4 robots no se nota; con cientos de eventos o solicitudes sí. Se arregla con `dict` por id y `Counter`. |
| H20 | `dominio/bitacora.py:23`; `dominio/solicitud.py:9,26` | Higiene | `datetime.now()` sin zona horaria; contador global `_ids` que no se reinicia entre pruebas; `origen is destino` compara identidad (dos `Ubicacion` iguales pasan la validación porque `Ubicacion` no define `__eq__`). |
| H21 | `servicios/clima_open_meteo.py:29-31` | Diagnóstico | El fail-safe es correcto (excepciones concretas, nada de `except:`), pero **descarta el motivo**: el usuario ve "clima no disponible" sin saber si fue timeout, HTTP 500 o JSON inválido. `ReporteClima.no_disponible(motivo)` mejoraría la bitácora. |
| H22 | `main.py:17,47,49,51` | Higiene | `sys.stdout.reconfigure` falla si stdout no es un `TextIOWrapper`; `s.estado.value == "asignada"` compara texto en vez de `EstadoSolicitud.ASIGNADA`; el `reintentar_pendientes()` de la línea 49 sobra porque `completar_entrega` ya reintenta. |
| H23 | `requirements.txt` | Dependencias | `pytest` va mezclado con las dependencias de ejecución y no hay versiones máximas ni lockfile (ver H7). |

**Verificado y sin problemas:** manejo de excepciones (ningún `except` genérico ni silencioso), argumentos por defecto
(ninguno mutable), recursos (`with open`, timeouts en todo HTTP), encapsulamiento (sin atributos públicos mutables en el
dominio), jerarquías (LSP: las subclases solo redefinen ganchos y respetan los contratos), imports (sin ciclos).
Falsos positivos descartados: ruff S104 en `panel_mapa.py:22` (`source_address` es la dirección de **salida**, no un
servidor escuchando); vulture `timeout` en `tests/test_clima_open_meteo.py:34` (imita la firma de `requests.get`).

## 3. Propuestas de refactorización (Antes vs. Después)

P1 a P4 se aplicaron juntas en una copia del repositorio y se validaron: **110/110 pruebas pasan**, R-01 vuelve a
`disponible` tras el mantenimiento, la segunda llamada a `asignar` saca la solicitud de pendientes y la tercera lanza
`ValueError` sin tocar ningún robot, el arrastre del deslizador añade **0** eventos y dos consultas cercanas a
Open-Meteo hacen **1** petición HTTP. Cada propuesta debería llegar con su prueba de regresión.

### P1 — Exigir `PENDIENTE` y no dejar solicitudes asignadas en la cola (H1, H19)

**Antes** (`asignador.py`)
```python
self._pendientes: list[SolicitudEntrega] = []
self._en_curso: list[SolicitudEntrega] = []

def asignar(self, solicitud: SolicitudEntrega) -> bool:
    asignada, motivo = self._intentar(solicitud)
    if not asignada and solicitud not in self._pendientes:
        solicitud.marcar_pendiente(motivo)
        self._pendientes.append(solicitud)
        ...
    return asignada
```
**Después**
```python
self._pendientes: dict[int, SolicitudEntrega] = {}  # id -> solicitud, en orden de llegada
self._en_curso: dict[int, SolicitudEntrega] = {}    # asignadas y aún sin entregar

def asignar(self, solicitud: SolicitudEntrega) -> bool:
    if solicitud.estado is not EstadoSolicitud.PENDIENTE:   # falla ANTES de tocar ningún robot
        raise ValueError(f"Solicitud {solicitud.id} ya está {solicitud.estado.value}")
    asignada, motivo = self._intentar(solicitud)
    if asignada:
        self._pendientes.pop(solicitud.id, None)
    elif solicitud.id not in self._pendientes:
        solicitud.marcar_pendiente(motivo)
        self._pendientes[solicitud.id] = solicitud
        self._bitacora.registrar(TipoEvento.SOLICITUD_PENDIENTE, f"Solicitud {solicitud.id}: {motivo}")
    return asignada
# y en el resto: self._en_curso[solicitud.id] = solicitud / del self._en_curso[solicitud.id]
```
`pendientes` y `en_curso` devuelven `tuple(self._x.values())`, así que la API pública no cambia. `dict` conserva el orden
de inserción y pasa las búsquedas de O(n) a O(1).

### P2 — Salida de mantenimiento con reloj inyectable (H2)

**Antes**
```python
if robot.necesita_mantenimiento():
    robot.enviar_a_mantenimiento()          # ... y nadie llama a terminar_mantenimiento()
```
**Después** (mismo patrón `reloj=time.monotonic` que ya usa `PanelMapa`, así se puede probar sin esperar)
```python
DURACION_MANTENIMIENTO_S = 30.0

def __init__(self, flota, proveedor_clima, bitacora, reloj: Callable[[], float] = time.monotonic):
    ...
    self._reloj = reloj
    self._en_mantenimiento: dict[str, float] = {}       # id del robot -> instante de salida

# en completar_entrega
if robot.necesita_mantenimiento():
    robot.enviar_a_mantenimiento()
    self._en_mantenimiento[robot.id] = self._reloj() + DURACION_MANTENIMIENTO_S

def reintentar_pendientes(self) -> int:
    self._liberar_mantenimientos()
    ...

def _liberar_mantenimientos(self) -> None:
    ahora = self._reloj()
    for id_robot, salida in list(self._en_mantenimiento.items()):
        robot = self._flota.buscar(id_robot)
        if salida <= ahora and robot is not None:
            robot.terminar_mantenimiento()
            del self._en_mantenimiento[id_robot]
            self._bitacora.registrar(TipoEvento.MANTENIMIENTO, "Recargado: vuelve a la flota", id_robot)
```
En la GUI, `App._ciclo` (cada 1 s) puede llamar a `asignador.reintentar_pendientes()` para que la salida ocurra aunque
no haya entregas. La duración es una decisión de diseño: hay que anotarla en `CAMBIOS_DISENO.md` y en el UML.

### P3 — Caché con vigencia en `ServicioClimaOpenMeteo` (H3)

**Antes**
```python
def obtener_reporte(self, ubicacion: Ubicacion) -> ReporteClima:
    params = {...}
    try:
        respuesta = requests.get(URL, params=params, timeout=self._timeout_s)   # en cada intento
        ...
```
**Después**
```python
VIGENCIA_S = 300  # Open-Meteo actualiza "current" cada 15 min: no hace falta pedirlo en cada intento

def __init__(self, umbrales=None, timeout_s=TIMEOUT_S, vigencia_s=VIGENCIA_S,
             reloj: Callable[[], float] = time.monotonic):
    super().__init__(umbrales)
    self._timeout_s, self._vigencia_s, self._reloj = timeout_s, vigencia_s, reloj
    self._cache: dict[tuple[float, float], tuple[float, ReporteClima]] = {}

def obtener_reporte(self, ubicacion: Ubicacion) -> ReporteClima:
    clave = (round(ubicacion.latitud, 2), round(ubicacion.longitud, 2))  # ~1 km: todo el campus
    guardado = self._cache.get(clave)
    if guardado and self._reloj() - guardado[0] < self._vigencia_s:
        return guardado[1]
    reporte = self._consultar(ubicacion)        # el cuerpo anterior de obtener_reporte, sin cambios
    if reporte.disponible:                      # un fallo no se guarda: el siguiente intento vuelve a preguntar
        self._cache[clave] = (self._reloj(), reporte)
    return reporte
```
La primera consulta y las consultas con la API caída siguen bloqueando. La solución completa para la GUI es que
`PanelClima` refresque el reporte en su hilo y que el asignador lea siempre el último valor guardado. También se puede
guardar el fallo durante ~30 s para no esperar 5 s en cada reintento.

### P4 — No volver a registrar rechazos en los reintentos y actualizar el motivo (H4, H9)

**Antes**
```python
for solicitud in list(self._pendientes):
    if self._intentar(solicitud)[0]:        # cada reintento vuelve a escribir RECHAZO_CLIMA
        self._pendientes.remove(solicitud)
        logradas += 1
```
**Después**
```python
for solicitud in list(self._pendientes.values()):
    asignada, motivo = self._intentar(solicitud, registrar_rechazo=False)
    if asignada:
        del self._pendientes[solicitud.id]
        logradas += 1
    elif motivo != solicitud.motivo:
        solicitud.marcar_pendiente(motivo)  # el motivo visible no queda desactualizado

def _intentar(self, solicitud, registrar_rechazo: bool = True) -> tuple[bool, str]:
    ...
    if not favorable:
        if registrar_rechazo:               # en los reintentos ya consta en la bitácora
            self._bitacora.registrar(TipoEvento.RECHAZO_CLIMA, ...)
```
Además conviene agrupar los eventos del deslizador en la GUI: reprogramar con `self.after(300, ...)` y cancelar el
anterior con `after_cancel`, para reintentar una vez al soltar y no en cada píxel.

### P5 — Tipado real sin ciclo de imports (H6)

**Antes** (`solicitud.py`)
```python
@property
def robot(self) -> Optional[object]:
    return self._robot
```
**Después**
```python
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:  # solo para el tipado: en ejecución no se importa nada nuevo
    from flota.dominio.robot import Robot

def asignar(self, robot: "Robot", costo: float, tiempo_min: float) -> None: ...

@property
def robot(self) -> Optional["Robot"]:
    return self._robot
```
Lo mismo vale para `Carga.es_compatible_con(self, robot: "Robot")` y `Robot.carga_actual -> Optional["Carga"]`. mypy
pasa a señalar los sitios donde se usa `solicitud.robot` sin comprobar `None`. En `completar_entrega` basta con
`assert robot is not None` después de verificar `ASIGNADA`.

### P6 — Bucles de la GUI que sobreviven a una excepción (H5)

**Antes** (`panel_mapa.py`)
```python
def _ciclo(self) -> None:
    self.refrescar()
    self.after(INTERVALO_MS, self._ciclo)
```
**Después**
```python
def _ciclo(self) -> None:
    try:
        self.refrescar()
    finally:  # un error en una entrega no debe detener la animación ni las siguientes entregas
        self.after(INTERVALO_MS, self._ciclo)
```
Lo mismo aplica a `App._ciclo`.

### P7 — Separar `_intentar` (H8) · opcional, tras P1-P4

```python
def _intentar(self, solicitud, registrar_rechazo=True) -> tuple[bool, str]:
    candidatos = self._candidatos_por_costo(solicitud)              # filtra + ordena (puro)
    elegido, motivo = self._primero_que_vuela(candidatos, solicitud, registrar_rechazo)  # clima
    if elegido is None:
        return False, motivo
    self._ejecutar_asignacion(solicitud, *elegido)                  # muta robot + solicitud
    return True, ""
```
Cada parte se puede probar por separado y la mutación queda al final, cuando todas las validaciones ya pasaron.

### Orden recomendado

P1 → P2 → P6 (correcciones, con una prueba de regresión cada una) · P4 → P3 (experiencia en la GUI) · P5 → P7 → H17/H18
(mantenibilidad). Después, una prueba de humo de la GUI con `tk` sin ventana (`withdraw()`) para que la cobertura de
`gui/` deje de ser 0 %.

## 4. Guía de uso del grafo (`graphify`)

**Archivos** (en `.context/`, regenerables con `./.context/actualizar_grafo.sh`, que requiere `pip install "graphifyy==0.9.80"`):

| Archivo | Para qué | Tamaño |
|---|---|---|
| [`PROJECT_INDEX.md`](PROJECT_INDEX.md) | **Mapa mental comprimido.** Es lo primero que debe cargar un agente. | ~1,1 k palabras |
| `.context/architecture_graph.json` | Grafo completo (nodos con `source_file` + `source_location`; aristas `calls`, `inherits`, `method`, `imports`, `uses`, …). Se consulta con la CLI, **no se pega en el prompt**. | 340 KB |
| `.context/GRAPH_REPORT.md` | Comunidades con nombre, nodos centrales ("god nodes") y puentes entre módulos. | 5 KB |
| `.context/graph.html` | Vista interactiva para personas (abrir en el navegador). | 300 KB |
| `.context/comunidades.json` | Nombres curados de las comunidades, asignados por una clase representativa ("clase": "nombre") para que sobrevivan a la renumeración al regenerar. | <1 KB |

El grafo indexa solo `src/` y `main.py` (`.graphifyignore` excluye `tests/`, `docs/` y `.context/`) y se genera solo
con el AST: sin LLM, sin API key y sin enviar código fuera.

**Plantilla de prompt para sesiones futuras**

```text
Contexto: lee PROJECT_INDEX.md (no abras los fuentes todavía). Para dudas de dependencias usa
`graphify explain|affected|path ... --graph .context/architecture_graph.json` y abre solo los archivos:línea
que devuelva. Hallazgos abiertos: AUDIT_REPORT.md §2 (IDs H3..H23; H1, H2 y H5 ya están corregidos).
Tarea: <p. ej. "implementa P2 de AUDIT_REPORT.md con su prueba">.
```

**Consultas útiles** (desde la raíz; `G=.context/architecture_graph.json`)

```bash
graphify explain "AsignadorEntregas" --graph $G               # 21 conexiones con archivo:línea
graphify affected "Bateria" --graph $G --depth 2              # impacto de un cambio (robot.py, flota.py, campus.py…)
graphify path "PanelSolicitud" "Bateria" --graph $G --undirected
graphify query "puede_atender cargar Dron" --graph $G --budget 1500
graphify god-nodes --graph $G --top 10
```

Recomendaciones: consultar con **identificadores del código** (en español), no con prosa en inglés, porque la
búsqueda es léxica. Subir `--budget` si la salida dice `TRUNCATED`. Regenerar el grafo después de cada refactor y
revisar `.context/comunidades.json` si aparecen comunidades nuevas. Las aristas `INFERRED` (11 %) son deducciones del
extractor: hay que confirmarlas en el código antes de basarse en ellas.
