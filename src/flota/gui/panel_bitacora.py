"""Radio: la bitácora como un registro de despacho, coloreada por tipo, y exportación del reporte."""
from tkinter import filedialog, messagebox

import customtkinter as ctk

from flota.gui import tema

COLOR_TIPO = {"ENTREGA_EXITOSA": "#46f0b4", "ENTREGA_FALLIDA": tema.FALLA, "RECHAZO_CLIMA": tema.ALERTA,
              "SOLICITUD_PENDIENTE": tema.ALERTA, "MANTENIMIENTO": "#6fb6ff",
              "DESPACHO_RECHAZADO": tema.FALLA}


class PanelBitacora(ctk.CTkFrame):

    def __init__(self, master, centro):
        super().__init__(master)
        self._centro = centro
        self._mostrados = 0
        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(cabecera, text="RADIO", font=tema.fuente(17, True)).pack(side="left")
        ctk.CTkButton(cabecera, text="EXPORTAR", width=90, height=24, font=tema.fuente(12),
                      command=self._exportar).pack(side="right")
        self._texto = ctk.CTkTextbox(self, height=130, state="disabled", font=tema.fuente(12), wrap="word")
        self._texto.pack(fill="both", expand=True, padx=10, pady=8)
        for tipo, color in COLOR_TIPO.items():
            self._texto.tag_config(tipo, foreground=color)

    def refrescar(self, estado: dict) -> None:
        bitacora = estado["bitacora"]
        nuevos = bitacora["total"] - self._mostrados
        if nuevos <= 0:
            return
        self._texto.configure(state="normal")
        for e in bitacora["ultimos"][-nuevos:]:
            robot = f" {e['robot']}" if e["robot"] else ""
            self._texto.insert("end", f"{e['hora'][:5]}{robot} {e['nombre'].upper()}\n", e["tipo"])
            self._texto.insert("end", f"  {e['mensaje']}\n")
        self._texto.configure(state="disabled")
        self._texto.see("end")
        self._mostrados = bitacora["total"]

    def _exportar(self) -> None:
        ruta = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="reporte_flota.txt",
                                            filetypes=[("Texto", "*.txt")])
        if not ruta:
            return
        try:
            with open(ruta, "w", encoding="utf-8") as archivo:
                archivo.write(self._centro.exportar_bitacora())
        except OSError as error:  # carpeta sin permiso, archivo abierto en otro programa...
            messagebox.showerror("Exportar bitácora", f"No se pudo guardar el reporte:
{error}")
