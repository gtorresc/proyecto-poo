"""Demo por consola: un día en el campus UdeM. `python main.py` (clima simulado); `--real` usa Open-Meteo y `--gui` abre la ventana."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from flota.asignacion.asignador import AsignadorEntregas
from flota.campus import cargar_campus
from flota.dominio.bitacora import Bitacora
from flota.dominio.carga import Alimento, Documento, Fragil, MaterialPeligroso
from flota.dominio.solicitud import SolicitudEntrega
from flota.servicios.clima_open_meteo import ServicioClimaOpenMeteo
from flota.servicios.clima_simulado import ServicioClimaSimulado


def main(real: bool = False) -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows usa cp1252 por defecto
    sitio, flota = cargar_campus()
    simulado = ServicioClimaSimulado()
    bitacora = Bitacora()
    asignador = AsignadorEntregas(flota, ServicioClimaOpenMeteo() if real else simulado, bitacora)

    def pedir(titulo, origen, destino, carga):
        s = SolicitudEntrega(sitio[origen], sitio[destino], carga)
        ok = asignador.asignar(s)
        resultado = (f"{s.robot.id}, ${s.costo:,.0f}, {s.tiempo_min:.1f} min" if ok
                     else f"PENDIENTE ({s.motivo})")
        print(f"[{titulo}] {resultado}")
        return s

    print("== Pedidos con buen clima ==")
    pedidas = [
        pedir("Tesis a la biblioteca", "ingenierias", "biblioteca", Documento("Tesis", 1)),
        pedir("Almuerzo a Derecho", "cafeteria", "derecho", Alimento("Almuerzo", 1.5, 60)),
        pedir("Reactivos a la huerta", "laboratorios", "eco_huerta", MaterialPeligroso("Reactivos", 4, 2)),
    ]
    print("\n== Mal clima: viento de 45 km/h ==")
    if not real:
        simulado.configurar(viento=45, rafagas=55, lluvia=20, dia=True)
    pedidas.append(pedir("Documento a la azotea", "biblioteca", "azotea_b11", Documento("Acta", 1)))
    pedidas.append(pedir("Equipo frágil a la azotea", "correspondencia", "azotea_b12", Fragil("Equipo", 2)))

    print("\n== Se completan las entregas y mejora el clima ==")
    if not real:
        simulado.configurar(viento=10, rafagas=15, lluvia=10, dia=True)
    for s in pedidas:
        if s.estado.value == "asignada":
            asignador.completar_entrega(s)
    asignador.reintentar_pendientes()
    for s in pedidas:
        if s.estado.value == "asignada":
            asignador.completar_entrega(s)

    print("\n" + bitacora.generar_reporte())


if __name__ == "__main__":
    if "--gui" in sys.argv:
        from flota.gui.app import main as abrir_gui
        abrir_gui(real="--real" in sys.argv)
    else:
        main(real="--real" in sys.argv)
