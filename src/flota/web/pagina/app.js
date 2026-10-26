// UdeM·DESPACHO, versión web. Solo presentación: todo lo que hace pasa por window.pywebview.api,
// que es PuenteWeb (Python) sobre CentroControl. Las reglas de negocio no están aquí.
import { Mapa2D, FRANJA, cargarTema } from "./mapa2d.js";

const $ = id => document.getElementById(id);
const ETIQUETA = { libre: "DISPONIBLE", ocupado: "EN RUTA", falla: "MANTENIMIENTO" };
const EJES = [["velocidad", "VEL"], ["carga", "CARGA"], ["autonomia", "AUTON"], ["economia", "ECON"], ["alcance", "ALCANCE"]];
const RUMBOS = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"];
const COLOR_EVENTO = { ENTREGA_EXITOSA: "#46f0b4", ENTREGA_FALLIDA: "#d2453b", RECHAZO_CLIMA: "#f08a2c",
                       SOLICITUD_PENDIENTE: "#f08a2c", MANTENIMIENTO: "#6fb6ff", DESPACHO_RECHAZADO: "#d2453b" };

let api, mapa, ultimo = null;
const VISTAS = ["despacho", "calles", "satelite"], NOMBRE_VISTA = { despacho: "DESPACHO", calles: "CALLES", satelite: "SATÉLITE" };
const mosaicos = {};  // capa -> respuesta del puente (se pide una sola vez)
let vistaActual = "despacho";
const vista = { robotElegido: null, llamada: null, mostrados: 0, inicio: Date.now(), tarjetas: {} };

window.addEventListener("pywebviewready", iniciar);

async function iniciar() {
  api = window.pywebview.api;
  const fuentes = await api.fuentes();
  for (const [nombre, datos] of Object.entries(fuentes)) {
    const bytes = Uint8Array.from(atob(datos), c => c.charCodeAt(0));
    document.fonts.add(await new FontFace(nombre, bytes).load());
  }
  const geo = await api.geometria();
  cargarTema(geo.tema);
  llenarFormulario(geo);
  mapa = await crearMapa(geo);
  conectarControles();
  ciclo();
}

async function crearMapa(geo) {
  const avisos = { baliza: abrirLlamada, robot: elegirRobot, sobre: mostrarNombreEdificio };
  try {
    const { Mapa3D } = await import("./mapa3d.js");
    return new Mapa3D($("lienzo"), geo, avisos);
  } catch (error) {  // sin WebGL (o si three.js no carga) queda el mapa 2D, que funciona en cualquier navegador
    console.warn("Vista 3D no disponible, se usa el mapa 2D:", error);
    document.querySelectorAll("[data-3d]").forEach(b => b.hidden = true);
    return new Mapa2D($("lienzo"), geo, avisos);
  }
}

function mostrarNombreEdificio(nombre, x, y) {
  const etiqueta = $("etiqueta-edificio");
  etiqueta.hidden = !nombre;  // los edificios sin nombre en OpenStreetMap no muestran nada
  if (!nombre) return;
  etiqueta.textContent = nombre;
  const ancho = $("mapa").clientWidth, derecha = x + 14 + etiqueta.offsetWidth > ancho;
  etiqueta.style.left = `${derecha ? x - 14 - etiqueta.offsetWidth : x + 14}px`;
  etiqueta.style.top = `${y - 30}px`;
}

async function cambiarVista() {
  const vista = VISTAS[(VISTAS.indexOf(vistaActual) + 1) % VISTAS.length];
  vistaActual = vista;
  if (vista !== "despacho" && !mosaicos[vista]) {
    avisar("cargando mapa…");
    const respuesta = await api.mosaico(vista);
    if (respuesta.error) {  // sin red: se queda en DESPACHO
      vistaActual = "despacho";
      mapa.usarVista("despacho");
      return avisar(respuesta.error);
    }
    mosaicos[vista] = respuesta;
  }
  if (vistaActual !== vista) return;  // el operador ya pidió otra mientras bajaba
  mapa.usarVista(vista, mosaicos[vista]);
  $("credito-mapa").textContent = vista === "despacho" ? "© OpenStreetMap contributors" : mosaicos[vista].credito;
  avisar(`vista ${NOMBRE_VISTA[vista]}`);
}

let temporizadorAviso;
function avisar(texto) {
  $("aviso-mapa").textContent = texto.toUpperCase();
  $("aviso-mapa").hidden = false;
  clearTimeout(temporizadorAviso);
  temporizadorAviso = setTimeout(() => { $("aviso-mapa").hidden = true; }, 4000);
}

async function ciclo() {
  try {
    ultimo = await api.estado();
    dibujar(ultimo);
  } finally {
    setTimeout(ciclo, 50);
  }
}

function dibujar(estado) {
  mapa.dibujar(estado);
  dibujarPlantilla(estado.robots);
  dibujarClima(estado.clima);
  dibujarRadio(estado.bitacora);
  dibujarBarras(estado);
  if (vista.llamada !== null) {
    const baliza = estado.balizas.find(b => b.id === vista.llamada);
    baliza ? mostrarLlamada(baliza) : cerrarLlamada();  // se asignó sola al reintentar
  }
  if (vista.robotElegido) mostrarRobot(estado.robots.find(r => r.id === vista.robotElegido));
}

// --- Formulario y despacho ------------------------------------------------------------
function llenarFormulario(geo) {
  const opciones = (select, items, valor, texto) =>
    items.forEach(i => select.add(new Option(i[texto], i[valor])));
  opciones($("origen"), geo.ubicaciones, "clave", "nombre");
  opciones($("destino"), geo.ubicaciones, "clave", "nombre");
  opciones($("carga"), geo.tipos_carga, "clave", "nombre");
  $("destino").selectedIndex = 1;
  $("formulario").addEventListener("submit", async e => {
    e.preventDefault();
    const peso = parseFloat($("peso").value.replace(",", "."));
    const r = await api.crear_solicitud($("origen").value, $("destino").value, $("carga").value, isNaN(peso) ? 0 : peso);
    if (r && r.error) return anunciar($("formulario-resultado"), `DATOS INVÁLIDOS: ${r.error}`, false);
    anunciar($("formulario-resultado"), `LLAMADA #${r} EN EL MAPA`, true);
    ultimo = await api.estado();
    abrirLlamada(r);
  });
}

function abrirLlamada(id) {
  const baliza = ultimo && ultimo.balizas.find(b => b.id === id);
  if (!baliza) return;
  vista.llamada = id;
  anunciar($("llamada-resultado"), baliza.motivo, false);
  mostrarLlamada(baliza);
  $("ficha-llamada").hidden = false;
}

function mostrarLlamada(b) {
  $("llamada-titulo").textContent = `LLAMADA #${b.id} · ${b.carga.toUpperCase()}`;
  $("llamada-datos").textContent = `De: ${b.origen}\nA:  ${b.destino}\nPeso: ${b.peso} kg · ` +
    `${b.automatica ? "en reintento automático" : "esperando robot"}\nElige un robot en la plantilla o pulsa AUTO.`;
}

function cerrarLlamada() { vista.llamada = null; $("ficha-llamada").hidden = true; }

async function despacharCon(promesa) {
  const r = await promesa;
  if (r.error) return anunciar($("llamada-resultado"), r.error, false);
  const [ok, motivo] = r;
  ok ? cerrarLlamada() : anunciar($("llamada-resultado"), `RECHAZADO: ${motivo}`, false);
}

function elegirRobot(id) {
  if (vista.llamada !== null) return despacharCon(api.despachar(vista.llamada, id));  // despacho manual
  vista.robotElegido = vista.robotElegido === id ? null : id;
  $("ficha-robot").hidden = !vista.robotElegido;
  if (ultimo) dibujar(ultimo);
}

function anunciar(elemento, texto, ok) {
  elemento.textContent = texto || "";
  elemento.className = "resultado " + (ok ? "bien" : "mal");
}

// --- Plantilla y ficha del robot --------------------------------------------------------
function dibujarPlantilla(robots) {
  for (const r of robots) {
    let t = vista.tarjetas[r.id];
    if (!t) {  // también los robots que se agreguen en vivo
      t = document.createElement("button");
      t.className = "tarjeta";
      t.innerHTML = `<div class="franja"></div><img alt=""><div class="nombre"></div><div class="tipo"></div>` +
                    `<div class="bateria"><div></div></div>`;
      t.querySelector(".nombre").textContent = r.id;
      t.querySelector(".tipo").textContent = r.tipo.toUpperCase();
      t.addEventListener("click", () => elegirRobot(r.id));
      $("plantilla").append(t);
      vista.tarjetas[r.id] = t;
      api.retrato(r.id, r.tipo).then(url => {
        t.querySelector("img").src = url;
        const img = new Image(); img.src = url; mapa.retratos[r.id] = img;
      });
    }
    const franja = t.querySelector(".franja");
    franja.textContent = ETIQUETA[r.franja]; franja.style.background = FRANJA[r.franja];
    const bateria = t.querySelector(".bateria div");
    bateria.style.width = `${r.bateria}%`;
    bateria.style.background = r.bateria > 50 ? FRANJA.libre : r.bateria > 25 ? "#f08a2c" : FRANJA.falla;
    t.classList.toggle("elegida", r.id === vista.robotElegido);
    t.setAttribute("aria-label", `${r.id}, ${r.tipo}, ${ETIQUETA[r.franja]}, batería ${r.bateria.toFixed(0)} %`);
  }
}

function mostrarRobot(r) {
  if (!r) return;
  $("robot-titulo").textContent = `${r.id} · ${r.tipo.toUpperCase()}`;
  $("robot-titulo").style.background = FRANJA[r.franja];
  const m = r.mision;
  $("robot-datos").textContent = `Estado: ${r.estado}\nBatería: ${r.bateria.toFixed(0)} %\n` +
    `${r.es_aereo ? "Vuela" : "Por senderos"}\n\n` +
    (m ? `Destino:\n${m.destino}\nCarga: ${m.carga}\nAvance: ${(m.progreso * 100).toFixed(0)} %` : "Sin misión");
  dibujarRadar($("radar"), r.radar);
}

export function puntosRadar(valores, cx, cy, radio) {
  return EJES.map(([eje], i) => {
    const angulo = -Math.PI / 2 + i * 2 * Math.PI / EJES.length;
    const r = radio * Math.max(0.05, Math.min(1, valores[eje]));
    return [cx + r * Math.cos(angulo), cy + r * Math.sin(angulo)];
  });
}

function dibujarRadar(lienzo, valores) {
  const c = lienzo.getContext("2d"), cx = 95, cy = 92, radio = 62;
  const poligono = puntos => { c.beginPath(); puntos.forEach(([x, y], i) => c[i ? "lineTo" : "moveTo"](x, y)); c.closePath(); };
  c.clearRect(0, 0, lienzo.width, lienzo.height);
  c.strokeStyle = "#b9a98a"; c.lineWidth = 1;
  for (const escala of [1, 0.66, 0.33]) { poligono(puntosRadar(Object.fromEntries(EJES.map(([e]) => [e, escala])), cx, cy, radio)); c.stroke(); }
  c.fillStyle = "#2a2a2a"; c.font = "10px ShareTechMono-Regular"; c.textAlign = "center"; c.textBaseline = "middle";
  puntosRadar(Object.fromEntries(EJES.map(([e]) => [e, 1])), cx, cy, radio + 16).forEach(([x, y], i) => c.fillText(EJES[i][1], x, y));
  poligono(puntosRadar(valores, cx, cy, radio));
  c.fillStyle = "#f5b77a"; c.fill(); c.strokeStyle = "#f08a2c"; c.lineWidth = 2; c.stroke();
}

// --- Clima, radio y barras --------------------------------------------------------------
function dibujarClima(c) {
  const datos = $("clima-datos"), semaforo = $("clima-semaforo");
  if (c.consultando) { datos.textContent = "consultando clima…"; semaforo.textContent = ""; return; }
  if (!c.disponible) datos.textContent = "clima no disponible";
  else datos.textContent = [c.temperatura != null && `${c.temperatura.toFixed(0)}°C`,
    c.humedad != null && `humedad ${c.humedad.toFixed(0)}%`,
    `viento ${c.viento.toFixed(0)} km/h` + (c.direccion != null ? ` ${RUMBOS[Math.round(c.direccion / 45) % 8]} ${c.direccion.toFixed(0)}°` : ""),
    `lluvia ${c.lluvia.toFixed(0)}%`].filter(Boolean).join("  |  ");
  semaforo.textContent = c.drones_autorizados ? "DRONES AUTORIZADOS" : `DRONES EN TIERRA: ${c.motivo}`;
  semaforo.style.color = c.drones_autorizados ? "#46f0b4" : "#f08a2c";
}

function dibujarRadio(bitacora) {
  const nuevos = bitacora.total - vista.mostrados;
  if (nuevos <= 0) return;
  const registro = $("registro");
  for (const e of bitacora.ultimos.slice(-nuevos)) {
    const linea = document.createElement("div");
    const tipo = document.createElement("span");
    tipo.className = "tipo"; tipo.style.color = COLOR_EVENTO[e.tipo] || "inherit";
    tipo.textContent = `${e.hora.slice(0, 5)}${e.robot ? " " + e.robot : ""} ${e.nombre.toUpperCase()}`;
    linea.append(tipo, `  ${e.mensaje}`);
    registro.append(linea);
  }
  registro.scrollTop = registro.scrollHeight;
  vista.mostrados = bitacora.total;
}

function dibujarBarras(e) {
  const r = e.resumen, s = Math.floor((Date.now() - vista.inicio) / 1000);
  const turno = `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  const hora = new Date().toTimeString().slice(0, 5);
  $("barra-superior").textContent = `UdeM·DESPACHO   |   ${r.robots} robots   |   ${r.en_ruta} en ruta   |   ` +
    `${r.esperando} en espera   |   turno ${turno}   |   ${hora}`;
  $("barra-inferior").textContent = `Flota sincronizada ${r.disponibles}/${r.robots}   |   clima: ${e.clima.proveedor}   |   ` +
    `calendario: ${e.calendario.proveedor} · festivo: ${e.calendario.festivo || "no"}   |   mantenimiento: ${r.mantenimiento}` +
    `   |   © OpenStreetMap contributors · Open-Meteo · Nager.Date · retratos RoboHash (CC-BY)`;
}

// --- Controles ----------------------------------------------------------------------------
function conectarControles() {
  $("boton-auto").addEventListener("click", () => vista.llamada !== null && despacharCon(api.despachar_auto(vista.llamada)));
  document.querySelector("[data-cerrar=llamada]").addEventListener("click", cerrarLlamada);
  document.querySelector("[data-cerrar=robot]").addEventListener("click", () => elegirRobot(vista.robotElegido));
  $("boton-vista").addEventListener("click", cambiarVista);
  $("boton-modo").addEventListener("click", () => mapa.alternar());
  $("boton-girar").addEventListener("click", () => mapa.girar());
  $("boton-mas").addEventListener("click", () => mapa.acercar(1.4));
  $("boton-menos").addEventListener("click", () => mapa.acercar(1 / 1.4));
  $("boton-exportar").addEventListener("click", async () => {
    const r = await api.exportar_bitacora();
    if (r && r.error) avisar(r.error);
  });

  segmentado($("selector-clima"), real => { api.usar_clima(real); $("simulador").querySelectorAll("input").forEach(i => i.disabled = real); });
  segmentado($("selector-calendario"), real => { api.usar_calendario(real); $("festivo").disabled = real; });
  const clima = () => api.configurar_clima($("viento").value, $("lluvia").value, $("dia").checked,
                                           $("visibilidad").value, $("tormenta").checked);
  ["viento", "lluvia", "visibilidad", "dia", "tormenta"].forEach(id => $(id).addEventListener("input", clima));
  $("festivo").addEventListener("change", () => api.configurar_festivo($("festivo").checked ? "Festivo simulado" : null));

  document.addEventListener("keydown", e => {
    if (e.target.matches("input, select")) return;  // escribir en el formulario no dispara atajos
    if (e.key === "Escape") { cerrarLlamada(); if (vista.robotElegido) elegirRobot(vista.robotElegido); }
    if (e.key.toLowerCase() === "a" && vista.llamada !== null) despacharCon(api.despachar_auto(vista.llamada));
    if (e.key === "Tab" && mapa.alternar) { e.preventDefault(); mapa.alternar(); }
    if (e.key.toLowerCase() === "r" && mapa.girar) mapa.girar();
    if (e.key.toLowerCase() === "v") cambiarVista();
  });
}

function segmentado(contenedor, alCambiar) {
  contenedor.querySelectorAll("button").forEach(boton => boton.addEventListener("click", () => {
    contenedor.querySelectorAll("button").forEach(b => b.classList.toggle("activo", b === boton));
    alCambiar(boton.dataset.real === "true");
  }));
}
