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
docs/uml/      diagrama de clases (PlantUML)
```

## Requisitos

- Python 3.10 o superior

```bash
pip install -r requirements.txt
```

## Estado

En desarrollo.
