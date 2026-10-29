"""PuenteWeb: lo que la página web puede pedirle a Python (sin abrir ninguna ventana)."""
import base64
import json

import pytest

from flota.asignacion.asignador import AsignadorEntregas
from flota.campus import cargar_campus, cargar_geometria
from flota.dominio.bitacora import Bitacora
from flota.presentacion.centro_control import CentroControl
from flota.servicios.calendario_simulado import CalendarioSimulado
from flota.servicios.clima_simulado import ServicioClimaSimulado
from flota.web.app_web import PAGINA
from flota.web.puente import PuenteWeb


@pytest.fixture
def puente():
    ubicaciones, flota = cargar_campus()
    bitacora = Bitacora()
    centro = CentroControl(ubicaciones, flota, AsignadorEntregas(flota, ServicioClimaSimulado(), bitacora),
                           bitacora, cargar_geometria(), clima_real=ServicioClimaSimulado(),
                           calendario_real=CalendarioSimulado())
    centro.usar_clima(False)
    centro.usar_calendario(False)
    return PuenteWeb(centro)


def test_todo_lo_que_devuelve_se_puede_pasar_a_json(puente):
    id_sol = puente.crear_solicitud("cafeteria", "biblioteca", "documento", 1)
    json.dumps([puente.geometria(), puente.estado(), puente.despachar(id_sol, "R-01")])


def test_los_errores_vuelven_como_datos_y_no_rompen_la_pagina(puente):
    assert "error" in puente.crear_solicitud("cafeteria", "cafeteria", "documento", 1)
    assert "error" in puente.crear_solicitud("cafeteria", "biblioteca", "documento", "pesado")
    assert "error" in puente.despachar(999, "R-01")


def test_despacho_manual_y_clima_desde_la_pagina(puente):
    puente.configurar_clima(10, 10, True, 10_000, True)
    id_sol = puente.crear_solicitud("biblioteca", "azotea_b11", "documento", 1)
    assert puente.despachar(id_sol, "D-01") == (False, "clima desfavorable: tormenta eléctrica")
    puente.configurar_clima(10, 10, True, 10_000, False)
    assert puente.despachar_auto(id_sol) == (True, "")
    assert puente.estado()["resumen"]["en_ruta"] == 1


def test_retratos_y_fuentes_viajan_en_base64(puente):
    assert puente.retrato("R-01", "Ruedas").startswith("data:image/png;base64,")
    fuentes = puente.fuentes()
    assert set(fuentes) == {"Oswald-SemiBold", "ShareTechMono-Regular"}
    assert base64.b64decode(fuentes["ShareTechMono-Regular"])[:4] == b"\x00\x01\x00\x00"  # TrueType


def test_la_pagina_y_sus_archivos_existen():
    html = PAGINA.read_text(encoding="utf-8")
    for archivo in ("estilos.css", "app.js"):
        assert archivo in html and (PAGINA.parent / archivo).exists()
    assert (PAGINA.parent / "mapa2d.js").exists()


def test_three_js_va_dentro_del_proyecto_y_no_depende_de_internet():
    html = PAGINA.read_text(encoding="utf-8")
    vendor = PAGINA.parent / "vendor"
    assert '"three": "./vendor/three.module.min.js"' in html  # import map local, sin CDN
    for archivo in ("three.module.min.js", "OrbitControls.js", "LICENSE-three.txt"):
        assert (vendor / archivo).exists()
    mapa3d = (PAGINA.parent / "mapa3d.js").read_text(encoding="utf-8")
    assert "http" not in mapa3d.split("\n", 1)[1]  # ningún recurso remoto
    assert 'import("./mapa3d.js")' in (PAGINA.parent / "app.js").read_text(encoding="utf-8")  # con respaldo 2D


def test_el_mosaico_viaja_como_data_url_o_como_error(puente, monkeypatch):
    from PIL import Image

    from flota.web import puente as modulo
    monkeypatch.setattr(modulo, "mosaico", lambda capa: (Image.new("RGB", (8, 8), "green"), [-1, -1, 1, 1]))
    datos = puente.mosaico("satelite")
    assert datos["imagen"].startswith("data:image/jpeg;base64,") and datos["caja"] == [-1, -1, 1, 1]
    assert "Esri" in datos["credito"]
    monkeypatch.setattr(modulo, "mosaico", lambda capa: None)  # sin red
    assert puente.mosaico("calles") == {"error": "vista realista sin conexión"}
    assert "error" in puente.mosaico("google")


def test_la_web_recibe_la_paleta_de_python(puente):
    from flota.presentacion import tema
    t = puente.geometria()["tema"]
    assert t["dia"] == tema.DIA and t["noche"] == tema.NOCHE and t["franja"] == tema.FRANJA
    assert t["neblina"]["satelite"] == tema.NEBLINA["satelite"]
    pagina = (PAGINA.parent / "mapa2d.js").read_text(encoding="utf-8")
    assert "#1d7f7b" not in pagina  # el JS ya no tiene su propia copia de los colores


def test_exportar_a_una_carpeta_que_no_existe_vuelve_como_error(puente, tmp_path):
    class Ventana:
        def create_file_dialog(self, *args, **kwargs):
            return str(tmp_path / "no_existe" / "reporte.txt")
    puente._ventana = Ventana()
    assert "no se pudo guardar" in puente.exportar_bitacora()["error"]
    puente._ventana.create_file_dialog = lambda *a, **k: str(tmp_path / "reporte.txt")
    assert puente.exportar_bitacora() == str(tmp_path / "reporte.txt")
    assert "REPORTE" in (tmp_path / "reporte.txt").read_text(encoding="utf-8")
