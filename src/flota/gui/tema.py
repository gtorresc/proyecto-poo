"""Paleta, fuentes y tema de CustomTkinter de UdeM·DESPACHO (guía de estilo 10)."""
import sys
from pathlib import Path

import customtkinter as ctk

RECURSOS = Path(__file__).resolve().parent.parent / "recursos"
TEMA_JSON = Path(__file__).with_name("tema_udem.json")  # colores de los widgets, en modo oscuro

# Paleta: el mapa cambia de día a noche; el resto de la interfaz no
DIA = {"fondo_mapa": "#1d7f7b", "campus": "#23918b", "edificio": "#2bb3a3", "pared": "#1f8f84",
       "arista": "#b9fff2", "sendero": "#5fd3c3", "calle": "#176a66", "ciudad": "#227f78",
       "pared_ciudad": "#1b6f69", "arista_ciudad": "#6fd6c8"}
NOCHE = {"fondo_mapa": "#0c1a1c", "campus": "#0f2225", "edificio": "#10302c", "pared": "#0b2420",
         "arista": "#46f0b4", "sendero": "#1f5a4c", "calle": "#14302e", "ciudad": "#0f2624",
         "pared_ciudad": "#0b1d1c", "arista_ciudad": "#1f6a58"}
RESALTADO = {"edificio": "#f08a2c", "pared": "#c46a1c", "arista": "#ffd2a1"}  # edificio con una llamada
BISEL = "#1b2b2e"
PANEL = "#132326"
TEXTO = "#c9e6e2"
TEXTO_BARRA = "#9fbfbd"
ALERTA = "#f08a2c"   # lo que exige acción: balizas, edificios resaltados
OCUPADO = "#1f6fd1"
LIBRE = "#3f9a6b"
FALLA = "#d2453b"    # con moderación
PAPEL = "#f1e4c6"
TINTA = "#2a2a2a"
FRANJA = {"libre": LIBRE, "ocupado": OCUPADO, "falla": FALLA}
ETIQUETA_FRANJA = {"libre": "DISPONIBLE", "ocupado": "EN RUTA", "falla": "MANTENIMIENTO"}

TITULO = "Oswald SemiBold"   # nombres y títulos; si no carga, Tk usa su fuente por defecto
MONO = "Share Tech Mono"     # datos, barras y bitácora


def bateria_color(nivel: float) -> str:
    return LIBRE if nivel > 50 else ALERTA if nivel > 25 else FALLA


def aplicar_tema() -> None:
    """Carga las fuentes del proyecto y el tema. Llamar antes de crear la ventana."""
    if sys.platform == "win32":  # en otros sistemas se usan las fuentes del sistema
        import ctypes
        for fuente in (RECURSOS / "fuentes").glob("*.ttf"):
            ctypes.windll.gdi32.AddFontResourceExW(str(fuente), 0x10, 0)  # 0x10: solo para este proceso
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme(str(TEMA_JSON))


def fuente(tamano: int, titulo: bool = False) -> ctk.CTkFont:
    return ctk.CTkFont(family=TITULO if titulo else MONO, size=tamano)
