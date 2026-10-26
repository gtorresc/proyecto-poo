# PROJECT_INDEX — mapa comprimido de `proyecto-poo`

> Léelo **antes** que los fuentes. Resume las ~1 400 líneas de `src/` + `main.py` en un solo esquema.
> Grafo completo (306 nodos, 610 aristas): [`.context/architecture_graph.json`](.context/architecture_graph.json) ·
> informe de comunidades: [`.context/GRAPH_REPORT.md`](.context/GRAPH_REPORT.md) · vista interactiva: `.context/graph.html`.
> Hallazgos de calidad: [`AUDIT_REPORT.md`](AUDIT_REPORT.md). Líneas actualizadas tras aplicar P1, P2 y P6 de la auditoría.

## 1. Qué es

Flota de robots de reparto del campus UdeM (proyecto de aula de POO). Registra robots (ruedas, orugas, dron),
recibe solicitudes de entrega, elige el robot compatible **más barato**, consulta el clima (Open-Meteo o
simulado) **solo si el elegido es un dron** y deja todo en una bitácora. Python ≥ 3.10, sin base de datos.

```bash
python -m pytest        # 114 pruebas, sin red (pytest.ini: pythonpath=src)
python main.py [--real] # demo por consola (clima simulado | Open-Meteo)
python main.py --gui    # CustomTkinter + tkintermapview (necesita internet para los tiles)
```

## 2. Capas y dirección de dependencias (sin ciclos, verificado por graphify)

```
main.py ─┬─> campus ─> dominio
         └─> gui ─────> asignacion ─> dominio, servicios
                  └───> servicios ──> dominio.ubicacion
dominio: no importa nada de fuera (puro). gui: sin reglas de negocio.
```

## 3. Clases (archivo · `Clase(Base) Llínea` → métodos clave)

**dominio/** — entidades; todo el estado es privado (`_x`) y se expone con `@property` de solo lectura.
- `ubicacion.py` · `Zona(Enum)` EDIFICIO/ZONA_VERDE/AZOTEA · `Ubicacion` L15 → `distancia_km()` (Haversine) L48
- `bateria.py` · `Bateria` L6 → `consumir()` L25, `recargar()` L35, `alcanza_para(pct)` L38 (respeta reserva 15 %)
- `estado_robot.py` · `EstadoRobot(Enum)` DISPONIBLE / EN_RUTA / MANTENIMIENTO
- `robot.py` · `Robot(ABC)` L13 — abstractos: `zonas_accesibles`, `costo_por_km`, `consumo_por_km`;
  ganchos con valor por defecto: `factor_ruta`=1.3, `requiere_clima`, `es_aereo`, `terreno_irregular`=False;
  `calcular_tiempo_min` L66, `calcular_costo` L69, `puede_atender(solicitud)` L75, `cargar` L89, `entregar` L103,
  `enviar_a_mantenimiento` L111, `necesita_mantenimiento` L118, `terminar_mantenimiento` L122.
  Subtipos: `RobotRuedas` L164 · `RobotOrugas` L183 · `Dron` L205
- `carga.py` · `Carga(ABC)` L5 → `recargo()` abstracto, `es_compatible_con(robot)` L27 (pregunta capacidades, nunca el tipo).
  Subtipos: `Documento` L35 · `Alimento` L40 · `Fragil` L57 · `MaterialPeligroso` L65
- `solicitud.py` · `EstadoSolicitud(Enum)` · `SolicitudEntrega` L19 — máquina de estados vía `_exigir()` L75:
  `asignar` L79, `marcar_pendiente` L89, `marcar_entregada` L93, `marcar_fallida` L97 (sin uso en la app). Id global `_ids` L9.
- `flota.py` · `Flota` L8 (agregación, lista) → `agregar` L17, `quitar` L24, `buscar` L32, `disponibles` L35
- `bitacora.py` · `TipoEvento(Enum)` · `EventoBitacora` L15 (inmutable) · `Bitacora` L49 → `registrar`, `eventos`, `filtrar`, `generar_reporte`

**servicios/** — clima detrás de una interfaz (Strategy / DIP).
- `proveedor_clima.py` · `UmbralesClima` L8 · `ReporteClima` L32 → `no_disponible()` L46, `es_favorable(umbrales)` L73 ·
  `ProveedorClima(ABC)` L88 → `obtener_reporte(ubicacion)` abstracto L98
- `clima_open_meteo.py` · `ServicioClimaOpenMeteo(ProveedorClima)` L13 — HTTP con timeout 5 s; cualquier fallo → `no_disponible()`
- `clima_simulado.py` · `ServicioClimaSimulado(ProveedorClima)` L8 → `configurar(viento, rafagas, lluvia, dia)` L15

**asignacion/** — `asignador.py` · `DURACION_MANTENIMIENTO_S` L10 · `AsignadorEntregas` L13 (reloj inyectable;
`_pendientes`/`_en_curso` son `dict` por id) → `asignar` L42 (exige `PENDIENTE`), `completar_entrega` L56,
`reintentar_pendientes` L73, `liberar_mantenimientos` L83, `_intentar` L95 (núcleo, CC=9), `cambiar_proveedor_clima` L29.

**campus** — `campus.py` · `cargar_campus()` L13 lee `campus.json` (12 ubicaciones, robots R-01, R-02 [frío], O-01, D-01).

**gui/** — `app.py` · `App(ctk.CTk)` L15 (bucle `_ciclo` 1 s: libera mantenimientos y refresca) · `main()` L62 ·
`panel_mapa.py` · `PanelMapa` L55 (bucle 50 ms; **es quien llama a `completar_entrega`** al terminar la animación),
parche de `tkintermapview.map_widget.requests` L40 · `panel_clima.py` · `PanelClima` L12 (hilo para Open-Meteo) ·
`panel_solicitud.py` · `PanelSolicitud` L15 · `panel_flota.py` · `PanelFlota` L14 · `panel_bitacora.py` · `PanelBitacora` L13

## 4. Flujos principales

1. **Asignar** `AsignadorEntregas.asignar(s)` → `_intentar`: filtra `flota.disponibles()` con `robot.puede_atender(s)`
   (estado, peso, zonas de origen y destino, `carga.es_compatible_con`, batería para ir al origen + entregar con reserva) →
   ordena por `calcular_costo` (solo tramo origen→destino × costo/km × recargo) → si el más barato `requiere_clima()`,
   pide **un** `ReporteClima` del destino y si no es favorable registra `RECHAZO_CLIMA` y prueba el siguiente →
   `robot.cargar(carga, origen)` + `s.asignar(robot, costo, tiempo)` + `_en_curso`. Si nadie puede: `s.marcar_pendiente`,
   `_pendientes`, evento `SOLICITUD_PENDIENTE`.
2. **Entregar** `completar_entrega(s)` → `robot.entregar(destino)` → `ENTREGA_EXITOSA` → si `necesita_mantenimiento()`
   (batería ≤ 25 %) `enviar_a_mantenimiento()` (recarga y queda en MANTENIMIENTO durante 30 s, hasta que
   `liberar_mantenimientos()` llama a `terminar_mantenimiento()`) → `reintentar_pendientes()`.
3. **Clima en vivo (GUI)** `PanelClima._aplicar` → `asignador.cambiar_proveedor_clima(...)` → `App._clima_cambio` → reintenta pendientes.

## 5. Reglas de negocio (constantes)

| Robot | kg máx | km/h | $/km | %bat/km | Zonas | Factor ruta | Especial |
|---|---|---|---|---|---|---|---|
| Ruedas | 20 | 12 | 1500 | 4 | EDIFICIO | 1.3 | — |
| Orugas | 40 | 6 | 2500 | 6 | EDIFICIO, ZONA_VERDE | 1.3 | terreno irregular |
| Dron | 3 | 30 | 4000 | 10 | las tres | 1.0 | aéreo, requiere clima |

Recargos/compatibilidad: Documento ×1.0 · Alimento ×1.2 (exige control de temperatura) · Frágil ×1.3 (no terreno irregular) ·
Peligroso ×1.5 (nunca aéreo). Batería: reserva 15 %, mantenimiento si ≤ reserva + 10, y dura 30 s. Clima favorable: de día, viento ≤ 30 km/h,
ráfagas ≤ 40 km/h, lluvia ≤ 50 %; sin datos → no vuela.

## 6. Pruebas (`tests/`, pytest, 114 casos)

Un archivo por clase de dominio (`test_robot`, `test_bateria`, `test_carga`, `test_solicitud`, `test_flota`, `test_bitacora`,
`test_ubicacion`), `test_asignador` (fixture `entorno` con R-01/O-01/D-01), `test_clima` y `test_clima_open_meteo`
(monkeypatch de `requests.get`), `test_campus`, `test_docs` (enlaces de README/CAMBIOS_DISENO/CHANGELOG_UML).
Cobertura: dominio/servicios/asignación 92-100 %; **gui 0 %**.

## 7. Cómo consultar el grafo en vez de leer archivos

```bash
pip install "graphifyy==0.9.80"
G=.context/architecture_graph.json
graphify explain "AsignadorEntregas" --graph $G          # vecinos de un símbolo con archivo:línea
graphify affected "Bateria" --graph $G --depth 2         # qué se rompe si cambio X
graphify query "puede_atender cargar Dron" --graph $G --budget 1500   # usa identificadores, no prosa
graphify path "PanelSolicitud" "Bateria" --graph $G --undirected
./.context/actualizar_grafo.sh                           # regenerar tras cambiar el código
```
