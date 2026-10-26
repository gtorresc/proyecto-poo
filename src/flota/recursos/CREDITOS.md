# Créditos de los recursos

| Recurso | Autor | Licencia |
| --- | --- | --- |
| `fuentes/Oswald-SemiBold.ttf` | The Oswald Project Authors | SIL Open Font License 1.1 (`fuentes/OFL-oswald.txt`) |
| `fuentes/ShareTechMono-Regular.ttf` | Carrois Type Design, Ralph du Carrois | SIL Open Font License 1.1 (`fuentes/OFL-sharetechmono.txt`) |
| `retratos/*.png` | RoboHash (robohash.org), set1 de Zikri Kader | CC-BY 3.0/4.0 |
| `web/pagina/vendor/three.module.min.js`, `OrbitControls.js` (versión 0.160.0) | three.js authors | MIT (`web/pagina/vendor/LICENSE-three.txt`) |

Las vistas CALLES y SATÉLITE usan tiles de OpenStreetMap (© OpenStreetMap contributors, ODbL) y de
Esri World Imagery (© Esri, Maxar, Earthstar Geographics). No están en el repositorio: se descargan la
primera vez y se guardan en `~/.cache/flota-udem/` (ver `gui/mosaico.py`).

Los retratos se generan a partir del id del robot (`gui/retratos.py`). Los que faltan se descargan
la primera vez y, sin internet, se reemplazan por un ícono dibujado según el tipo de robot.
