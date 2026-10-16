# proyecto-poo

Proyecto de aula POO: **sistema de gestión de una flota de robots de reparto universitario**.

La universidad cuenta con robots terrestres de ruedas, de orugas y drones que transportan
documentos, alimentos, objetos frágiles y materiales de laboratorio dentro del campus.
El sistema registra la flota, recibe solicitudes de entrega, las asigna a un robot compatible,
calcula costos y tiempos, consulta el clima (Open-Meteo) antes de autorizar un dron y lleva
una bitácora de eventos.

## Estructura

```
src/flota/
  dominio/     robots, cargas, batería, ubicaciones, solicitudes, bitácora
  servicios/   proveedores de clima (API real y simulado)
  asignacion/  reglas de asignación de entregas
  gui/         interfaz gráfica (CustomTkinter + mapa OpenStreetMap)
tests/         pruebas con pytest
docs/          entregables por fase (análisis, CRC, UML)
```

## Avance por fases

| Fase | Estado | Entregable |
| --- | --- | --- |
| 1. Análisis del problema | Hecha | [fase1-analisis.md](docs/fase1-analisis/fase1-analisis.md) · [PDF](docs/fase1-analisis/fase1-analisis.pdf) |
| 2. Clases y responsabilidades (CRC) | Hecha | [fase2-crc.md](docs/fase2-crc/fase2-crc.md) · [PDF](docs/fase2-crc/fase2-crc.pdf) |
| 3. Diseño UML | Hecha | [diagrama_clases_v1.png](docs/uml/diagrama_clases_v1.png) · [fuente draw.io](docs/uml/diagrama_clases_v1.drawio) · [changelog y trazabilidad](docs/uml/CHANGELOG_UML.md) |
| 4. Justificación de decisiones | Pendiente | — |
| 5. Implementación | Pendiente | — |
| 6. Reflexión crítica | Pendiente | — |

La trazabilidad entre fases (requisito → tarjeta CRC → clase del UML) está en
[CHANGELOG_UML.md](docs/uml/CHANGELOG_UML.md).

## Requisitos

- Python 3.10 o superior

```bash
pip install -r requirements.txt
```

## Estado

En desarrollo.
