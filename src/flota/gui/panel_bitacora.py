"""Bitácora en pantalla: eventos coloreados por tipo y exportación del reporte."""
from tkinter import filedialog

import customtkinter as ctk

COLOR_TIPO = {"ENTREGA_EXITOSA": "#2e8b57", "ENTREGA_FALLIDA": "#c0392b", "RECHAZO_CLIMA": "#e67e22",
              "SOLICITUD_PENDIENTE": "#e6b800", "MANTENIMIENTO": "#5dade2",
              "DESPACHO_RECHAZADO": "#c0392b"}


class PanelBitacora(ctk.CTkFrame):

    def __init__(self, master, centro):
        super().__init__(master)
        self._centro = centro
        self._mostrados = 0
        cabecera = ctk.CTkFrame(self, fg_color="transparent")
        cabecera.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(cabecera, text="BITÁCORA", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(cabecera, text="Exportar reporte", width=130,
                      command=self._exportar).pack(side="right")
        self._texto = ctk.CTkTextbox(self, height=130, state="disabled")
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
            robot = f" [{e['robot']}]" if e["robot"] else ""
            self._texto.insert("end", f"{e['hora']} {e['nombre'].upper()}{robot}: {e['mensaje']}\n", e["tipo"])
        self._texto.configure(state="disabled")
        self._texto.see("end")
        self._mostrados = bitacora["total"]

    def _exportar(self) -> None:
        ruta = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="reporte_flota.txt",
                                            filetypes=[("Texto", "*.txt")])
        if ruta:
            with open(ruta, "w", encoding="utf-8") as archivo:
                archivo.write(self._centro.exportar_bitacora())
