# Fase 1 — Análisis del problema

Sistema de gestión de una flota de robots de reparto para el campus de la Universidad de Medellín: este análisis fija qué debe hacer el sistema, qué reglas lo gobiernan y qué decidimos asumir donde el enunciado es ambiguo. Aún no incluye clases (eso es la Fase 2).

## 1. Requisitos funcionales

El sistema debe cumplir 12 requisitos; RF6 es la consulta obligatoria del clima antes de usar un dron.

| ID | Requisito |
| --- | --- |
| RF1 | Registrar robots indicando tipo (ruedas, orugas, dron), identificador, carga máxima, velocidad, nivel de batería y ubicación inicial. |
| RF2 | Consultar el estado de cada robot: batería, ubicación, carga actual y si está disponible, en ruta o en mantenimiento. |
| RF3 | Recibir solicitudes de entrega con origen, destino, tipo de carga y peso. |
| RF4 | Validar que una carga cumpla sus restricciones propias (alimentos con control de temperatura, materiales peligrosos solo con robots habilitados). |
| RF5 | Asignar cada solicitud a un robot compatible según capacidad, tipo de carga permitido, batería suficiente y zona accesible. |
| RF6 | Antes de asignar un dron, consultar el clima del campus en una API pública (Open-Meteo) y rechazar la asignación si las condiciones no son favorables. |
| RF7 | Si la solicitud no puede asignarse o el dron es rechazado, reasignarla a otro robot compatible o dejarla pendiente. |
| RF8 | Calcular el costo y el tiempo estimado de una entrega según el tipo de robot, la distancia y el tipo de carga. |
| RF9 | Registrar en una bitácora las entregas exitosas, fallidas, rechazos por clima y mantenimientos. |
| RF10 | Mostrar y exportar la bitácora como reporte. |
| RF11 | Enviar a mantenimiento un robot con batería baja y reincorporarlo al terminar. |
| RF12 | Reintentar las solicitudes pendientes cuando cambien las condiciones (robot liberado o clima favorable). |

## 2. Reglas de negocio

Ocho reglas salen directamente del enunciado y siete más las dedujimos para que el sistema sea coherente.

### Explícitas (están en el enunciado)

1. Cada tipo de robot tiene su propia carga máxima, velocidad, autonomía y zonas permitidas.
2. Un robot solo puede llevar los tipos de carga permitidos para él.
3. Un robot no se asigna si su batería no alcanza para la entrega.
4. Un robot solo va a zonas accesibles para su tipo: orugas a zonas verdes, drones a azoteas.
5. Antes de autorizar un dron se consulta el clima; con viento alto o lluvia probable se rechaza.
6. Los alimentos requieren control de temperatura.
7. Los materiales peligrosos de laboratorio tienen restricciones adicionales.
8. El costo y el tiempo dependen del tipo de robot y del tipo de carga.

### Implícitas (deducidas)

1. Un robot atiende una sola entrega a la vez.
2. Un robot en mantenimiento no recibe asignaciones.
3. El peso de la carga debe ser mayor que 0 y no superar la carga máxima del robot.
4. La batería se descuenta al completar una entrega y siempre queda entre 0 % y 100 %.
5. Si no se puede conocer el clima, el dron no vuela.
6. Una carga frágil no viaja en robot de orugas, por el terreno irregular.
7. Toda asignación o rechazo queda registrado en la bitácora.

## 3. Supuestos propios

El supuesto central es el umbral de clima: un dron no vuela con viento sobre 30 km/h, ráfagas sobre 40 km/h o probabilidad de lluvia sobre 50 %.

| # | Supuesto | Justificación |
| --- | --- | --- |
| S1 | Umbral de clima: el dron no vuela si el viento sostenido supera 30 km/h, si las ráfagas superan 40 km/h o si la probabilidad de lluvia de la hora actual supera 50 %. | Los drones pequeños de reparto operan con seguridad por debajo de unos 30–35 km/h; las ráfagas son el mayor riesgo de perder el control. Con más de 50 % la lluvia es más probable que no. |
| S2 | Los drones no vuelan de noche (dato `is_day` de Open-Meteo). | Las azoteas no tienen iluminación y la visibilidad es baja; la API ya entrega el dato. |
| S3 | Un robot debe conservar al menos 15 % de batería al terminar la entrega; por debajo de 15 % pasa a mantenimiento. | Evita robots varados a mitad del campus. |
| S4 | Si la API de clima falla o tarda más de 5 s, se asume clima desfavorable. | Es preferible demorar una entrega que perder un dron. |
| S5 | Distancia en línea recta para drones y con un factor de rodeo de 1,3 para robots terrestres. | Los robots terrestres siguen senderos; el campus mide unos 450 m de punta a punta. |
| S6 | Los materiales peligrosos nunca viajan en dron. | Una caída desde una azotea pondría en riesgo a las personas. |
| S7 | El campus tiene un conjunto fijo de puntos de entrega con su zona: edificios (bloques), zonas verdes (canchas, Eco Huerta) y azoteas de los bloques de 4 pisos. | Simplifica la ubicación sin geocodificación; los puntos se toman de OpenStreetMap. |

## 4. Preguntas al cliente

Estas nueve preguntas cubren los vacíos del enunciado que más afectan el diseño.

1. ¿Qué pasa con una entrega que ningún robot puede hacer en ese momento: se espera, se cancela o se avisa a alguien?
2. ¿Hay prioridades entre solicitudes, por ejemplo material de laboratorio antes que documentos?
3. ¿Qué temperatura deben mantener los alimentos y por cuánto tiempo máximo?
4. ¿Qué tipos de materiales peligrosos se transportan y qué normativa aplica?
5. ¿Los drones pueden volar sobre zonas con personas o solo entre azoteas?
6. ¿El costo se cobra a la facultad solicitante? ¿Existe una tarifa definida?
7. ¿Cada cuánto se hace mantenimiento y cuánto dura? ¿Hay estaciones de carga fijas?
8. ¿Se opera de noche o los fines de semana?
9. ¿Quién puede crear solicitudes: cualquier persona o solo personal autorizado?
