"""Bitácora en pantalla: eventos coloreados por tipo y exportación del reporte."""
from tkinter import filedialog

import customtkinter as ctk

from flota.dominio.bitacora import TipoEvento

COLOR_TIPO = {TipoEvento.ENTREGA_EXITOSA: "#2e8b57", TipoEvento.ENTREGA_FALLIDA: "#c0392b",
              TipoEvento.RECHAZO_CLIMA: "#e67e22", TipoEvento.SOLICITUD_PENDIENTE: "#e6b800",
              TipoEvento.MANTENIMIENTO: "#5dade2"}


class PanelBitacora(ctk.CTkFrame):

    def __init__(self, master, bitacora):
        super().__init__(master)
        self._bitacora = bitacora
        self._mostrados = 0
        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(cabecera, text="BITÁCORA", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(cabecera, text="Exportar reporte", width=130,
                      command=self._exportar).pack(side="right")
        self._texto = ctk.CTkTextbox(self, height=130, state="disabled")
        self._texto.pack(fill="both", expand=True, padx=10, pady=8)
        for tipo, color in COLOR_TIPO.items():
            self._texto.tag_config(tipo.name, foreground=color)
        self.refrescar()

    def refrescar(self) -> None:
        nuevos = self._bitacora.eventos()[self._mostrados:]
        if not nuevos:
            return
        self._texto.configure(state="normal")
        for evento in nuevos:
            self._texto.insert("end", evento.como_texto() + "\n", evento.tipo.name)
        self._texto.configure(state="disabled")
        self._texto.see("end")
        self._mostrados += len(nuevos)

    def _exportar(self) -> None:
        ruta = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="reporte_flota.txt",
                                            filetypes=[("Texto", "*.txt")])
        if ruta:
            with open(ruta, "w", encoding="utf-8") as archivo:
                archivo.write(self._bitacora.generar_reporte())
