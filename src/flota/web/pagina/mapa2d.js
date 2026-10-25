// Mapa 2D del campus en un <canvas>: vista cenital, zoom y arrastre limitados al campus.
// Es el respaldo de la vista 3D: solo usa Canvas 2D, que funciona en cualquier navegador.

export const PALETA = {
  dia: { fondo: "#1d7f7b", campus: "#23918b", edificio: "#2bb3a3", pared: "#1f8f84", arista: "#b9fff2",
         sendero: "#5fd3c3", calle: "#176a66", ciudad: "#227f78", paredCiudad: "#1b6f69", aristaCiudad: "#6fd6c8" },
  noche: { fondo: "#0c1a1c", campus: "#0f2225", edificio: "#10302c", pared: "#0b2420", arista: "#46f0b4",
           sendero: "#1f5a4c", calle: "#14302e", ciudad: "#0f2624", paredCiudad: "#0b1d1c", aristaCiudad: "#1f6a58" },
};
export const RESALTADO = { edificio: "#f08a2c", pared: "#c46a1c", arista: "#ffd2a1" };
export const FRANJA = { libre: "#3f9a6b", ocupado: "#1f6fd1", falla: "#d2453b" };
const CALLES = new Set(["residential", "tertiary", "unclassified", "living_street"]);
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
    this._escuchar();
    new ResizeObserver(() => this._redimensionar()).observe(lienzo);
  }

  get escala() { return this.zoom * Math.min(this.ancho, this.alto) / this.tamano; }

  proyectar(x, y) {
    return [this.ancho / 2 + (x - this.centro[0]) * this.escala, this.alto / 2 - (y - this.centro[1]) * this.escala];
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
      if (!arrastre) return;
      this._mover(e.offsetX - arrastre.x, e.offsetY - arrastre.y);
      arrastre.x = e.offsetX; arrastre.y = e.offsetY;
    });
    this.lienzo.addEventListener("pointerup", e => {
      if (arrastre && Math.hypot(e.offsetX - arrastre.x0, e.offsetY - arrastre.y0) < 5) this._clic(e.offsetX, e.offsetY);
      arrastre = null;
    });
    this.lienzo.addEventListener("wheel", e => { e.preventDefault(); this.acercar(e.deltaY < 0 ? 1.2 : 1 / 1.2); });
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
    c.fillStyle = p.fondo; c.fillRect(0, 0, this.ancho, this.alto);
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
      c.strokeStyle = naranja ? RESALTADO.arista : e.en_campus ? p.arista : p.aristaCiudad;
      c.lineWidth = e.en_campus ? 1.5 : 1; c.stroke();
    });
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
    dibujarNubes(c, this.ancho, this.alto, estado.clima, performance.now() / 1000);
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

// Sombras de nubes que cruzan el mapa con el viento; más densas cuanto más llueve
const NUBES = Array.from({ length: 7 }, (_, i) => ({ x: (i * 0.37) % 1, y: (i * 0.61) % 1, r: 0.12 + (i % 3) * 0.05 }));

export function dibujarNubes(c, ancho, alto, clima, segundos) {
  if (!clima || clima.consultando || !clima.disponible || (clima.lluvia < 40 && !clima.tormenta)) return;
  const densidad = Math.min(1, (clima.tormenta ? 100 : clima.lluvia) / 100);
  const rumbo = ((clima.direccion ?? 270) + 180) * Math.PI / 180;  // el viento viene de "direccion": las nubes van al otro lado
  const avance = segundos * (2 + clima.viento / 4) / 1000;
  NUBES.slice(0, Math.ceil(densidad * NUBES.length)).forEach(n => {
    const x = (((n.x + Math.sin(rumbo) * avance) % 1) + 1) % 1 * (ancho + 400) - 200;
    const y = (((n.y - Math.cos(rumbo) * avance) % 1) + 1) % 1 * (alto + 400) - 200;
    const radio = n.r * Math.max(ancho, alto);
    const g = c.createRadialGradient(x, y, 0, x, y, radio);
    g.addColorStop(0, `rgba(10, 30, 32, ${0.35 * densidad})`);
    g.addColorStop(1, "rgba(10, 30, 32, 0)");
    c.fillStyle = g;
    c.fillRect(x - radio, y - radio, 2 * radio, 2 * radio);
  });
}
