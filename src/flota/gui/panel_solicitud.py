"""Formulario de nueva solicitud: arma el objeto y se lo entrega al asignador."""
import customtkinter as ctk

from flota.dominio.carga import Alimento, Documento, Fragil, MaterialPeligroso
from flota.dominio.solicitud import SolicitudEntrega

TIPOS_CARGA = {
    "Documento": lambda peso: Documento("Documento", peso),
    "Alimento": lambda peso: Alimento("Alimento", peso, 60),
    "Frágil": lambda peso: Fragil("Carga frágil", peso),
    "Material peligroso": lambda peso: MaterialPeligroso("Material peligroso", peso, 2),
}


class PanelSolicitud(ctk.CTkFrame):

    def __init__(self, master, ubicaciones: dict, asignador, al_cambiar):
        super().__init__(master)
        self._por_nombre = {u.nombre: u for u in ubicaciones.values()}
        self._asignador = asignador
        self._al_cambiar = al_cambiar
        nombres = list(self._por_nombre)
        ctk.CTkLabel(self, text="NUEVA SOLICITUD", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(8, 2))
        self._origen = self._lista("Origen", nombres)
        self._destino = self._lista("Destino", nombres)
        self._destino.set(nombres[1])
        self._carga = self._lista("Carga", list(TIPOS_CARGA))
        ctk.CTkLabel(self, text="Peso (kg)", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)
        self._peso = ctk.CTkEntry(self)
        self._peso.insert(0, "1.5")
        self._peso.pack(fill="x", padx=10)
        ctk.CTkButton(self, text="ASIGNAR", command=self._asignar).pack(fill="x", padx=10, pady=8)
        self._resultado = ctk.CTkLabel(self, text="", wraplength=300, justify="left")
        self._resultado.pack(anchor="w", padx=10, pady=(0, 8))

    def _lista(self, texto, valores):
        ctk.CTkLabel(self, text=texto, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)
        menu = ctk.CTkOptionMenu(self, values=valores, dynamic_resizing=False)
        menu.pack(fill="x", padx=10)
        return menu

    def _asignar(self) -> None:
        try:
            carga = TIPOS_CARGA[self._carga.get()](float(self._peso.get().replace(",", ".")))
            solicitud = SolicitudEntrega(self._por_nombre[self._origen.get()],
                                         self._por_nombre[self._destino.get()], carga)
        except ValueError as error:  # peso no numérico, <= 0 u origen igual al destino
            self._mostrar(f"Datos inválidos: {error}", "#c0392b")
            return
        if self._asignador.asignar(solicitud):
            self._mostrar(f"{solicitud.robot.id} · ${solicitud.costo:,.0f} · {solicitud.tiempo_min:.1f} min",
                          "#2e8b57")
        else:
            self._mostrar(f"Pendiente: {solicitud.motivo}", "#e6b800")
        self._al_cambiar()

    def _mostrar(self, texto: str, color: str) -> None:
        self._resultado.configure(text=texto, text_color=color)
