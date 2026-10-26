// Campus en 3D con three.js: edificios extruidos con aristas claras (vista DESPACHO) o, en las vistas
// CALLES y SATÉLITE, con la imagen real en el suelo y en los techos, luz y sombras.
// La misma cámara pasa de vista cenital (2D) a oblicua (3D) con una transición. Robots, rutas y
// balizas se dibujan encima en un canvas 2D, con las mismas funciones que el mapa de respaldo.
import * as THREE from "three";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { CALLES, PALETA, RESALTADO, FRANJA, dibujarBaliza, dibujarRobot } from "./mapa2d.js";
import { ALTURA_NUBES_M, NEBLINA, difuminarBordes, dibujarEncima, dibujarLuces, posicionNube, spriteNube } from "./clima.js";

const POLAR_3D = 0.95, POLAR_2D = 0.0001;  // ángulo desde la vertical
const ZOOM_MIN = 1, ZOOM_MAX = 4, RADIO_CLIC = 18, ESPERA_ANILLO_S = 90, TRANSICION_MS = 600;
const ZOOM_MIN_REAL = 1.6, PANEO_REAL = 0.6;  // en las vistas realistas: no alejarse ni salirse del mosaico

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
    this.renderer.shadowMap.enabled = true;
    this.vista = "despacho";

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
    this.nubes = geo.nubes.map(n => {  // nubes de verdad: planos semitransparentes a 70 m de altura
      const material = new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(spriteNube(n.semilla)),
                                                     transparent: true, depthWrite: false, opacity: 0 });
      const plano = new THREE.Mesh(new THREE.PlaneGeometry(2 * n.radio, 2 * n.radio), material);
      plano.rotation.x = -Math.PI / 2;
      this.escena.add(plano);
      return plano;
    });
    this.rayo = new THREE.Raycaster();
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
    this.estiloDespacho = [suelo];  // lo que se oculta en las vistas realistas
    for (const camino of this.geo.caminos) {
      const linea = new THREE.Line(new THREE.BufferGeometry().setFromPoints(camino.puntos.map(([x, y]) => a3(x, y, 0.1))),
                                   CALLES.has(camino.tipo) ? m.calle : m.sendero);
      this.escena.add(linea);
      this.estiloDespacho.push(linea);
    }
    this.edificios = this.geo.edificios.map(e => {
      const volumen = new THREE.ExtrudeGeometry(forma(e.contorno), { depth: e.altura, bevelEnabled: false });
      volumen.rotateX(-Math.PI / 2);  // la extrusión (z) pasa a ser la altura (y) y el norte queda en -z
      const cuerpo = new THREE.Mesh(volumen, e.en_campus ? [m.techo, m.pared] : [m.techoCiudad, m.paredCiudad]);
      cuerpo.castShadow = cuerpo.receiveShadow = true;
      const aristas = new THREE.LineSegments(new THREE.EdgesGeometry(volumen, 25), e.en_campus ? m.arista : m.aristaCiudad);
      this.escena.add(cuerpo, aristas);
      this.estiloDespacho.push(aristas);
      return { cuerpo, aristas, en_campus: e.en_campus };
    });
    // luz para las vistas realistas (los materiales de DESPACHO no la usan)
    this.luzCielo = new THREE.HemisphereLight(0xffffff, 0x45503f, 1.1);
    this.sol = new THREE.DirectionalLight(0xffffff, 1.7);
    this.sol.position.set(-250, 400, 150);
    this.sol.castShadow = true;
    Object.assign(this.sol.shadow.camera, { left: -700, right: 700, top: 700, bottom: -700, near: 10, far: 1500 });
    this.sol.shadow.mapSize.set(2048, 2048);
    this.escena.add(this.luzCielo, this.sol, this.sol.target);
  }

  // --- Vistas realistas -------------------------------------------------------------------
  usarVista(vista, mosaico) {
    this.vista = vista;
    if (this.sueloReal) { this.escena.remove(this.sueloReal); this.sueloReal = null; }
    if (vista !== "despacho") {
      let techo;
      const [x0, y0, x1, y1] = mosaico.caja, ancho = x1 - x0, alto = y1 - y0;
      const suelo = new THREE.Texture(), foto = new THREE.Texture(), imagen = new Image();
      imagen.onload = () => {  // el suelo lleva los bordes difuminados; los techos, la foto tal cual
        suelo.image = difuminarBordes(imagen); foto.image = imagen;
        suelo.needsUpdate = foto.needsUpdate = techo.needsUpdate = true;
      };
      imagen.src = mosaico.imagen;
      for (const t of [suelo, foto]) {
        t.colorSpace = THREE.SRGBColorSpace;
        t.anisotropy = this.renderer.capabilities.getMaxAnisotropy();
      }
      this.sueloReal = new THREE.Mesh(new THREE.PlaneGeometry(ancho, alto),
                                      new THREE.MeshStandardMaterial({ map: suelo, transparent: true, depthWrite: false }));
      this.sueloReal.rotation.x = -Math.PI / 2;
      this.sueloReal.position.copy(a3(x0 + ancho / 2, y0 + alto / 2, -0.3));
      this.sueloReal.receiveShadow = true;
      this.escena.add(this.sueloReal);
      // los techos usan la misma foto: las tapas de ExtrudeGeometry traen sus coordenadas en metros
      techo = foto.clone();
      techo.repeat.set(1 / ancho, 1 / alto);
      techo.offset.set(-x0 / ancho, -y0 / alto);
      this.materialesReales = {
        techo: vista === "satelite" ? new THREE.MeshStandardMaterial({ map: techo }) : new THREE.MeshStandardMaterial({ color: "#ece9e4" }),
        pared: new THREE.MeshStandardMaterial({ color: vista === "satelite" ? "#b9b2a6" : "#d3cdc4" }),
        techoNaranja: new THREE.MeshStandardMaterial({ color: RESALTADO.edificio }),
        paredNaranja: new THREE.MeshStandardMaterial({ color: RESALTADO.pared }),
      };
    }
    this.estiloDespacho.forEach(objeto => { objeto.visible = vista === "despacho"; });
    if (vista === "despacho") {
      this.limitesPaneo = this.geo.limites;
      this.controles.minZoom = ZOOM_MIN;
    } else {
      const [x0, y0, x1, y1] = mosaico.caja, mx = (x1 - x0) * (1 - PANEO_REAL) / 2, my = (y1 - y0) * (1 - PANEO_REAL) / 2;
      this.limitesPaneo = [x0 + mx, y0 + my, x1 - mx, y1 - my];
      this.controles.minZoom = ZOOM_MIN_REAL;
      if (this.camara.zoom < ZOOM_MIN_REAL) { this.camara.zoom = ZOOM_MIN_REAL; this.camara.updateProjectionMatrix(); }
    }
    this._limitar();
    this._aplicarPaleta(this._paleta);
    this._aplicarResaltados(new Set(this._resaltados.split(",").filter(Boolean).map(Number)));
  }

  _aplicarPaleta(p) {
    const m = this.materiales, noche = p === PALETA.noche;
    this.escena.background = new THREE.Color(this.vista === "despacho" ? p.fondo_mapa : NEBLINA[this.vista][noche ? 1 : 0]);
    this.luzCielo.intensity = noche ? 0.25 : 1.1;  // de noche la foto se oscurece y se ven las luces
    this.sol.intensity = noche ? 0.15 : 1.7;
    m.campus.color.set(p.campus); m.techo.color.set(p.edificio); m.pared.color.set(p.pared);
    m.techoCiudad.color.set(p.ciudad); m.paredCiudad.color.set(p.pared_ciudad);
    m.arista.color.set(p.arista); m.aristaCiudad.color.set(p.arista_ciudad);
    m.sendero.color.set(p.sendero); m.calle.color.set(p.calle);
  }

  _aplicarResaltados(indices) {
    const m = this.materiales;
    this.edificios.forEach((e, i) => {
      const naranja = indices.has(i);
      if (this.vista !== "despacho") {
        const r = this.materialesReales;
        e.cuerpo.material = naranja ? [r.techoNaranja, r.paredNaranja] : [r.techo, r.pared];
        return;
      }
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
    this.camara.zoom = Math.min(Math.max(this.camara.zoom * factor, this.controles.minZoom), ZOOM_MAX);
    this.camara.updateProjectionMatrix();
  }

  _limitar() {  // el mapa no se sale del área descargada (en las vistas realistas, del centro del mosaico)
    const [xMin, yMin, xMax, yMax] = this.limitesPaneo || this.geo.limites, t = this.controles.target;
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
    this.lienzo.addEventListener("pointermove", e => {  // nombre del edificio bajo el cursor
      if (e.buttons) return this.avisos.sobre(null);
      const puntero = new THREE.Vector2(e.offsetX / this.lienzo.clientWidth * 2 - 1, -e.offsetY / this.lienzo.clientHeight * 2 + 1);
      this.rayo.setFromCamera(puntero, this.camara);
      const [golpe] = this.rayo.intersectObjects(this.edificios.map(ed => ed.cuerpo), false);
      const i = golpe ? this.edificios.findIndex(ed => ed.cuerpo === golpe.object) : -1;
      this.avisos.sobre(i >= 0 ? this.geo.edificios[i].nombre : null, e.offsetX, e.offsetY);
    });
    this.lienzo.addEventListener("pointerleave", () => this.avisos.sobre(null));
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
    if (this.estado) this._moverNubes(this.estado.ambiente, performance.now() / 1000);
    this.renderer.render(this.escena, this.camara);
    if (this.estado) this._dibujarVivo(this.estado);
  }

  _moverNubes(ambiente, t) {
    const visibles = Math.round(this.nubes.length * ambiente.nubes);
    this.nubes.forEach((plano, i) => {
      const [x, y] = posicionNube(this.geo.nubes[i], ambiente.viento, t, this.geo.limites);
      plano.position.copy(a3(x, y, ALTURA_NUBES_M));
      plano.material.opacity = i < visibles ? ambiente.nubes * 0.6 : 0;
    });
  }

  _dibujarVivo(estado) {
    const c = this.superposicion.getContext("2d"), tresD = this.modo === "3D";
    c.clearRect(0, 0, this.lienzo.clientWidth, this.lienzo.clientHeight);
    for (const r of estado.robots) {
      if (r.recorrido.length < 2) continue;
      c.beginPath(); r.recorrido.forEach(([x, y], i) => c[i ? "lineTo" : "moveTo"](...this._aPantalla(x, y)));
      c.setLineDash([6, 4]); c.strokeStyle = FRANJA[r.franja]; c.lineWidth = 3; c.stroke(); c.setLineDash([]);
    }
    dibujarLuces(c, estado.ambiente, this.geo, (x, y, z) => this._aPantalla(x, y, z));
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
    dibujarEncima(c, this.lienzo.clientWidth, this.lienzo.clientHeight, estado.ambiente, this.geo,
                  (x, y, z) => this._aPantalla(x, y, z), 1, performance.now() / 1000, false);
  }
}
