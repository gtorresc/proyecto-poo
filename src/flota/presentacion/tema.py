"""Paleta de UdeM·DESPACHO (guía de estilo 10): la web la recibe con la geometría del campus."""
from pathlib import Path

RECURSOS = Path(__file__).resolve().parent.parent / "recursos"  # fuentes y retratos

# El mapa cambia de día a noche
DIA = {"fondo_mapa": "#1d7f7b", "campus": "#23918b", "edificio": "#2bb3a3", "pared": "#1f8f84",
       "arista": "#b9fff2", "sendero": "#5fd3c3", "calle": "#176a66", "ciudad": "#227f78",
       "pared_ciudad": "#1b6f69", "arista_ciudad": "#6fd6c8"}
NOCHE = {"fondo_mapa": "#0c1a1c", "campus": "#0f2225", "edificio": "#10302c", "pared": "#0b2420",
         "arista": "#46f0b4", "sendero": "#1f5a4c", "calle": "#14302e", "ciudad": "#0f2624",
         "pared_ciudad": "#0b1d1c", "arista_ciudad": "#1f6a58"}
RESALTADO = {"edificio": "#f08a2c", "pared": "#c46a1c", "arista": "#ffd2a1"}  # edificio con una llamada
# color en el que se pierden los bordes de la imagen real, de día y de noche
NEBLINA = {"satelite": ("#56635c", "#05080f"), "calles": ("#dcd8d0", "#0b0f16")}
FRANJA = {"libre": "#3f9a6b", "ocupado": "#1f6fd1", "falla": "#d2453b"}  # estado del robot
