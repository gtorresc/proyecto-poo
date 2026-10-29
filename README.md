<p align="center">
  <img src="docs/img/banner.png" alt="UdeM·DESPACHO: centro de control para una flota de robots de reparto en el campus de la Universidad de Medellín" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10 o superior">
  <img src="https://img.shields.io/badge/pruebas-235%20en%20verde-3f9a6b" alt="235 pruebas en verde">
  <img src="https://img.shields.io/badge/interfaz-web%203D%20%C2%B7%20three.js-1d7f7b" alt="Interfaz web 3D con three.js">
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/licencia-MIT-f08a2c" alt="Licencia MIT"></a>
</p>

<p align="center">
  <a href="#capturas">Capturas</a> ·
  <a href="#características">Características</a> ·
  <a href="#instalación">Instalación</a> ·
  <a href="#uso">Uso</a> ·
  <a href="#arquitectura">Arquitectura</a> ·
  <a href="#documentación-del-curso">Documentación</a> ·
  <a href="#créditos">Créditos</a>
</p>

---

**UdeM·DESPACHO** es el proyecto final de Programación Orientada a Objetos: un sistema que gestiona una
flota mixta de robots de reparto (de ruedas, de orugas y drones) dentro del campus de la Universidad de
Medellín. Registra la flota, recibe solicitudes de entrega y las asigna a un robot compatible. También
calcula el costo y el tiempo por los senderos reales del campus, consulta el clima antes de autorizar un dron
y lleva una bitácora de todo lo que pasa.

El operador trabaja desde un centro de control con el campus en 2D o 3D. Ve las llamadas como balizas
sobre los edificios y despacha cada entrega a mano o en automático. Si elige un robot que no puede, el
sistema le dice exactamente qué regla lo impide.

## Capturas

<p align="center">
  <img src="docs/img/web_3d.png" alt="Centro de control web con el campus en 3D, una llamada abierta y un despacho rechazado por tormenta" width="100%">
  <br><sub><b>Vista 3D con tormenta.</b> El operador eligió el dron para la azotea del bloque 11: la ficha y la radio dicen por qué no puede volar.</sub>
</p>

<p align="center">
  <img src="docs/img/web_2d_noche.png" alt="Centro de control web en 2D de noche con la ficha y el radar del robot de orugas" width="100%">
  <br><sub><b>Vista 2D de noche.</b> Ficha del robot de orugas en ruta, con su radar: velocidad, carga, autonomía, economía y alcance.</sub>
</p>

<table>
  <tr>
    <td width="50%"><img src="docs/img/vista_satelite_3d.png" alt="Vista satélite en 3D: la foto aérea en el suelo y en los techos de los bloques" width="100%"></td>
    <td width="50%"><img src="docs/img/vista_calles_3d.png" alt="Vista de calles en 3D con los edificios extruidos sobre el mapa de OpenStreetMap" width="100%"></td>
  </tr>
  <tr>
    <td align="center"><sub><b>Vista SATÉLITE en 3D:</b> la foto aérea en el suelo y en cada techo.</sub></td>
    <td align="center"><sub><b>Vista CALLES en 3D:</b> el mapa de OpenStreetMap con los bloques extruidos.</sub></td>
  </tr>
</table>

## Características

**Modelo orientado a objetos**
- Jerarquías con polimorfismo real: `Robot` → `RobotRuedas`, `RobotOrugas`, `Dron`; `Carga` → `Documento`, `Alimento`, `Fragil`, `MaterialPeligroso`.
- Composición `Robot ◆— Bateria`, agregación `Flota ◇— Robot` y encapsulamiento con validaciones en cada clase.
- Los servicios externos (clima y festivos) están detrás de interfaces propias y se inyectan al asignador: el proveedor real se cambia por un simulador en vivo, sin tocar la lógica de asignación.

**Reglas de negocio**
- Asignación automática al robot compatible más barato, o despacho manual con el motivo exacto si no se puede (zona, peso, carga, batería, clima o festivo).
- Los robots terrestres siguen los senderos reales del campus (Dijkstra sobre datos de OpenStreetMap); el dron vuela en línea recta.
- El dron no vuela de noche, con viento o ráfagas fuertes, lluvia probable, tormenta eléctrica o niebla.
- En festivos la cafetería cierra y no se aceptan entregas de alimentos.
- Pendientes que se reintentan solos, mantenimiento por batería y bitácora exportable.

**Interfaz**
- El campus real (95 edificios y 300 caminos de OpenStreetMap) dibujado en 2D o 3D, sin tiles y sin internet.
- Tres vistas: DESPACHO (la del estilo de la consola), CALLES (mapa de OpenStreetMap) y SATÉLITE (foto aérea),
  todas en 2D o 3D. En 3D satelital cada techo muestra su pedazo de la foto real.
- Balizas sobre los edificios, rutas animadas, plantilla de robots con su estado y el nombre de cada bloque al pasar el mouse.
- El clima se ve en el mapa: nubes que avanzan con el viento, lluvia, niebla, relámpagos y luces encendidas de noche.
- Una interfaz web (HTML, CSS y three.js) en una ventana de escritorio con pywebview, sobre un modelo de
  presentación en Python que se prueba sin abrir ninguna ventana.

**APIs gratuitas, sin API key**

| API | Para qué | Si no responde |
| --- | --- | --- |
| [Open-Meteo](https://open-meteo.com) | viento, ráfagas, lluvia, visibilidad, tormenta, día o noche | el dron no vuela |
| [Nager.Date](https://date.nager.at) | festivos de Colombia | se asume día hábil |
| [Overpass (OpenStreetMap)](https://overpass-api.de) | edificios y senderos del campus (se descarga una vez) | se usan los datos guardados |
| [RoboHash](https://robohash.org) | retrato de cada robot | ícono dibujado según el tipo |
| [Tiles de OpenStreetMap](https://www.openstreetmap.org) | vista CALLES (se descarga una vez y queda en caché) | se queda en la vista DESPACHO |
| [Esri World Imagery](https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9) | vista SATÉLITE (se descarga una vez y queda en caché) | se queda en la vista DESPACHO |

## Versiones

| Versión | Dónde | Qué tiene |
| --- | --- | --- |
| Entregada (Fase 5) | tag `v1-entrega` | dominio, clima, asignación y una interfaz de CustomTkinter con el mapa de OpenStreetMap |
| Final, UdeM·DESPACHO | rama `main`, tag `v2-final` | todo lo anterior, más rutas por senderos, clima extendido, festivos, despacho manual y el centro de control web con el campus en 2D/3D |

La versión final reemplazó la interfaz de CustomTkinter por la web, con el visto bueno del profesor. La
entregada se puede ver con `git checkout v1-entrega`.

## Instalación

Requisitos: Python 3.10 o superior y Windows 10/11 con WebView2 (viene instalado en Windows 11).

```bash
git clone https://github.com/gtorresc/proyecto-poo.git
```

```bash
pip install -r requirements.txt
```

## Uso

```bash
python main.py              # centro de control (pywebview + three.js)
python main.py --real       # el mismo, con Open-Meteo y Nager.Date en vez de los simuladores
python main.py --consola    # demo por texto: un día en el campus con clima simulado
python -m pytest            # pruebas
```

- `--real` también vale con `--consola`, y `python main.py --depurar` abre las herramientas de desarrollo del navegador.
- Con los simuladores, todo funciona sin internet. Las vistas CALLES y SATÉLITE necesitan internet la primera
  vez (unos 5 segundos); después quedan guardadas en `~/.cache/flota-udem/`, fuera del repositorio.

| Acción | Cómo |
| --- | --- |
| Crear una llamada | formulario "NUEVA LLAMADA": aparece una baliza sobre el edificio de origen |
| Despachar a mano | clic en la baliza y luego en un robot de la plantilla |
| Despachar en automático | botón AUTO, o tecla `A` con la llamada abierta |
| Ver el nombre de un bloque | pasar el mouse por encima del edificio |
| Ver el radar de un robot | clic en su tarjeta (sin llamada abierta) |
| Vista 2D o 3D, girar | `Tab` y `R`, o los botones del mapa; rueda para el zoom, arrastre para moverse |
| Rotar libremente | botón derecho del mouse |
| Cambiar clima o festivos | panel "CLIMA Y CALENDARIO": simulador o APIs reales, en vivo |
| Cambiar de vista (DESPACHO, CALLES, SATÉLITE) | `V` o el botón VISTA |
| Cerrar fichas | `Esc` |

## Arquitectura

```mermaid
flowchart LR
    subgraph Presentación
        WEB["Web<br>HTML · JS · three.js"]
        PUENTE["PuenteWeb"]
        CC["CentroControl<br>modelo de presentación"]
    end
    subgraph Núcleo
        AS["AsignadorEntregas"]
        DOM["Dominio<br>Robot · Carga · Flota · Ruta<br>Solicitud · Bitácora"]
    end
    subgraph Servicios
        CLIMA["ProveedorClima<br>Open-Meteo · simulado"]
        CAL["ProveedorCalendario<br>Nager.Date · simulado"]
    end
    WEB --> PUENTE --> CC
    CC --> AS --> DOM
    AS --> CLIMA
    AS --> CAL
```

La interfaz no tiene reglas de negocio: solo lee el estado de `CentroControl` y le pasa las acciones
del operador. Si se borra, el sistema y sus pruebas siguen funcionando.

```
main.py            punto de entrada (centro de control web o --consola)
src/flota/
  dominio/         robots, cargas, batería, ubicaciones, rutas, solicitudes, bitácora
  servicios/       proveedores de clima y de festivos (API real y simulador)
  asignacion/      asignación automática y despacho manual
  presentacion/    CentroControl, paleta, retratos y mosaicos de las vistas realistas
  web/             interfaz web y PuenteWeb
  recursos/        fuentes, retratos y sus licencias
  campus.json      puntos de entrega y flota inicial
  campus_osm.json  edificios y caminos del campus (OpenStreetMap)
scripts/           descarga de la geometría del campus
tests/             pruebas con pytest
docs/              entregables del curso, UML y capturas
```

## Documentación del curso

| Fase | Entregable |
| --- | --- |
| 1. Análisis del problema | [fase1-analisis.md](docs/fase1-analisis/fase1-analisis.md) · [PDF](docs/fase1-analisis/fase1-analisis.pdf) |
| 2. Clases y responsabilidades (CRC) | [fase2-crc.md](docs/fase2-crc/fase2-crc.md) · [PDF](docs/fase2-crc/fase2-crc.pdf) |
| 3. Diseño UML | [UML v1](docs/fase3-uml/diagrama_clases_v1.png) · [fuente draw.io](docs/fase3-uml/diagrama_clases_v1.drawio) · [changelog y trazabilidad](docs/fase3-uml/CHANGELOG_UML.md) |
| 4. Justificación de decisiones | [fase4-justificacion.md](docs/fase4-justificacion/fase4-justificacion.md) · [PDF](docs/fase4-justificacion/fase4-justificacion.pdf) |
| 5. Implementación | [código](src/flota) · [pruebas](tests) · [cambios de diseño](docs/CAMBIOS_DISENO.md) · [UML v2](docs/fase3-uml/diagrama_clases_v2.png) · [fuente draw.io](docs/fase3-uml/diagrama_clases_v2.drawio) |
| Mejoras UdeM·DESPACHO | [cambios de diseño, sección 7](docs/CAMBIOS_DISENO.md) · [UML v3](docs/fase3-uml/diagrama_clases_v3.png) · [fuente draw.io](docs/fase3-uml/diagrama_clases_v3.drawio) |
| 6. Reflexión crítica | pendiente |

Presentación de la primera entrega: [PDF](<docs/entrega1/Primera entrega — Flota de robots UdeM.pdf>).
Cada diferencia entre el UML y el código, con su motivo, está en [CAMBIOS_DISENO.md](docs/CAMBIOS_DISENO.md).

## Créditos

- Datos del mapa y tiles de la vista CALLES: © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright).
- Imágenes de la vista SATÉLITE: © Esri, Maxar, Earthstar Geographics (no se incluyen en el repositorio).
- Clima: [Open-Meteo](https://open-meteo.com). Festivos: [Nager.Date](https://date.nager.at).
- Retratos de los robots: [RoboHash](https://robohash.org), set1 de Zikri Kader (CC-BY).
- Fuentes: Oswald y Share Tech Mono (SIL Open Font License). 3D: [three.js](https://threejs.org) (MIT).
- Detalle de licencias de terceros en [src/flota/recursos/CREDITOS.md](src/flota/recursos/CREDITOS.md).

## Licencia

El código de este proyecto se distribuye bajo la licencia MIT ([LICENSE.md](LICENSE.md)). Los datos, las
fuentes, los retratos y las librerías de terceros conservan sus propias licencias.
