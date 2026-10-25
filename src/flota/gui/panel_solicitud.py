"""Formulario de nueva llamada: CentroControl la pone en el mapa como baliza, sin asignarla todavía."""
import customtkinter as ctk

from flota.gui import tema


class PanelSolicitud(ctk.CTkFrame):

    def __init__(self, master, centro, al_crear):
        super().__init__(master)
        geo = centro.geometria()
        self._clave_lugar = {u["nombre"]: u["clave"] for u in geo["ubicaciones"]}
        self._clave_carga = {t["nombre"]: t["clave"] for t in geo["tipos_carga"]}
        self._centro = centro
        self._al_crear = al_crear
        nombres = list(self._clave_lugar)
        ctk.CTkLabel(self, text="NUEVA LLAMADA", font=tema.fuente(17, True)).pack(
            anchor="w", padx=10, pady=(6, 0))
        self._origen = self._lista("Origen", nombres)
        self._destino = self._lista("Destino", nombres)
        self._destino.set(nombres[1])
        self._carga = self._lista("Carga", list(self._clave_carga))
        ctk.CTkLabel(self, text="peso kg", font=tema.fuente(12), height=16).pack(anchor="w", padx=10)
        self._peso = ctk.CTkEntry(self)
        self._peso.insert(0, "1.5")
        self._peso.pack(fill="x", padx=10)
        ctk.CTkButton(self, text="CREAR LLAMADA", font=tema.fuente(15, True),
                      command=self._asignar).pack(fill="x", padx=10, pady=8)
        self._resultado = ctk.CTkLabel(self, text="", wraplength=300, justify="left", font=tema.fuente(13))
        self._resultado.pack(anchor="w", padx=10, pady=(0, 8))

    def _lista(self, texto, valores):
        ctk.CTkLabel(self, text=texto.lower(), font=tema.fuente(12), height=16).pack(anchor="w", padx=10)
        menu = ctk.CTkOptionMenu(self, values=valores, dynamic_resizing=False)
        menu.pack(fill="x", padx=10)
        return menu

    def _asignar(self) -> None:
        try:
            id_sol = self._centro.crear_solicitud(
                self._clave_lugar[self._origen.get()], self._clave_lugar[self._destino.get()],
                self._clave_carga[self._carga.get()], float(self._peso.get().replace(",", ".")))
        except ValueError as error:  # peso no numérico, <= 0 u origen igual al destino
            self._mostrar(f"DATOS INVÁLIDOS: {error}", tema.FALLA)
            return
        self._mostrar(f"LLAMADA #{id_sol} EN EL MAPA", "#46f0b4")
        self._al_crear(id_sol)

    def _mostrar(self, texto: str, color: str) -> None:
        self._resultado.configure(text=texto, text_color=color)
