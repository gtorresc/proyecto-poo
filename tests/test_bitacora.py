"""Bitácora de eventos."""
from datetime import datetime

import pytest

from flota.dominio.bitacora import Bitacora, EventoBitacora, TipoEvento


@pytest.fixture
def bitacora():
    b = Bitacora()
    b.registrar(TipoEvento.ENTREGA_EXITOSA, "Tesis entregada", "R-01")
    b.registrar(TipoEvento.RECHAZO_CLIMA, "Viento de 45 km/h", "D-01")
    b.registrar(TipoEvento.ENTREGA_EXITOSA, "Almuerzo entregado", "R-02")
    return b


def test_eventos_en_orden_y_devuelve_copia(bitacora):
    eventos = bitacora.eventos()
    assert [e.robot_id for e in eventos] == ["R-01", "D-01", "R-02"]
    assert isinstance(eventos, tuple)
    bitacora.registrar(TipoEvento.MANTENIMIENTO, "Recarga")
    assert len(eventos) == 3 and len(bitacora.eventos()) == 4


def test_filtrar_por_tipo(bitacora):
    assert [e.robot_id for e in bitacora.filtrar(TipoEvento.ENTREGA_EXITOSA)] == ["R-01", "R-02"]
    assert bitacora.filtrar(TipoEvento.MANTENIMIENTO) == []


def test_como_texto():
    e = EventoBitacora(TipoEvento.RECHAZO_CLIMA, "Viento", "D-01", datetime(2026, 10, 21, 9, 30, 5))
    assert e.como_texto() == "2026-10-21 09:30:05 RECHAZO POR CLIMA [D-01]: Viento"
    assert "[" not in EventoBitacora(TipoEvento.MANTENIMIENTO, "Recarga").como_texto()


def test_reporte_resume_por_tipo_y_lista_eventos(bitacora):
    reporte = bitacora.generar_reporte()
    assert "entrega exitosa: 2" in reporte and "rechazo por clima: 1" in reporte
    assert "Tesis entregada" in reporte
    assert "(sin eventos)" in Bitacora().generar_reporte()


def test_rechaza_eventos_invalidos():
    with pytest.raises(ValueError):
        Bitacora().registrar(TipoEvento.MANTENIMIENTO, "  ")
    with pytest.raises(TypeError):
        Bitacora().registrar("mantenimiento", "x")
