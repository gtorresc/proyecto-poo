# Cambios de diseño: del UML v1 al código

El UML v1 ([diagrama_clases_v1.png](fase3-uml/diagrama_clases_v1.png)) salió de las tarjetas CRC antes de escribir código. Al implementarlo apareció lo que el papel no mostraba. Este anexo lista cada diferencia: qué cambió, por qué y qué se aprendió. El resultado está en [diagrama_clases_v2.png](fase3-uml/diagrama_clases_v2.png) ([fuente draw.io](fase3-uml/diagrama_clases_v2.drawio)).

Las clases, las relaciones y los patrones de las Fases 3 y 4 (herencia de `Robot`, `Carga` y `ProveedorClima`, composición `Robot ◆— Bateria`, agregación `Flota ◇— Robot`, clima inyectado) se mantuvieron sin cambios.

## 1. Reglas que cambiaron al probarlas

| Qué cambió | Por qué | Qué aprendimos |
| --- | --- | --- |
| El mantenimiento no se activa con "batería < 15 %", sino cuando `nivel <= reserva + 10` (`Robot.necesita_mantenimiento()`, constante `MARGEN_MANTENIMIENTO`). | `puede_atender` ya exige que tras la entrega queden al menos 15 %, así que la batería nunca baja de 15 %: la regla original era inalcanzable. | Dos reglas del mismo supuesto (S3) pueden anularse entre sí. Un test que intentaba llegar a mantenimiento lo mostró. |
| `puede_atender` mide la batería de **dos tramos**: del robot al origen y del origen al destino. | El UML solo hablaba de "batería suficiente". Un robot lejos del origen gasta más de lo que parece. | `cargar(carga, origen)` hace el mismo viaje al origen y descuenta esa batería, para que la predicción y el consumo coincidan. |
| El asignador consulta el clima solo cuando le toca a un dron, recorriendo los candidatos de más barato a más caro. | El primer diseño consultaba el clima de todos los drones antes de comparar costos. Dos tests lo detectaron: un robot terrestre más barato no debe depender de la red. | El orden de las operaciones también es parte del diseño, no solo qué clases existen. |
| El clima se consulta en el **destino** de la solicitud. | El UML no decía en qué punto del campus medir. Se tomó el destino (la azotea donde aterriza el dron) como supuesto propio. | El campus mide unos 450 m: un solo punto de referencia sería igual de válido. |

## 2. Miembros añadidos al UML v1

| Clase | Añadido | Motivo |
| --- | --- | --- |
| `Robot` | `terminar_mantenimiento()` | Sin él, un robot enviado a mantenimiento quedaba bloqueado para siempre y `reintentar_pendientes` no podía volver a usarlo. |
| `Robot` | `necesita_mantenimiento()` | Mantiene la regla del punto 1 dentro del robot, que es quien conoce su batería. |
| `Robot` | `cargar(carga, origen=None)` | Ver punto 1: el robot viaja al origen y gasta batería. |
| `Bateria` | propiedad `reserva_minima` | `Robot` necesita leerla sin tocar el atributo privado. |
| `Flota` | propiedad `robots` (devuelve una copia) y validaciones en `agregar` (id repetido, tipo) y `quitar` (no existe, o va en ruta) | La GUI necesita listar los robots; proteger la lista interna mantiene el encapsulamiento. |
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

## 7. Versión 3: mejoras de la rama `udem-despacho`

Después de entregar la Fase 5 se abrió la rama `udem-despacho` para mejorar el programa sin arriesgar la versión entregada (`main`). Cada cambio se anota aquí en el mismo commit que lo introduce.

| Qué cambió | Por qué | Qué aprendimos |
| --- | --- | --- |
| Nuevo archivo de datos `src/flota/campus_osm.json` (perímetro, 95 edificios con contorno y pisos, 300 caminos) y `cargar_geometria()` en `campus.py`. Lo genera una sola vez `scripts/descargar_campus_osm.py` desde la API Overpass de OpenStreetMap. | El mapa en 2D y 3D y las rutas por senderos necesitan la forma real del campus. Se descarga una vez y queda en el repositorio: el programa no depende de Overpass al ejecutarse y funciona sin internet. No es una clase del dominio, como `campus.json`. | Los datos abiertos tienen huecos. OSM no tiene los bloques 3, 4 y 12, justo tres puntos de entrega. Se trazaron a mano sobre imagen satelital, marcados como `trazado_a_mano`, y un test comprueba que cada punto de entrega cae sobre un edificio. Solo 12 de los 95 edificios traen número de pisos. |
| Nuevas clases `Ruta` (puntos y distancia) y `RedSenderos` (grafo de los senderos de OSM; camino más corto con Dijkstra y caché por par de puntos), en `dominio/ruta.py`. | El UML v1 estimaba la distancia por tierra como Haversine × `factor_ruta()` (1,3, supuesto S5). Ahora los robots terrestres recorren los senderos reales y el costo, el tiempo y la batería salen de esa ruta. | Medido sobre los 66 pares de puntos del campus, el rodeo real está entre 1,06 y 2,93 veces la línea recta, con una mediana de 1,61. El 1,3 de S5 se quedaba corto. |
| `Robot.trazar_ruta(origen, destino)` y asociación opcional `Robot → RedSenderos` (parámetro `red` del constructor). `Dron` redefine `trazar_ruta` para volar recto y ya no necesita `factor_ruta()`. `_distancia_ruta_km` usa `trazar_ruta`. | Es polimorfismo real: la misma llamada da un camino por senderos o una línea recta según el subtipo. Sin red, o sin camino entre dos puntos, se vuelve a Haversine × `factor_ruta()`, así que los tests anteriores siguen valiendo. La red es una sola, compartida por toda la flota (asociación, no composición: no nace ni muere con el robot). | Agregar el comportamiento en un método que los subtipos redefinen evitó un `if es_aereo()` en los cálculos de costo y batería. |
| `distancia_haversine_km(lat1, lon1, lat2, lon2)` sale de `Ubicacion.distancia_km` como función del módulo `ubicacion.py`. | `RedSenderos` mide tramos entre coordenadas que no son puntos de entrega. | La fórmula queda en un solo lugar; `Ubicacion.distancia_km` la llama. |
| `campus.py` arma la red con `crear_red_senderos()` usando solo los caminos internos (`TIPOS_SENDERO`), incluidas las escaleras. | Sin las escaleras, el campus queda partido: de la cafetería a Ingenierías, que están pegadas, el rodeo era 15 veces la línea recta. Supuesto S8: junto a cada escalera hay una rampa. | Una mejora futura: que `RobotRuedas` evite las escaleras, otra vez con polimorfismo. Antes habría que mapear las rampas. |
| `ReporteClima` suma `visibilidad_m`, `tormenta`, `humedad_pct` y `direccion_viento_grados`, todos opcionales. `UmbralesClima` suma `visibilidad_min_m` (1000 m). `es_favorable` rechaza al dron con tormenta eléctrica o con niebla (supuesto S9). `ServicioClimaOpenMeteo` pide `visibility`, `weather_code` (95–99 = tormenta), `relative_humidity_2m` y `wind_direction_10m`, y el simulador permite configurarlos. | En Medellín las tormentas eléctricas de la tarde y la niebla de la mañana son más comunes que el viento fuerte. La humedad y la dirección del viento no deciden nada: son para el widget del clima de la nueva interfaz. | El cambio no tocó `AsignadorEntregas` ni ningún robot: solo el reporte y sus proveedores. Es la prueba de que el contrato `ProveedorClima` aísla el clima del resto. Un dato que falta (`null` en la API) no bloquea al dron; un reporte que no llega, sí (S4). |
| Nuevo contrato `ProveedorCalendario` (abstracta: `festivo(fecha)` y `es_festivo(fecha)`) con `CalendarioNagerDate` (API Nager.Date, festivos de Colombia, una consulta por año) y `CalendarioSimulado`. `Carga.requiere_cafeteria()` devuelve True solo en `Alimento`. `AsignadorEntregas` recibe un calendario opcional (`cambiar_calendario()`, propiedad `calendario`): en festivo, un alimento queda pendiente con el motivo "cafetería cerrada (festivo: …)". | Es una regla real del campus, que cierra la cafetería en festivos, y se alimenta de una segunda API externa. Se aisló con el mismo patrón que el clima: interfaz, implementación real y simulador, inyectados por asociación. | Sumar una API nueva fue copiar un patrón ya probado; ahí está el valor de haber aislado la primera. El fail-safe es el contrario al del clima (supuesto S10): si Nager.Date no responde, se asume día hábil. Equivocarse con un festivo cuesta un almuerzo; con el clima, un dron. |
| `Robot.motivo_rechazo(solicitud)` devuelve la primera regla que falla (estado, peso, zona, tipo de carga, batería) o `None`. `puede_atender` pasa a ser `motivo_rechazo(...) is None`. | La nueva interfaz deja que el operador elija el robot, al estilo del juego *Dispatch*. Un "no" sin motivo no le sirve: necesita saber qué regla falló. | Las reglas siguen en un solo lugar y en el mismo orden. Solo cambió que ahora el método cuenta cuál falló, en vez de responder sí o no. |
| `AsignadorEntregas.despachar(solicitud, robot)` (despacho manual) y el método privado `_asignar_a`, extraído de `_intentar`. Nuevo `TipoEvento.DESPACHO_RECHAZADO`. | El despacho manual aplica las mismas reglas que el automático: festivo, `motivo_rechazo` y clima si el robot lo requiere. Si se rechaza, la solicitud no entra a la cola de reintentos automáticos: sigue esperando que el operador elija otro robot. | `_asignar_a` evita copiar el cierre de la asignación (cargar el robot, calcular el tiempo, pasar la solicitud a en curso) entre el despacho automático y el manual. |
| Nueva clase de presentación `CentroControl` (`gui/centro_control.py`), fuera del dominio. Traduce el dominio a datos simples (`estado()`, `geometria()` en metros) y convierte las acciones del operador en llamadas al dominio (`crear_solicitud`, `despachar`, `despachar_auto`, `usar_clima`, `usar_calendario`…). `tick()` avanza los viajes por la ruta real y termina el mantenimiento a los 10 s. Los paneles de CustomTkinter ya no tocan `Flota`, `Bitacora` ni `AsignadorEntregas`: solo leen y llaman a `CentroControl`. | La rama tendrá dos interfaces, CustomTkinter y web. Sin un modelo común, cada una tendría que repetir la animación, el cambio de proveedores y el armado de solicitudes. Además, la animación estaba dentro de `PanelMapa` y solo se podía probar abriendo la ventana. | Es el mismo principio que el clima, aplicado a la presentación: la interfaz depende de un contrato de datos y no del dominio. Ahora la animación, el radar y el despacho se prueban con pytest y un reloj falso (`test_centro_control.py`). El robot en mantenimiento antes quedaba bloqueado para siempre en la GUI, porque nadie llamaba a `terminar_mantenimiento()`; el test lo dejó a la vista. |

