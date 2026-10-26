# Graph Report - proyecto-poo

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 690 nodes · 1412 edges · 40 communities (15 shown, 25 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 106 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e2d7ae18`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Módulo web/pagina/mapa2d.js
- Módulo scripts/descargar_campus_osm.py
- Clima: proveedores, reporte y umbrales
- Presentación compartida: CentroControl
- Jerarquía Carga
- Módulo web/pagina/app.js
- Módulo dominio/ruta.py
- Ciclo de vida de SolicitudEntrega
- Módulo gui/app.py
- Web: PuenteWeb y página
- Núcleo del dominio: Robot, Flota y Ubicacion
- GUI: ventana App y paneles
- Enumeraciones de estado
- Asignación: AsignadorEntregas, SolicitudEntrega y cargas
- GUI: PanelMapa y animación
- Módulo dominio/solicitud.py
- GUI: Camara y proyección 2D/3D
- Módulo dominio/bitacora.py
- Subtipos de robot, Zona y carga del campus
- GUI: efectos de clima en el mapa
- GUI: plantilla y fichas de robots
- Ubicacion y Zona
- Módulo servicios/calendario_nager_date.py
- Módulo gui/centro_control.py
- GUI: PanelClima
- Módulo campus.py
- GUI: widget del clima
- Módulo dominio/robot.py
- Módulo servicios/calendario_simulado.py
- Módulo gui/panel_solicitud.py
- Módulo gui/plantilla.py
- Módulo gui/panel_mapa.py

## God Nodes (most connected - your core abstractions)
1. `Ubicacion` - 52 edges
2. `Robot` - 47 edges
3. `CentroControl` - 39 edges
4. `SolicitudEntrega` - 35 edges
5. `PanelMapa` - 30 edges
6. `AsignadorEntregas` - 28 edges
7. `ReporteClima` - 24 edges
8. `App` - 22 edges
9. `Mapa3D` - 21 edges
10. `RedSenderos` - 19 edges

## Surprising Connections (you probably didn't know these)
- `main()` --uses--> `AsignadorEntregas`  [INFERRED]
  main.py → src/flota/asignacion/asignador.py
- `main()` --uses--> `Bitacora`  [INFERRED]
  main.py → src/flota/dominio/bitacora.py
- `main()` --uses--> `EstadoSolicitud`  [INFERRED]
  main.py → src/flota/dominio/solicitud.py
- `main()` --uses--> `ServicioClimaOpenMeteo`  [INFERRED]
  main.py → src/flota/servicios/clima_open_meteo.py
- `main()` --uses--> `ServicioClimaSimulado`  [INFERRED]
  main.py → src/flota/servicios/clima_simulado.py

## Import Cycles
- None detected.

## Communities (40 total, 25 thin omitted)

### Community 0 - "Módulo web/pagina/mapa2d.js"
Cohesion: 0.08
Nodes (19): ALTURA_NUBES_M, azarFijo(), dibujarEncima(), dibujarLuces(), difuminarBordes(), NEBLINA, posicionNube(), puntoEnPoligono() (+11 more)

### Community 1 - "Módulo scripts/descargar_campus_osm.py"
Cohesion: 0.06
Nodes (17): a_texto(), convertir(), main(), _niveles(), _puntos(), ambiente(), punto_en_recorrido(), a_pixel() (+9 more)

### Community 2 - "Clima: proveedores, reporte y umbrales"
Cohesion: 0.07
Nodes (5): ServicioClimaOpenMeteo, ServicioClimaSimulado, ProveedorClima, ReporteClima, UmbralesClima

### Community 3 - "Presentación compartida: CentroControl"
Cohesion: 0.09
Nodes (3): a_metros(), CentroControl, leer()

### Community 4 - "Jerarquía Carga"
Cohesion: 0.08
Nodes (7): main(), pedir(), Alimento, Carga, Documento, Fragil, MaterialPeligroso

### Community 5 - "Módulo web/pagina/app.js"
Cohesion: 0.12
Nodes (32): abrirLlamada(), anunciar(), avisar(), cambiarVista(), cerrarLlamada(), ciclo(), COLOR_EVENTO, conectarControles() (+24 more)

### Community 8 - "Módulo gui/app.py"
Cohesion: 0.14
Nodes (3): main(), aplicar_tema(), fuente()

### Community 11 - "GUI: ventana App y paneles"
Cohesion: 0.17
Nodes (3): App, PanelBitacora, FichaSolicitud

### Community 13 - "Asignación: AsignadorEntregas, SolicitudEntrega y cargas"
Cohesion: 0.17
Nodes (4): AsignadorEntregas, Bitacora, crear_centro(), ProveedorCalendario

### Community 18 - "Subtipos de robot, Zona y carga del campus"
Cohesion: 0.14
Nodes (3): Dron, RobotRuedas, Zona

### Community 19 - "GUI: efectos de clima en el mapa"
Cohesion: 0.17
Nodes (4): CapaClima, gotas(), posicion_nube(), sprite_nube()

### Community 20 - "GUI: plantilla y fichas de robots"
Cohesion: 0.15
Nodes (4): Plantilla, TarjetaRobot, icono(), retrato()

### Community 24 - "Módulo gui/centro_control.py"
Cohesion: 0.20
Nodes (4): dentro(), caras_visibles(), edificio_bajo(), oscurecer()

### Community 26 - "Módulo campus.py"
Cohesion: 0.43
Nodes (3): cargar_campus(), cargar_geometria(), crear_red_senderos()

### Community 28 - "GUI: widget del clima"
Cohesion: 0.29
Nodes (3): rumbo(), texto_clima(), WidgetClima

## Knowledge Gaps
- **9 isolated node(s):** `sprites`, `COLOR_EVENTO`, `EJES`, `ETIQUETA`, `mosaicos` (+4 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 255 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CentroControl` connect `Presentación compartida: CentroControl` to `Clima: proveedores, reporte y umbrales`, `Ciclo de vida de SolicitudEntrega`, `Módulo gui/app.py`, `GUI: ventana App y paneles`, `Enumeraciones de estado`, `Asignación: AsignadorEntregas, SolicitudEntrega y cargas`, `Módulo servicios/calendario_nager_date.py`, `Módulo servicios/calendario_simulado.py`?**
  _High betweenness centrality (0.130) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `Ubicacion` (e.g. with `Dron` and `Robot`) actually correct?**
  _`Ubicacion` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `sprites`, `COLOR_EVENTO`, `EJES` to the rest of the system?**
  _9 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Módulo web/pagina/mapa2d.js` be split into smaller, more focused modules?**
  _Cohesion score 0.08045977011494253 - nodes in this community are weakly interconnected._
- **Why does `Ubicacion` connect `Ubicacion y Zona` to `Clima: proveedores, reporte y umbrales`, `Jerarquía Carga`, `Módulo dominio/ruta.py`, `Ciclo de vida de SolicitudEntrega`, `Núcleo del dominio: Robot, Flota y Ubicacion`, `Enumeraciones de estado`, `Módulo dominio/solicitud.py`, `Subtipos de robot, Zona y carga del campus`, `Módulo dominio/bateria.py`, `Módulo campus.py`, `Módulo dominio/robot.py`?**
  _High betweenness centrality (0.112) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `Robot` (e.g. with `Flota` and `Bateria`) actually correct?**
  _`Robot` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Should `Módulo scripts/descargar_campus_osm.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06205673758865248 - nodes in this community are weakly interconnected._