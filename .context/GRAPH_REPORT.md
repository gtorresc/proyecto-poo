# Graph Report - proyecto-poo

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 306 nodes · 610 edges · 14 communities (7 shown, 7 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 66 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7af5e808`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Asignación: AsignadorEntregas, SolicitudEntrega y cargas
- Núcleo del dominio: Robot, Flota y Ubicacion
- Clima: proveedores, reporte y umbrales
- Subtipos de robot, Zona y carga del campus
- GUI: ventana App y paneles
- Enumeraciones de estado
- Bitácora y eventos
- Batería
- GUI: PanelMapa y animación

## God Nodes (most connected - your core abstractions)
1. `Robot` - 43 edges
2. `Ubicacion` - 42 edges
3. `SolicitudEntrega` - 31 edges
4. `AsignadorEntregas` - 22 edges
5. `ReporteClima` - 19 edges
6. `Zona` - 17 edges
7. `Carga` - 16 edges
8. `ProveedorClima` - 16 edges
9. `main()` - 16 edges
10. `UmbralesClima` - 15 edges

## Surprising Connections (you probably didn't know these)
- `main()` --uses--> `ServicioClimaOpenMeteo`  [INFERRED]
  main.py → src/flota/servicios/clima_open_meteo.py
- `main()` --uses--> `ServicioClimaSimulado`  [INFERRED]
  main.py → src/flota/servicios/clima_simulado.py
- `main()` --uses--> `Bitacora`  [INFERRED]
  main.py → src/flota/dominio/bitacora.py
- `main()` --uses--> `AsignadorEntregas`  [INFERRED]
  main.py → src/flota/asignacion/asignador.py
- `main()` --uses--> `Alimento`  [INFERRED]
  main.py → src/flota/dominio/carga.py

## Import Cycles
- None detected.

## Communities (14 total, 7 thin omitted)

### Community 0 - "Asignación: AsignadorEntregas, SolicitudEntrega y cargas"
Cohesion: 0.06
Nodes (9): main(), pedir(), AsignadorEntregas, Alimento, Carga, Documento, Fragil, MaterialPeligroso (+1 more)

### Community 1 - "Núcleo del dominio: Robot, Flota y Ubicacion"
Cohesion: 0.07
Nodes (3): Flota, Robot, Ubicacion

### Community 2 - "Clima: proveedores, reporte y umbrales"
Cohesion: 0.07
Nodes (6): main(), ServicioClimaOpenMeteo, ServicioClimaSimulado, ProveedorClima, ReporteClima, UmbralesClima

### Community 3 - "Subtipos de robot, Zona y carga del campus"
Cohesion: 0.06
Nodes (6): cargar_campus(), Dron, RobotOrugas, RobotRuedas, Zona, _AdaptadorIPv4

### Community 4 - "GUI: ventana App y paneles"
Cohesion: 0.12
Nodes (5): App, PanelBitacora, PanelClima, PanelFlota, PanelSolicitud

### Community 5 - "Enumeraciones de estado"
Cohesion: 0.11
Nodes (3): EstadoRobot, EstadoSolicitud, color_bateria()

### Community 6 - "Bitácora y eventos"
Cohesion: 0.14
Nodes (3): Bitacora, EventoBitacora, TipoEvento

## Knowledge Gaps
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Ubicacion` connect `Núcleo del dominio: Robot, Flota y Ubicacion` to `Asignación: AsignadorEntregas, SolicitudEntrega y cargas`, `Clima: proveedores, reporte y umbrales`, `Subtipos de robot, Zona y carga del campus`, `Enumeraciones de estado`?**
  _High betweenness centrality (0.282) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `Robot` (e.g. with `Flota` and `Bateria`) actually correct?**
  _`Robot` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `Asignación: AsignadorEntregas, SolicitudEntrega y cargas` be split into smaller, more focused modules?**
  _Cohesion score 0.05714285714285714 - nodes in this community are weakly interconnected._
- **Why does `Robot` connect `Núcleo del dominio: Robot, Flota y Ubicacion` to `Subtipos de robot, Zona y carga del campus`, `Enumeraciones de estado`, `Batería`?**
  _High betweenness centrality (0.169) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `Ubicacion` (e.g. with `Dron` and `Robot`) actually correct?**
  _`Ubicacion` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Should `Núcleo del dominio: Robot, Flota y Ubicacion` be split into smaller, more focused modules?**
  _Cohesion score 0.0653061224489796 - nodes in this community are weakly interconnected._
- **Why does `SolicitudEntrega` connect `Asignación: AsignadorEntregas, SolicitudEntrega y cargas` to `Núcleo del dominio: Robot, Flota y Ubicacion`, `Clima: proveedores, reporte y umbrales`, `GUI: ventana App y paneles`, `Enumeraciones de estado`?**
  _High betweenness centrality (0.141) - this node is a cross-community bridge._