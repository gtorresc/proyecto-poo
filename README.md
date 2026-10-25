# proyecto-poo

Proyecto de aula POO: **sistema de gestión de una flota de robots de reparto universitario**.

La universidad cuenta con robots terrestres de ruedas, de orugas y drones que transportan
documentos, alimentos, objetos frágiles y materiales de laboratorio dentro del campus.
El sistema registra la flota, recibe solicitudes de entrega, las asigna a un robot compatible,
calcula costos y tiempos, consulta el clima (Open-Meteo) antes de autorizar un dron y lleva
una bitácora de eventos.

## Versiones

| Versión | Dónde | Qué tiene |
| --- | --- | --- |
| Entregada (Fase 5) | rama `main`, tag `v1-entrega` | dominio, clima, asignación y la GUI de CustomTkinter con el mapa de OpenStreetMap |
| UdeM·DESPACHO | rama `udem-despacho` | todo lo anterior, más rutas por los senderos reales, clima extendido (niebla y tormenta), festivos de Colombia, despacho manual y dos interfaces nuevas inspiradas en el juego *Dispatch*: CustomTkinter con el campus en 2D/3D y una versión web con three.js |

Para tener las dos versiones lado a lado sin cambiar de rama:

```bash
git worktree add ../proyecto-poo-mejorado udem-despacho
```

## Estructura

```
main.py          demo por consola e interfaces gráficas (ver "Cómo ejecutar")
src/flota/
  dominio/       robots, cargas, batería, ubicaciones, rutas por senderos, solicitudes, bitácora
  servicios/     proveedores de clima y de festivos (API real y simulador)
  asignacion/    reglas de asignación y despacho de entregas
  gui/           CentroControl (modelo de presentación compartido) e interfaz CustomTkinter
  web/           la misma interfaz en HTML/JS (pywebview + three.js), conectada por PuenteWeb
  recursos/      fuentes, retratos de los robots y sus créditos
  campus.json    puntos reales del campus UdeM y flota inicial (datos, no clases)
  campus_osm.json  edificios y caminos del campus tomados de OpenStreetMap (datos de dibujo y rutas)
  campus.py      carga campus.json, arma la flota y la red de senderos
scripts/         descargar_campus_osm.py: regenera campus_osm.json desde Overpass (solo hace falta una vez)
tests/           pruebas con pytest
docs/            entregables por fase (análisis, CRC, UML, justificación, cambios de diseño)
```

## Avance por fases

| Fase | Estado | Entregable |
| --- | --- | --- |
| 1. Análisis del problema | Hecha | [fase1-analisis.md](docs/fase1-analisis/fase1-analisis.md) · [PDF](docs/fase1-analisis/fase1-analisis.pdf) |
| 2. Clases y responsabilidades (CRC) | Hecha | [fase2-crc.md](docs/fase2-crc/fase2-crc.md) · [PDF](docs/fase2-crc/fase2-crc.pdf) |
| 3. Diseño UML | Hecha | [diagrama_clases_v1.png](docs/fase3-uml/diagrama_clases_v1.png) · [fuente draw.io](docs/fase3-uml/diagrama_clases_v1.drawio) · [changelog y trazabilidad](docs/fase3-uml/CHANGELOG_UML.md) |
| 4. Justificación de decisiones | Hecha | [fase4-justificacion.md](docs/fase4-justificacion/fase4-justificacion.md) · [PDF](docs/fase4-justificacion/fase4-justificacion.pdf) |
| 5. Implementación | Hecha | [src/flota](src/flota) · [tests](tests) · [cambios de diseño](docs/CAMBIOS_DISENO.md) · [UML v2](docs/fase3-uml/diagrama_clases_v2.png) · [fuente draw.io](docs/fase3-uml/diagrama_clases_v2.drawio) |
| Mejoras UdeM·DESPACHO | Hechas | [cambios de diseño, sección 7](docs/CAMBIOS_DISENO.md) · [UML v3](docs/fase3-uml/diagrama_clases_v3.png) · [fuente draw.io](docs/fase3-uml/diagrama_clases_v3.drawio) |
| 6. Reflexión crítica | Pendiente | — |

Presentación de la primera entrega (Fases 1 a 3):
[PDF](<docs/entrega1/Primera entrega — Flota de robots UdeM.pdf>)

La trazabilidad entre fases (requisito → tarjeta CRC → clase del UML) está en
[CHANGELOG_UML.md](docs/fase3-uml/CHANGELOG_UML.md).

## Requisitos

- Python 3.10 o superior
- Para `--web`: Windows 10/11 con WebView2 (viene instalado en Windows 11)

```bash
pip install -r requirements.txt
```

## Cómo ejecutar

```bash
python -m pytest          # pruebas del dominio, servicios, asignación, presentación y documentación
python main.py            # demo por consola con el campus UdeM y clima simulado
python main.py --real     # la demo consultando el clima real (Open-Meteo)
python main.py --gui      # UdeM·DESPACHO en CustomTkinter (mapa del campus en 2D/3D)
python main.py --web      # UdeM·DESPACHO en versión web (pywebview + three.js)
```

- `--real` también vale con `--gui` y `--web`: arrancan con Open-Meteo y Nager.Date en vez de los simuladores.
- `python main.py --web --depurar` abre las herramientas de desarrollo del navegador.
- La demo con simuladores y las pruebas funcionan sin internet. Si una API no responde, el sistema sigue:
  sin clima el dron no vuela; sin calendario se asume día hábil (queda en la bitácora).
- El mapa se dibuja con los datos de OpenStreetMap guardados en `campus_osm.json`, así que funciona sin internet.

### Uso de UdeM·DESPACHO

| Acción | Cómo |
| --- | --- |
| Crear una llamada | formulario "NUEVA LLAMADA" → aparece una baliza naranja sobre el edificio |
| Despachar a mano | clic en la baliza y luego en un robot de la plantilla; si no puede, la ficha dice por qué |
| Despachar en automático | botón AUTO o tecla `A` con la llamada abierta |
| Ver el radar de un robot | clic en su tarjeta (sin llamada abierta) |
| Vista 2D / 3D, girar | `Tab` y `R`, o los botones del mapa; rueda para el zoom y arrastre para moverse |
| Clima y festivos | panel "CLIMA Y CALENDARIO": simulador o APIs reales, en vivo |
| Cerrar fichas | `Esc` |

En la versión web, el botón derecho del mouse rota la vista 3D. Si el equipo no tiene WebGL, se usa el mapa 2D.

## Cambios respecto al diseño

El código se apartó del UML v1 en algunos puntos. Cada diferencia, con su motivo, está en
[CAMBIOS_DISENO.md](docs/CAMBIOS_DISENO.md) y quedó reflejada en el [UML v2](docs/fase3-uml/diagrama_clases_v2.png).
Las mejoras de la rama `udem-despacho` están en la sección 7 del mismo anexo y en el [UML v3](docs/fase3-uml/diagrama_clases_v3.png).

## Créditos

- Datos del mapa: © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright).
- Clima: [Open-Meteo](https://open-meteo.com). Festivos: [Nager.Date](https://date.nager.at).
- Retratos de los robots: [RoboHash](https://robohash.org), set1 de Zikri Kader (CC-BY).
- Fuentes: Oswald y Share Tech Mono (SIL Open Font License). 3D: [three.js](https://threejs.org) (MIT).
- Detalle de licencias en [src/flota/recursos/CREDITOS.md](src/flota/recursos/CREDITOS.md).
- Inspiración visual: el juego *Dispatch* (AdHoc Studio). No se usa ningún recurso del juego.
