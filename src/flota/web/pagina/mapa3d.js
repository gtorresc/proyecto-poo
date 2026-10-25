// Campus en 3D con three.js: edificios extruidos con aristas claras.
// La misma cámara pasa de vista cenital (2D) a oblicua (3D) con una transición. Robots, rutas y
// balizas se dibujan encima en un canvas 2D, con las mismas funciones que el mapa de respaldo.
import * as THREE from "three";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { PALETA, RESALTADO, FRANJA, dibujarBaliza, dibujarNubes, dibujarRobot } from "./mapa2d.js";

const CALLES = new Set(["residential", "tertiary", "unclassified", "living_street"]);
const POLAR_3D = 0.95, POLAR_2D = 0.0001;  // ángulo desde la vertical
const ZOOM_MIN = 1, ZOOM_MAX = 4, RADIO_CLIC = 18, ESPERA_ANILLO_S = 90, TRANSICION_MS = 600;

// el norte (y) del campus es -z en three.js; la altura es y
const a3 = (x, y, z = 0) => new THREE.Vector3(x, z, -y);

export class Mapa3D {
  constructor(lienzo, geo, avisos) {
    this.lienzo = lienzo;
    this.geo = geo;
    this.avisos = avisos;
    this.retratos = {};
    this.enPantalla = { balizas: [], robots: [] };
    this.estado = null;
    this.modo = "3D";
    this.renderer = new THREE.WebGLRenderer({ canvas: lienzo, antialias: true });  // sin WebGL lanza un error
    this.renderer.setPixelRatio(window.devicePixelRatio || 1);

    const xs = geo.perimetro.map(p => p[0]), ys = geo.perimetro.map(p => p[1]);
    this.tamano = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys));
    const centro = a3((Math.max(...xs) + Math.min(...xs)) / 2, (Math.max(...ys) + Math.min(...ys)) / 2);

    this.escena = new THREE.Scene();
    this.camara = new THREE.OrthographicCamera(-1, 1, 1, -1, 1, 5000);
    this.camara.position.copy(centro).add(new THREE.Vector3(0, 1000, 0));
    this.camara.zoom = 1.5;  // empieza cerca del campus; con zoom 1 se ve también el barrio
    this.controles = new OrbitControls(this.camara, lienzo);
    this.controles.target.copy(centro);
    Object.assign(this.controles, { minZoom: ZOOM_MIN, maxZoom: ZOOM_MAX, maxPolarAngle: 1.2, enableDamping: true,
                                    screenSpacePanning: false, zoomToCursor: true });
    this.controles.mouseButtons = { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE };
    this.controles.addEventListener("change", () => this._limitar());
    this._ponerAngulos(POLAR_3D, 0);

    this.materiales = this._crearMateriales();
    this._construirCampus();
    this.superposicion = this._crearSuperposicion();
    this._escucharClics();
    new ResizeObserver(() => this._redimensionar()).observe(lienzo);
    this._paleta = PALETA.dia;
    this._aplicarPaleta(this._paleta);
    this._resaltados = "";
    this._redimensionar();
    this._animar();
  }

  _crearMateriales() {
    const lado = { side: THREE.DoubleSide };
    return {
      campus: new THREE.MeshBasicMaterial(lado), techo: new THREE.MeshBasicMaterial(lado), pared: new THREE.MeshBasicMaterial(lado),
      techoCiudad: new THREE.MeshBasicMaterial(lado), paredCiudad: new THREE.MeshBasicMaterial(lado),
      techoNaranja: new THREE.MeshBasicMaterial({ ...lado, color: RESALTADO.edificio }),
      paredNaranja: new THREE.MeshBasicMaterial({ ...lado, color: RESALTADO.pared }),
      arista: new THREE.LineBasicMaterial(), aristaCiudad: new THREE.LineBasicMaterial(),
      aristaNaranja: new THREE.LineBasicMaterial({ color: RESALTADO.arista }),
      sendero: new THREE.LineBasicMaterial(), calle: new THREE.LineBasicMaterial(),
    };
  }

  _construirCampus() {
    const m = this.materiales;
    const forma = puntos => new THREE.Shape(puntos.map(([x, y]) => new THREE.Vector2(x, y)));
    const suelo = new THREE.Mesh(new THREE.ShapeGeometry(forma(this.geo.perimetro)), m.campus);
    suelo.rotation.x = -Math.PI / 2;
    suelo.position.y = -0.2;
    this.escena.add(suelo);
    for (const camino of this.geo.caminos) {
      const linea = new THREE.Line(new THREE.BufferGeometry().setFromPoints(camino.puntos.map(([x, y]) => a3(x, y, 0.1))),
                                   CALLES.has(camino.tipo) ? m.calle : m.sendero);
      this.escena.add(linea);
    }
    this.edificios = this.geo.edificios.map(e => {
      const volumen = new THREE.ExtrudeGeometry(forma(e.contorno), { depth: e.altura, bevelEnabled: false });
      volumen.rotateX(-Math.PI / 2);  // la extrusión (z) pasa a ser la altura (y) y el norte queda en -z
      const cuerpo = new THREE.Mesh(volumen, e.en_campus ? [m.techo, m.pared] : [m.techoCiudad, m.paredCiudad]);
      const aristas = new THREE.LineSegments(new THREE.EdgesGeometry(volumen, 25), e.en_campus ? m.arista : m.aristaCiudad);
      this.escena.add(cuerpo, aristas);
      return { cuerpo, aristas, en_campus: e.en_campus };
    });
  }

  _aplicarPaleta(p) {
    const m = this.materiales;
    this.escena.background = new THREE.Color(p.fondo);
    m.campus.color.set(p.campus); m.techo.color.set(p.edificio); m.pared.color.set(p.pared);
    m.techoCiudad.color.set(p.ciudad); m.paredCiudad.color.set(p.paredCiudad);
    m.arista.color.set(p.arista); m.aristaCiudad.color.set(p.aristaCiudad);
    m.sendero.color.set(p.sendero); m.calle.color.set(p.calle);
  }

  _aplicarResaltados(indices) {
    const m = this.materiales;
    this.edificios.forEach((e, i) => {
      const naranja = indices.has(i);
      e.cuerpo.material = naranja ? [m.techoNaranja, m.paredNaranja] : e.en_campus ? [m.techo, m.pared] : [m.techoCiudad, m.paredCiudad];
      e.aristas.material = naranja ? m.aristaNaranja : e.en_campus ? m.arista : m.aristaCiudad;
    });
  }

  // --- Cámara -------------------------------------------------------------------------
  _ponerAngulos(polar, azimut) {
    const distancia = 1000, t = this.controles.target;
    this.camara.position.set(t.x + distancia * Math.sin(polar) * Math.sin(azimut), t.y + distancia * Math.cos(polar),
                             t.z + distancia * Math.sin(polar) * Math.cos(azimut));
    this.camara.lookAt(t);
    this.controles.update();
  }

  _transicion(polarFinal, azimutFinal) {
    const polar0 = this.controles.getPolarAngle(), azimut0 = this.controles.getAzimuthalAngle(), inicio = performance.now();
    const paso = ahora => {
      const t = Math.min(1, (ahora - inicio) / TRANSICION_MS), suave = t * t * (3 - 2 * t);
      this._ponerAngulos(polar0 + (polarFinal - polar0) * suave, azimut0 + (azimutFinal - azimut0) * suave);
      if (t < 1) requestAnimationFrame(paso);
    };
    requestAnimationFrame(paso);
  }

  alternar() {
    this.modo = this.modo === "3D" ? "2D" : "3D";
    this.controles.enableRotate = this.modo === "3D";  // en 2D el mapa no se inclina
    this._transicion(this.modo === "3D" ? POLAR_3D : POLAR_2D, this.controles.getAzimuthalAngle());
  }

  girar() { this._transicion(this.controles.getPolarAngle(), this.controles.getAzimuthalAngle() + Math.PI / 2); }

  acercar(factor) {
    this.camara.zoom = Math.min(Math.max(this.camara.zoom * factor, ZOOM_MIN), ZOOM_MAX);
    this.camara.updateProjectionMatrix();
  }

  _limitar() {  // el mapa no se sale del área descargada
    const [xMin, yMin, xMax, yMax] = this.geo.limites, t = this.controles.target;
    const x = Math.min(Math.max(t.x, xMin), xMax), z = Math.min(Math.max(t.z, -yMax), -yMin);
    if (x !== t.x || z !== t.z) {
      this.camara.position.x += x - t.x; this.camara.position.z += z - t.z;
      t.x = x; t.z = z;
    }
  }

  _redimensionar() {
    const ancho = this.lienzo.clientWidth, alto = this.lienzo.clientHeight;
    if (!ancho) return;
    this.renderer.setSize(ancho, alto, false);
    const mitad = this.tamano / 2, aspecto = ancho / alto;
    Object.assign(this.camara, aspecto > 1 ? { left: -mitad * aspecto, right: mitad * aspecto, top: mitad, bottom: -mitad }
                                           : { left: -mitad, right: mitad, top: mitad / aspecto, bottom: -mitad / aspecto });
    this.camara.updateProjectionMatrix();
    const r = window.devicePixelRatio || 1, s = this.superposicion;
    s.width = ancho * r; s.height = alto * r; s.getContext("2d").setTransform(r, 0, 0, r, 0, 0);
  }

  // --- Capa viva (robots, rutas, balizas) encima del 3D -------------------------------------
  _crearSuperposicion() {
    const s = document.createElement("canvas");
    s.style.cssText = "position:absolute; inset:0; width:100%; height:100%; pointer-events:none;";
    this.lienzo.after(s);
    return s;
  }

  _aPantalla(x, y, z = 0) {
    const v = a3(x, y, z).project(this.camara);
    return [(v.x + 1) / 2 * this.lienzo.clientWidth, (1 - v.y) / 2 * this.lienzo.clientHeight];
  }

  _escucharClics() {
    let inicio = null;
    this.lienzo.addEventListener("pointerdown", e => { inicio = [e.offsetX, e.offsetY]; });
    this.lienzo.addEventListener("pointerup", e => {
      if (!inicio || Math.hypot(e.offsetX - inicio[0], e.offsetY - inicio[1]) >= 5) return;  // fue un arrastre
      for (const tipo of ["balizas", "robots"]) {
        const cerca = this.enPantalla[tipo].map(([id, x, y]) => [Math.hypot(e.offsetX - x, e.offsetY - y), id]).sort((a, b) => a[0] - b[0]);
        if (cerca.length && cerca[0][0] <= RADIO_CLIC) return this.avisos[tipo === "balizas" ? "baliza" : "robot"](cerca[0][1]);
      }
    });
    this.lienzo.addEventListener("contextmenu", e => e.preventDefault());
  }

  dibujar(estado) {  // lo llama app.js con cada estado; el dibujo ocurre en _animar
    this.estado = estado;
    const paleta = estado.clima.es_de_dia === false ? PALETA.noche : PALETA.dia;
    if (paleta !== this._paleta) { this._paleta = paleta; this._aplicarPaleta(paleta); }
    const resaltados = estado.balizas.map(b => b.edificio).filter(i => i !== null).sort().join(",");
    if (resaltados !== this._resaltados) {
      this._resaltados = resaltados;
      this._aplicarResaltados(new Set(resaltados.split(",").filter(Boolean).map(Number)));
    }
  }

  _animar() {
    requestAnimationFrame(() => this._animar());
    this.controles.update();
    this.renderer.render(this.escena, this.camara);
    if (this.estado) this._dibujarVivo(this.estado);
  }

  _dibujarVivo(estado) {
    const c = this.superposicion.getContext("2d"), tresD = this.modo === "3D";
    c.clearRect(0, 0, this.lienzo.clientWidth, this.lienzo.clientHeight);
    for (const r of estado.robots) {
      if (r.recorrido.length < 2) continue;
      c.beginPath(); r.recorrido.forEach(([x, y], i) => c[i ? "lineTo" : "moveTo"](...this._aPantalla(x, y)));
      c.setLineDash([6, 4]); c.strokeStyle = FRANJA[r.franja]; c.lineWidth = 3; c.stroke(); c.setLineDash([]);
    }
    this.enPantalla = { balizas: [], robots: [] };
    for (const b of estado.balizas) {
      const alto = b.edificio !== null ? this.geo.edificios[b.edificio].altura : 0;
      const [x, y] = this._aPantalla(b.x, b.y, alto + 4);
      dibujarBaliza(c, x, y, Math.max(0, 1 - b.espera_s / ESPERA_ANILLO_S));
      this.enPantalla.balizas.push([b.id, x, y]);
    }
    for (const r of estado.robots) {
      if (r.z && tresD) {  // sombra en el suelo: así se nota que el dron vuela
        const [sx, sy] = this._aPantalla(r.x, r.y);
        c.fillStyle = "#0b2a28aa"; c.beginPath(); c.ellipse(sx, sy, 9, 4, 0, 0, 2 * Math.PI); c.fill();
      }
      const [x, y] = this._aPantalla(r.x, r.y, r.z);
      dibujarRobot(c, x, y, r, this.retratos[r.id]);
      this.enPantalla.robots.push([r.id, x, y]);
    }
    dibujarNubes(c, this.lienzo.clientWidth, this.lienzo.clientHeight, estado.clima, performance.now() / 1000);
  }
}
