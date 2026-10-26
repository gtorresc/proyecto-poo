# Cambios de diseño: del UML v1 al código

El UML v1 ([diagrama_clases_v1.png](fase3-uml/diagrama_clases_v1.png)) salió de las tarjetas CRC antes de escribir código. Al implementarlo apareció lo que el papel no mostraba. Este anexo lista cada diferencia: qué cambió, por qué y qué se aprendió. El resultado está en [diagrama_clases_v2.png](fase3-uml/diagrama_clases_v2.png) ([fuente draw.io](fase3-uml/diagrama_clases_v2.drawio)).

Las clases, las relaciones y los patrones de las Fases 3 y 4 (herencia de `Robot`, `Carga` y `ProveedorClima`, composición `Robot ◆— Bateria`, agregación `Flota ◇— Robot`, clima inyectado) se mantuvieron sin cambios.

## 1. Reglas que cambiaron al probarlas

| Qué cambió | Por qué | Qué aprendimos |
| --- | --- | --- |
| El mantenimiento no se activa con "batería < 15 %", sino cuando `nivel <= reserva + 10` (`Robot.necesita_mantenimiento()`, constante `MARGEN_MANTENIMIENTO`). | `puede_atender` ya exige que tras la entrega queden al menos 15 %, así que la batería nunca baja de 15 %: la regla original era inalcanzable. | Dos reglas del mismo supuesto (S3) pueden anularse entre sí. Un test que intentaba llegar a mantenimiento lo mostró. |
| `puede_atender` mide la batería de **dos tramos**: del robot al origen y del origen al destino. | El UML solo hablaba de "batería suficiente". Un robot lejos del origen gasta más de lo que parece. | `cargar(carga, origen)` hace el mismo viaje al origen y descuenta esa batería, para que la predicción y el consumo coincidan. |
| El asignador consulta el clima solo cuando le toca a un dron, recorriendo los candidatos de más barato a más caro. | El primer diseño consultaba el clima de todos los drones antes de comparar costos. Dos tests lo detectaron: un robot terrestre más barato no debe depender de la red. | El orden de las operaciones también es parte del diseño, no solo qué clases existen. |
| El robot sale de mantenimiento solo, `DURACION_MANTENIMIENTO_S` (30 s) después de entrar. `AsignadorEntregas` guarda la hora de salida con un reloj inyectable y la revisa en `reintentar_pendientes` y en el ciclo de 1 s de la ventana. | La auditoría técnica ([AUDIT_REPORT.md](../AUDIT_REPORT.md), H2) mostró que nadie llamaba a `terminar_mantenimiento()`: cada robot que llegaba al 25 % quedaba fuera de la flota para siempre. | Añadir un método no basta: alguien tiene que llamarlo. El reloj inyectable (el mismo patrón de `PanelMapa`) permite probarlo sin esperar 30 s. |
| `AsignadorEntregas.asignar` rechaza con `ValueError` una solicitud que ya no está pendiente y la saca de la cola si se asigna. | La auditoría (H1) mostró que reasignar una solicitud dejaba un robot en ruta sin entrega: `_intentar` cargaba el robot antes de que la solicitud rechazara el cambio de estado. | Las validaciones van antes de cualquier cambio de estado, no después. |
| El clima se consulta en el **destino** de la solicitud. | El UML no decía en qué punto del campus medir. Se tomó el destino (la azotea donde aterriza el dron) como supuesto propio. | El campus mide unos 450 m: un solo punto de referencia sería igual de válido. |

## 2. Miembros añadidos al UML v1

| Clase | Añadido | Motivo |
| --- | --- | --- |
| `Robot` | `terminar_mantenimiento()` | Sin él, un robot enviado a mantenimiento quedaba bloqueado para siempre y `reintentar_pendientes` no podía volver a usarlo. |
| `Robot` | `necesita_mantenimiento()` | Mantiene la regla del punto 1 dentro del robot, que es quien conoce su batería. |
| `Robot` | `cargar(carga, origen=None)` | Ver punto 1: el robot viaja al origen y gasta batería. |
| `Bateria` | propiedad `reserva_minima` | `Robot` necesita leerla sin tocar el atributo privado. |
| `Flota` | propiedad `robots` (devuelve una copia) y validaciones en `agregar` (id repetido, tipo) y `quitar` (no existe, o va en ruta) | La GUI necesita listar los robots; proteger la lista interna mantiene el encapsulamiento. |
| `AsignadorEntregas` | `liberar_mantenimientos()`, parámetro `reloj` y atributo `_en_mantenimiento` | Ver punto 1: salida automática de mantenimiento. |
| `AsignadorEntregas` | `pendientes`, `en_curso`, `proveedor_clima` (solo lectura), atributo `_en_curso` y método privado `_intentar` | La animación del mapa necesita saber qué viajes están en curso, incluidas las pendientes que se reasignan solas al mejorar el clima. `_intentar` evita duplicar la lógica entre `asignar` y `reintentar_pendientes`. |
| `ProveedorClima` | propiedad `umbrales` | El asignador y los paneles de la GUI evalúan reportes con los mismos umbrales del proveedor. |
| `ReporteClima` | `no_disponible()` (constructor alternativo) y atributo `_temperatura_c` | Un fallo de red se representa con un reporte "no disponible" y no con una excepción (supuesto S4). La temperatura venía en la CRC, no en el UML. |
| `EventoBitacora` | parámetro opcional `fecha` | Permite probar `como_texto()` con una fecha fija. |
| `SolicitudEntrega` | contador de ids a nivel de módulo y validaciones (origen distinto de destino, tipos) | El UML pedía `_id: int` sin decir quién lo genera. |

## 3. Del UML que no existe en el código

| Elemento | Qué pasó |
| --- | --- |
| `ServicioClimaOpenMeteo._url_base` | Es una constante del módulo (`URL`), no un atributo de instancia: nunca cambia entre objetos. Se conserva `_timeout_s`. |

## 4. Fuera del UML a propósito

| Elemento | Motivo |
| --- | --- |
| `src/flota/campus.json` y `src/flota/campus.py` | Son datos (los puntos reales del campus y la flota inicial), no clases del dominio. La demo y la GUI cargan lo mismo. |
| `main.py` | Punto de entrada: demo por consola, `--real` para Open-Meteo y `--gui` para la ventana. |
| `src/flota/gui/` | Capa de presentación. No tiene reglas de negocio: solo llama a `AsignadorEntregas` y lee `Flota` y `Bitacora`. Si se borra, el sistema y sus tests siguen funcionando. |

## 5. Decidido no implementar

| Elemento | Motivo |
| --- | --- |
| Reporte de la bitácora en CSV | La CRC lo mencionaba; se entregó en texto (`generar_reporte()` y el botón "Exportar reporte"), que cubre el requisito. |
| OSRM (rutas reales) y Nager.Date (festivos) | Eran opcionales. La distancia es Haversine × `factor_ruta()`, como en el UML v1. |

## 6. Dos hallazgos técnicos fuera del dominio

- **El mapa tardaba ~20 s por cada tile.** En una red con IPv6 bloqueado, `requests` espera a que fallen las 4 direcciones IPv6 antes de probar IPv4, y `tkintermapview` no pone timeout. Se arregló en `gui/panel_mapa.py` con una sesión que fuerza IPv4 y tiene timeout de 10 s. Aprendizaje: una dependencia externa puede fallar por la red de quien la usa, no por el código; por eso el clima real también tiene timeout y respuesta "no disponible".
- **OpenStreetMap exige identificar la aplicación.** `tkintermapview` manda un `User-Agent` fijo que OSM puede bloquear; el mapa envía `FlotaRobotsUdeM/1.0` (política de uso de tiles de OSM).
