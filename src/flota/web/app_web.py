"""Abre la interfaz web en una ventana de escritorio (pywebview usa el WebView2 de Windows)."""
from pathlib import Path

from flota.gui.centro_control import crear_centro
from flota.web.puente import PuenteWeb

PAGINA = Path(__file__).with_name("pagina") / "index.html"


def main(real: bool = False, depurar: bool = False) -> None:
    import webview  # solo esta interfaz lo necesita
    puente = PuenteWeb(crear_centro(real))
    puente._ventana = webview.create_window("UdeM·DESPACHO - Flota de reparto (web)", str(PAGINA),
                                            js_api=puente, width=1366, height=860, min_size=(1100, 720),
                                            background_color="#1b2b2e")
    webview.start(http_server=True, debug=depurar)  # el servidor local permite módulos de JavaScript
