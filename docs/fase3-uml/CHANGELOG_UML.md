# Changelog del diagrama de clases

Archivos:
- `diagrama_clases_v1.drawio` / `.png`: primera versión, derivada de las tablas CRC (Fase 2)
- `diagrama_clases_v2.drawio` / `.png`: ajustada al código de la Fase 5 (fuente editable en draw.io / diagrams.net)
- `diagrama_clases_v3.drawio` / `.png`: mejoras de la rama `udem-despacho` (rutas por senderos, festivos, despacho manual)

---

## v3 (2026-10-25): mejoras de la rama `udem-despacho`

Entran cinco clases nuevas y dos relaciones nuevas; las de v2 se mantienen. El detalle de cada cambio está
en la sección 7 de [CAMBIOS_DISENO.md](../CAMBIOS_DISENO.md). La interfaz gráfica (`CentroControl`, los
paneles, `PuenteWeb`) es capa de presentación y queda fuera del diagrama, igual que en v1 y v2.

| Clase o relación | Cambio en el diagrama |
|---|---|
| `Ruta` (nueva) | puntos y distancia de un recorrido; `linea_recta()` como constructor alternativo |
| `RedSenderos` (nueva) | grafo de los senderos de OSM; `ruta()` con Dijkstra; `RedSenderos ..> Ruta` «crea» |
| `Robot — RedSenderos` (nueva, 0..* — 0..1) | asociación opcional: toda la flota comparte una red |
| `Robot` | `+ _red`, `+ trazar_ruta()`, `+ motivo_rechazo()` |
| `Dron` | `trazar_ruta()` (vuela recto) reemplaza a `factor_ruta()` |
| `ProveedorCalendario` (nueva, abstracta), `CalendarioNagerDate`, `CalendarioSimulado` (nuevas) | festivos de Colombia, mismo patrón que el clima |
| `AsignadorEntregas — ProveedorCalendario` (nueva, 1 — 0..1, «inyectado») | `+ _calendario`, `+ calendario`, `+ cambiar_calendario()` |
| `AsignadorEntregas` | `+ despachar()` (despacho manual), `- _motivo_festivo()`, `- _asignar_a()` |
| `Carga`, `Alimento` | `+ requiere_cafeteria()` |
| `ReporteClima` | `+ _visibilidad_m`, `+ _tormenta`, `+ _humedad_pct`, `+ _direccion_viento_grados` |
| `UmbralesClima` | `+ _visibilidad_min_m` |
| `ServicioClimaSimulado` | `configurar()` recibe visibilidad, tormenta, humedad y dirección |
| `TipoEvento` | `+ DESPACHO_RECHAZADO` |
| `AsignadorEntregas` (revisión previa a la Fase 6) | `+ _en_mantenimiento`, `+ _reloj`, `+ liberar_mantenimientos()` (ya estaban en el código desde v2 y faltaban en el diagrama); `_pendientes` y `_en_curso` pasan de `list` a `dict` por id; `- _motivo_imposible()` |
| `Robot` (revisión previa a la Fase 6) | `+ motivo_incapaz()`: las reglas que no cambian esperando, separadas de `motivo_rechazo()` |

---

## v2 (2026-10-25): ajustes tras implementar el sistema (Fase 5)

Las clases y las relaciones no cambian. Solo se ajustan miembros, porque al escribir el código aparecieron
cosas que el papel no mostraba. El detalle de cada cambio (qué, por qué y qué se aprendió) está en
[CAMBIOS_DISENO.md](../CAMBIOS_DISENO.md).

| Clase | Cambio en el diagrama |
|---|---|
| `Robot` | `+ necesita_mantenimiento()`, `+ terminar_mantenimiento()`; `cargar()` recibe `origen` opcional |
| `Bateria` | `+ reserva_minima` (propiedad) |
| `Flota` | `+ robots` (propiedad, devuelve una copia) |
| `AsignadorEntregas` | `+ _en_curso`, `+ pendientes`, `+ en_curso`, `+ proveedor_clima`, `- _intentar()` |
| `ProveedorClima` | `+ umbrales` (propiedad) |
| `ReporteClima` | `+ _temperatura_c`, `+ no_disponible()` (constructor alternativo) |
| `ServicioClimaOpenMeteo` | se quita `_url_base` (es una constante del módulo) |

---

## v1 (2026-10-14): primera versión derivada de las tablas CRC (Fase 2)

### Trazabilidad análisis → CRC → UML

| Requisito (Fase 1) | Tarjeta CRC (Fase 2) | Elemento en el UML v1 |
|---|---|---|
| RF1 Registrar robots | Robot, Flota | `Robot` (abstracta), `Flota.agregar()` |
| RF2 Estado del robot | Robot, Bateria, Ubicacion | `Robot._estado: EstadoRobot`, `Robot._bateria`, `Robot._ubicacion` |
| RF3 Recibir solicitudes | SolicitudEntrega | `SolicitudEntrega` con origen, destino y carga |
| RF4 Restricciones de la carga | Carga y subtipos | `Carga.es_compatible_con()` redefinido en `Alimento`, `Fragil`, `MaterialPeligroso` |
| RF5 Asignar robot compatible | Robot, AsignadorEntregas | `Robot.puede_atender()`, `AsignadorEntregas.asignar()` |
| RF6 Consultar clima antes de usar dron | ProveedorClima, ServicioClimaOpenMeteo | `Robot.requiere_clima()` (solo `Dron` → True), `ProveedorClima.condiciones_favorables()` |
| RF7 Reasignar o dejar pendiente | AsignadorEntregas, SolicitudEntrega | `AsignadorEntregas._pendientes`, `SolicitudEntrega.marcar_pendiente()` |
| RF8 Costo y tiempo | Robot (polimórfico), Carga | `Robot.calcular_costo()`, `calcular_tiempo_min()`, `costo_por_km()` en cada subtipo, `Carga.recargo()` |
| RF9 Bitácora de eventos | Bitacora, EventoBitacora | `Bitacora ◆— EventoBitacora`, enum `TipoEvento` |
| RF10 Reporte | Bitacora | `Bitacora.generar_reporte()` |
| RF11 Mantenimiento | Robot, Bateria | `Robot.enviar_a_mantenimiento()`, `Bateria.recargar()` |
| RF12 Reintentar pendientes | AsignadorEntregas | `AsignadorEntregas.reintentar_pendientes()` |
| Supuesto S1 (umbrales de clima) | ReporteClima / UmbralesClima | `UmbralesClima` (30 km/h, 40 km/h, 50 %) |
| Supuesto S3 (reserva de batería 15 %) | Bateria | `Bateria._reserva_minima = 15.0`, `alcanza_para()` |
| Supuesto S4 (API caída = no vuela) | ServicioClimaOpenMeteo | `ReporteClima._disponible`, `_timeout_s = 5.0` |
| Supuesto S6 (peligrosos nunca en dron) | MaterialPeligroso | `MaterialPeligroso.es_compatible_con()` usando `Robot.es_aereo()` |

### Relaciones exigidas por el PRD (Fase 3)

| Exigencia | Dónde está |
|---|---|
| Herencia con polimorfismo real | `Robot` → `RobotRuedas`, `RobotOrugas`, `Dron`; `Carga` → 4 subtipos; `ProveedorClima` → 2 implementaciones |
| Composición genuina (ciclo de vida dependiente) | `Robot ◆— Bateria` (1–1); `Bitacora ◆— EventoBitacora` (1–0..*) |
| Agregación / asociación | `Flota ◇— Robot` (0..1–0..*); asociaciones de `AsignadorEntregas`, `SolicitudEntrega` |
| Clima como dependencia desacoplada | `AsignadorEntregas — ProveedorClima` «inyectado» (asociación, no herencia) |

### Cambios respecto a las tablas CRC

| Cambio | Motivo |
|---|---|
| La tarjeta "ReporteClima / UmbralesClima" se separó en dos clases | Los umbrales son configuración que comparten el proveedor real y el simulado. El reporte es el dato que llega de la API. Tienen ciclos de vida distintos. |
| Se agregó el enum `EstadoSolicitud` | La CRC decía "llevar su estado". Al modelarlo apareció un conjunto cerrado de valores (pendiente, asignada, entregada, fallida). |
| Se agregó `Robot._tiene_control_temperatura` | `Alimento.es_compatible_con()` necesita consultar esa capacidad sin preguntar por la subclase del robot (decisión D4). |
| Se explicitó `AsignadorEntregas._pendientes` | Lo exige RF12: para reintentar hay que guardar las solicitudes pendientes. |
| Se agregó el método privado `ServicioClimaOpenMeteo._parsear_respuesta()` | Deja oculto el formato JSON de Open-Meteo: nadie fuera del servicio lo conoce. |
| Se agregó `EventoBitacora.como_texto()` | El reporte de la bitácora necesita una representación de cada evento. |
| Distancia por rutas reales (OSRM) **no** entra en v1 | Es opcional. Se usa `Ubicacion.distancia_km()` (Haversine) × `Robot.factor_ruta()`. |
