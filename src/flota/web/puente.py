"""Puente entre JavaScript y CentroControl: lo único de Python que ve la página web.

pywebview llama a estos métodos desde varios hilos; un candado evita que dos llamadas toquen
el dominio a la vez. Todo lo que devuelven son datos simples (se convierten a JSON).
"""
import base64
import io
import threading

from flota.presentacion.mosaico import CAPAS, mosaico
from flota.presentacion.retratos import retrato
from flota.presentacion import tema
from flota.presentacion.tema import RECURSOS


class PuenteWeb:

    def __init__(self, centro):
        self._centro = centro
        self._candado = threading.Lock()
        self._ventana = None  # la pone app_web; hace falta para el diálogo de guardar

    def _llamar(self, accion, *args):
        """Ejecuta una acción del operador; un dato inválido vuelve como {'error': ...}, no como excepción."""
        with self._candado:
            try:
                return accion(*args)
            except (ValueError, TypeError) as error:
                return {"error": str(error)}

    # --- Lecturas ----------------------------------------------------------
    def geometria(self) -> dict:
        """La geometría del campus y los colores de presentacion/tema.py: la web no tiene su propia copia."""
        return {**self._centro.geometria(), "tema": {
            "dia": tema.DIA, "noche": tema.NOCHE, "franja": tema.FRANJA,
            "resaltado": tema.RESALTADO, "neblina": tema.NEBLINA}}

    def estado(self) -> dict:
        """La página lo pide cada 50 ms: también avanza la simulación."""
        with self._candado:
            self._centro.tick()
            return self._centro.estado()

    def retrato(self, id_robot: str, tipo: str) -> str:
        """Retrato como data URL (puede bajarlo de RoboHash la primera vez; fuera del candado)."""
        buffer = io.BytesIO()
        retrato(id_robot, tipo).save(buffer, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

    def mosaico(self, capa: str) -> dict:
        """Mosaico de CALLES o SATÉLITE como data URL; la primera vez se baja (fuera del candado)."""
        if capa not in CAPAS:
            return {"error": f"Vista desconocida: {capa}"}
        resultado = mosaico(capa)
        if resultado is None:
            return {"error": "vista realista sin conexión"}
        imagen, caja = resultado
        buffer = io.BytesIO()
        imagen.save(buffer, format="JPEG", quality=85)
        return {"imagen": "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode(),
                "caja": caja, "credito": CAPAS[capa]["credito"]}

    def fuentes(self) -> dict:
        """Las mismas fuentes de la versión de escritorio, en base64 para la API FontFace."""
        return {archivo.stem: base64.b64encode(archivo.read_bytes()).decode()
                for archivo in (RECURSOS / "fuentes").glob("*.ttf")}

    # --- Acciones del operador ---------------------------------------------
    def crear_solicitud(self, origen, destino, tipo_carga, peso_kg):
        return self._llamar(self._centro.crear_solicitud, origen, destino, tipo_carga, peso_kg)

    def despachar(self, id_solicitud, id_robot):
        return self._llamar(self._centro.despachar, id_solicitud, id_robot)

    def despachar_auto(self, id_solicitud):
        return self._llamar(self._centro.despachar_auto, id_solicitud)

    def usar_clima(self, real):
        return self._llamar(self._centro.usar_clima, bool(real))

    def configurar_clima(self, viento, lluvia, dia, visibilidad, tormenta):
        return self._llamar(self._centro.configurar_clima, float(viento), float(lluvia), bool(dia),
                            float(visibilidad), bool(tormenta))

    def usar_calendario(self, real):
        return self._llamar(self._centro.usar_calendario, bool(real))

    def configurar_festivo(self, nombre):
        return self._llamar(self._centro.configurar_festivo, nombre or None)

    def exportar_bitacora(self):
        """Abre el diálogo de guardar; devuelve la ruta, '' si se canceló o {'error': ...} si no se pudo escribir."""
        import webview
        with self._candado:
            reporte = self._centro.exportar_bitacora()
        rutas = self._ventana.create_file_dialog(webview.SAVE_DIALOG, save_filename="reporte_flota.txt")
        if not rutas:
            return ""
        ruta = rutas if isinstance(rutas, str) else rutas[0]
        try:
            with open(ruta, "w", encoding="utf-8") as archivo:
                archivo.write(reporte)
        except OSError as error:  # carpeta sin permiso, archivo abierto en otro programa...
            return {"error": f"no se pudo guardar el reporte: {error.strerror or error}"}
        return ruta
