# proyecto-poo

Proyecto de aula POO: **sistema de gestión de una flota de robots de reparto universitario**.

La universidad cuenta con robots terrestres de ruedas, de orugas y drones que transportan
documentos, alimentos, objetos frágiles y materiales de laboratorio dentro del campus.
El sistema registra la flota, recibe solicitudes de entrega, las asigna a un robot compatible,
calcula costos y tiempos, consulta el clima (Open-Meteo) antes de autorizar un dron y lleva
una bitácora de eventos.

## Estructura

```
main.py          demo por consola e interfaz gráfica (ver "Cómo ejecutar")
src/flota/
  dominio/       robots, cargas, batería, ubicaciones, solicitudes, bitácora
  servicios/     proveedores de clima (API real y simulado)
  asignacion/    reglas de asignación de entregas
  gui/           interfaz gráfica (CustomTkinter + mapa OpenStreetMap)
  campus.json    puntos reales del campus UdeM y flota inicial (datos, no clases)
  campus_osm.json  edificios y caminos del campus tomados de OpenStreetMap (datos de dibujo y rutas)
  campus.py      carga campus.json, arma la flota y lee campus_osm.json
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
| 6. Reflexión crítica | Pendiente | — |

Presentación de la primera entrega (Fases 1 a 3):
[PDF](<docs/entrega1/Primera entrega — Flota de robots UdeM.pdf>)

La trazabilidad entre fases (requisito → tarjeta CRC → clase del UML) está en
[CHANGELOG_UML.md](docs/fase3-uml/CHANGELOG_UML.md).

## Requisitos

- Python 3.10 o superior

```bash
pip install -r requirements.txt
```

## Cómo ejecutar

```bash
python -m pytest          # pruebas del dominio, clima, asignación y enlaces de la documentación
python main.py            # demo por consola con el campus UdeM y clima simulado
python main.py --real     # la demo consultando el clima real (Open-Meteo)
python main.py --gui      # interfaz gráfica: mapa, flota, clima, solicitudes y bitácora
```

- La demo con clima simulado y las pruebas funcionan sin internet.
- `--real` consulta Open-Meteo; si la API no responde, el dron no vuela y el sistema sigue (queda en la bitácora).
- La interfaz gráfica descarga el mapa de OpenStreetMap, así que necesita internet para dibujarlo
  (© OpenStreetMap contributors). El interruptor del panel de clima cambia entre simulado y real en vivo.

## Cambios respecto al diseño

El código se apartó del UML v1 en algunos puntos. Cada diferencia, con su motivo, está en
[CAMBIOS_DISENO.md](docs/CAMBIOS_DISENO.md) y quedó reflejada en el [UML v2](docs/fase3-uml/diagrama_clases_v2.png).
