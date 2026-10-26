// Mapa 2D del campus en un <canvas>: vista cenital, zoom y arrastre limitados al campus.
// Es el respaldo de la vista 3D: solo usa Canvas 2D, que funciona en cualquier navegador.
import { NEBLINA, difuminarBordes, dibujarEncima, dibujarLuces, puntoEnPoligono } from "./clima.js";

// Los colores salen de gui/tema.py (llegan con la geometría): las dos interfaces usan los mismos
export const PALETA = { dia: {}, noche: {} }, RESALTADO = {}, FRANJA = {};
export const CALLES = new Set(["residential", "tertiary", "unclassified", "living_street"]);

export function cargarTema(tema) {  // antes de crear el mapa
  Object.assign(PALETA.dia, tema.dia); Object.assign(PALETA.noche, tema.noche);
  Object.assign(RESALTADO, tema.resaltado); Object.assign(FRANJA, tema.franja); Object.assign(NEBLINA, tema.neblina);
}
const ZOOM_MIN = 1, ZOOM_MAX = 4, RADIO_CLIC = 18, ESPERA_ANILLO_S = 90;

export class Mapa2D {
  constructor(lienzo, geo, avisos) {
    this.lienzo = lienzo;
    this.ctx = lienzo.getContext("2d");
    this.geo = geo;
    this.avisos = avisos;  // { baliza(id), robot(id) }
    const xs = geo.perimetro.map(p => p[0]), ys = geo.perimetro.map(p => p[1]);
    this.tamano = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys));
    this.centro = [(Math.max(...xs) + Math.min(...xs)) / 2, (Math.max(...ys) + Math.min(...ys)) / 2];
    this.zoom = 1;
    this.retratos = {};
    this.enPantalla = { balizas: [], robots: [] };
    this.paleta = PALETA.dia;
    this.resaltados = "";
    this.fondo = document.createElement("canvas");
    this.foto = null;  // en las vistas realistas: { imagen, caja }
    this._escuchar();
    new ResizeObserver(() => this._redimensionar()).observe(lienzo);
  }

  get escala() { return this.zoom * Math.min(this.ancho, this.alto) / this.tamano; }

  proyectar(x, y) {
    return [this.ancho / 2 + (x - this.centro[0]) * this.escala, this.alto / 2 - (y - this.centro[1]) * this.escala];
  }

  usarVista(vista, mosaico) {
    if (vista === "despacho") { this.foto = null; return this._dibujarFondo(); }
    const imagen = new Image();
    imagen.onload = () => { this.foto = { imagen: difuminarBordes(imagen), caja: mosaico.caja, vista }; this._dibujarFondo(); };
    imagen.src = mosaico.imagen;
  }

  acercar(factor) {
    this.zoom = Math.min(Math.max(this.zoom * factor, ZOOM_MIN), ZOOM_MAX);
    this._dibujarFondo();
  }

  _mover(dx, dy) {
    const [xMin, yMin, xMax, yMax] = this.geo.limites;
    this.centro = [Math.min(Math.max(this.centro[0] - dx / this.escala, xMin), xMax),
                   Math.min(Math.max(this.centro[1] + dy / this.escala, yMin), yMax)];
    this._dibujarFondo();
  }

  _escuchar() {
    let arrastre = null;
    this.lienzo.addEventListener("pointerdown", e => { arrastre = { x0: e.offsetX, y0: e.offsetY, x: e.offsetX, y: e.offsetY }; });
    this.lienzo.addEventListener("pointermove", e => {
      if (!arrastre) return this._sobre(e.offsetX, e.offsetY);
      this._mover(e.offsetX - arrastre.x, e.offsetY - arrastre.y);
      arrastre.x = e.offsetX; arrastre.y = e.offsetY;
    });
    this.lienzo.addEventListener("pointerup", e => {
      if (arrastre && Math.hypot(e.offsetX - arrastre.x0, e.offsetY - arrastre.y0) < 5) this._clic(e.offsetX, e.offsetY);
      arrastre = null;
    });
    this.lienzo.addEventListener("wheel", e => { e.preventDefault(); this.acercar(e.deltaY < 0 ? 1.2 : 1 / 1.2); });
  }

  _sobre(sx, sy) {  // nombre del edificio bajo el cursor (del más cercano a la cámara al más lejano)
    const x = this.centro[0] + (sx - this.ancho / 2) / this.escala, y = this.centro[1] - (sy - this.alto / 2) / this.escala;
    const e = [...this.geo.edificios].reverse().find(e => puntoEnPoligono(x, y, e.contorno));
    this.avisos.sobre(e ? e.nombre : null, sx, sy);
  }

  _clic(sx, sy) {
    for (const tipo of ["balizas", "robots"]) {
      const cerca = this.enPantalla[tipo].map(([id, x, y]) => [Math.hypot(sx - x, sy - y), id]).sort((a, b) => a[0] - b[0]);
      if (cerca.length && cerca[0][0] <= RADIO_CLIC) return this.avisos[tipo === "balizas" ? "baliza" : "robot"](cerca[0][1]);
    }
  }

  _redimensionar() {
    const r = window.devicePixelRatio || 1;
    this.ancho = this.lienzo.clientWidth; this.alto = this.lienzo.clientHeight;
    for (const c of [this.lienzo, this.fondo]) { c.width = this.ancho * r; c.height = this.alto * r; c.getContext("2d").setTransform(r, 0, 0, r, 0, 0); }
    this._dibujarFondo();
  }

  // Suelo, caminos y edificios: se dibujan aparte y solo cuando cambia algo
  _dibujarFondo() {
    if (!this.ancho) return;
    const c = this.fondo.getContext("2d"), p = this.paleta;
    const camino = puntos => { c.beginPath(); puntos.forEach(([x, y], i) => c[i ? "lineTo" : "moveTo"](...this.proyectar(x, y))); };
    c.fillStyle = p.fondo_mapa; c.fillRect(0, 0, this.ancho, this.alto);
    if (this.foto) return this._dibujarFoto(c);
    camino(this.geo.perimetro); c.closePath(); c.fillStyle = p.campus; c.fill(); c.strokeStyle = p.sendero; c.lineWidth = 2; c.stroke();
    c.lineCap = "round";
    for (const v of this.geo.caminos) {
      const calle = CALLES.has(v.tipo);
      camino(v.puntos); c.strokeStyle = calle ? p.calle : p.sendero; c.lineWidth = Math.max(1, this.escala * (calle ? 6 : 1.6)); c.stroke();
    }
    const resaltados = new Set(this.resaltados.split(",").filter(Boolean).map(Number));
    this.geo.edificios.forEach((e, i) => {
      camino(e.contorno); c.closePath();
      const naranja = resaltados.has(i);
      c.fillStyle = naranja ? RESALTADO.edificio : e.en_campus ? p.edificio : p.ciudad; c.fill();
      c.strokeStyle = naranja ? RESALTADO.arista : e.en_campus ? p.arista : p.arista_ciudad;
      c.lineWidth = e.en_campus ? 1.5 : 1; c.stroke();
    });
  }

  _dibujarFoto(c) {  // la imagen real y solo el contorno naranja de los edificios con una llamada
    const [x0, y0, x1, y1] = this.foto.caja, [sx, sy] = this.proyectar(x0, y1);
    c.fillStyle = NEBLINA[this.foto.vista][this.paleta === PALETA.noche ? 1 : 0]; c.fillRect(0, 0, this.ancho, this.alto);
    c.drawImage(this.foto.imagen, sx, sy, (x1 - x0) * this.escala, (y1 - y0) * this.escala);
    if (this.paleta === PALETA.noche) { c.fillStyle = "rgba(5, 12, 28, .6)"; c.fillRect(0, 0, this.ancho, this.alto); }
    c.strokeStyle = RESALTADO.edificio; c.lineWidth = 3;
    for (const i of this.resaltados.split(",").filter(Boolean).map(Number)) {
      c.beginPath();
      this.geo.edificios[i].contorno.forEach(([x, y], k) => c[k ? "lineTo" : "moveTo"](...this.proyectar(x, y)));
      c.closePath(); c.stroke();
    }
  }

  dibujar(estado) {
    const paleta = estado.clima.es_de_dia === false ? PALETA.noche : PALETA.dia;
    const resaltados = estado.balizas.map(b => b.edificio).filter(i => i !== null).sort().join(",");
    if (paleta !== this.paleta || resaltados !== this.resaltados) {
      this.paleta = paleta; this.resaltados = resaltados; this._dibujarFondo();
    }
    const c = this.ctx;
    c.clearRect(0, 0, this.ancho, this.alto);
    c.drawImage(this.fondo, 0, 0, this.ancho, this.alto);
    for (const r of estado.robots) {
      if (r.recorrido.length < 2) continue;
      c.beginPath(); r.recorrido.forEach(([x, y], i) => c[i ? "lineTo" : "moveTo"](...this.proyectar(x, y)));
      c.setLineDash([6, 4]); c.strokeStyle = FRANJA[r.franja]; c.lineWidth = 3; c.stroke(); c.setLineDash([]);
    }
    dibujarLuces(c, estado.ambiente, this.geo, (x, y) => this.proyectar(x, y));
    this.enPantalla = { balizas: [], robots: [] };
    for (const b of estado.balizas) {
      const [x, y] = this.proyectar(b.x, b.y);
      dibujarBaliza(c, x, y, Math.max(0, 1 - b.espera_s / ESPERA_ANILLO_S));
      this.enPantalla.balizas.push([b.id, x, y]);
    }
    for (const r of estado.robots) {
      const [x, y] = this.proyectar(r.x, r.y);
      dibujarRobot(c, x, y, r, this.retratos[r.id]);
      this.enPantalla.robots.push([r.id, x, y]);
    }
    dibujarEncima(c, this.ancho, this.alto, estado.ambiente, this.geo, (x, y) => this.proyectar(x, y), this.escala,
                  performance.now() / 1000, true);
  }
}

export function dibujarBaliza(c, x, y, queda) {
  c.fillStyle = "#132326"; c.beginPath(); c.arc(x, y, 15, 0, 2 * Math.PI); c.fill();
  if (queda > 0) { c.strokeStyle = "#f3efe4"; c.lineWidth = 3; c.beginPath(); c.arc(x, y, 15, -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * queda); c.stroke(); }
  c.fillStyle = "#f08a2c"; c.beginPath(); c.arc(x, y, 11, 0, 2 * Math.PI); c.fill();
  c.fillStyle = "#fff"; c.font = "16px Oswald-SemiBold"; c.textAlign = "center"; c.textBaseline = "middle"; c.fillText("!", x, y + 1);
}

export function dibujarRobot(c, x, y, r, imagen) {
  const color = FRANJA[r.franja];
  c.fillStyle = "#2f5a58"; c.strokeStyle = color; c.lineWidth = 3;
  c.beginPath(); c.arc(x, y, 15, 0, 2 * Math.PI); c.fill(); c.stroke();
  if (imagen && imagen.complete) {
    c.save(); c.beginPath(); c.arc(x, y, 12, 0, 2 * Math.PI); c.clip(); c.drawImage(imagen, x - 12, y - 12, 24, 24); c.restore();
  }
  c.fillStyle = "#f3efe4"; c.font = "12px Oswald-SemiBold"; c.textAlign = "center"; c.textBaseline = "top"; c.fillText(r.id, x, y + 18);
}
