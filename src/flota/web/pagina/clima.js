// El clima dibujado sobre el mapa web: luces de noche, nubes, lluvia, niebla y relámpagos.
// Usa estado.ambiente y la geometría de CentroControl; es la misma lógica de gui/capa_clima.py.

export const ALTURA_NUBES_M = 70;
const EXAGERAR_VIENTO = 4, MARGEN_NUBES_M = 150, GOTAS_MAX = 160, CAIDA_PX_S = 650;

function azarFijo(semilla) {  // mulberry32: el mismo número de semilla da las mismas nubes
  return () => {
    semilla = (semilla + 0x6D2B79F5) | 0;
    let t = Math.imul(semilla ^ (semilla >>> 15), 1 | semilla);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function posicionNube(nube, viento, t, limites) {
  const [x0, y0, x1, y1] = [limites[0] - MARGEN_NUBES_M, limites[1] - MARGEN_NUBES_M,
                            limites[2] + MARGEN_NUBES_M, limites[3] + MARGEN_NUBES_M];
  const vuelta = (v, a, b) => a + (((v - a) % (b - a)) + (b - a)) % (b - a);
  return [vuelta(nube.x + viento[0] * EXAGERAR_VIENTO * t, x0, x1), vuelta(nube.y + viento[1] * EXAGERAR_VIENTO * t, y0, y1)];
}

const sprites = {};
export function spriteNube(semilla) {  // nube algodonosa: círculos claros juntos y difuminados
  if (sprites[semilla]) return sprites[semilla];
  const lado = 256, c = document.createElement("canvas");
  c.width = c.height = lado;
  const g = c.getContext("2d"), azar = azarFijo(semilla);
  g.filter = `blur(${lado / 14}px)`;
  g.fillStyle = "rgb(222, 233, 234)";
  for (let i = 0; i < 9; i++) {
    const r = (0.12 + azar() * 0.08) * lado, x = (0.35 + azar() * 0.3) * lado, y = (0.38 + azar() * 0.24) * lado;
    g.beginPath(); g.arc(x, y, r, 0, 2 * Math.PI); g.fill();
  }
  return (sprites[semilla] = c);
}

export function dibujarLuces(c, ambiente, geo, proyectar) {
  if (!ambiente.noche) return;
  for (const [x, y, z] of geo.luces) {
    const [sx, sy] = proyectar(x, y, z);
    const brillo = c.createRadialGradient(sx, sy, 0, sx, sy, 6);
    brillo.addColorStop(0, "rgba(255, 211, 107, 1)");
    brillo.addColorStop(0.35, "rgba(255, 211, 107, .8)");
    brillo.addColorStop(1, "rgba(255, 180, 60, 0)");
    c.fillStyle = brillo; c.fillRect(sx - 6, sy - 6, 12, 12);
  }
}

// Encima de los robots. Las nubes se dibujan aquí solo en el mapa 2D: en el 3D son planos de three.js.
export function dibujarEncima(c, ancho, alto, ambiente, geo, proyectar, escala, t, conNubes) {
  if (conNubes) {
    const visibles = geo.nubes.slice(0, Math.round(geo.nubes.length * ambiente.nubes));
    c.globalAlpha = ambiente.nubes * 0.6;
    for (const n of visibles) {
      const [x, y] = posicionNube(n, ambiente.viento, t, geo.limites), [sx, sy] = proyectar(x, y, 0), lado = n.radio * 2 * escala;
      c.drawImage(spriteNube(n.semilla), sx - lado / 2, sy - lado / 2, lado, lado);
    }
    c.globalAlpha = 1;
  }
  if (ambiente.lluvia > 0) {
    const vientoPx = ambiente.viento[0] * 25, inclinacion = Math.max(-0.8, Math.min(0.8, vientoPx / CAIDA_PX_S)), largo = 14;
    const azar = azarFijo(3);
    c.strokeStyle = ambiente.noche ? "rgba(127, 168, 176, .8)" : "rgba(212, 241, 238, .75)";
    c.lineWidth = 1; c.beginPath();
    for (let i = 0; i < Math.round(GOTAS_MAX * ambiente.lluvia); i++) {
      const u = azar(), v = azar(), rapidez = 0.8 + azar() * 0.4;
      const y = (v * alto + t * CAIDA_PX_S * rapidez) % alto, x = ((u * ancho + t * vientoPx * rapidez) % ancho + ancho) % ancho;
      c.moveTo(x, y); c.lineTo(x + inclinacion * largo, y + largo);
    }
    c.stroke();
  }
  const oscuro = ambiente.lluvia * 0.3 + ambiente.niebla * 0.45;
  if (oscuro > 0) {  // cielo cargado y niebla: un velo encima de todo
    c.fillStyle = ambiente.niebla > ambiente.lluvia ? `rgba(205, 218, 218, ${oscuro})` : `rgba(6, 18, 24, ${oscuro})`;
    c.fillRect(0, 0, ancho, alto);
  }
  if (ambiente.tormenta && [0, 2].includes(Math.floor(t * 10) % 61)) {  // un destello cada ~6 s
    c.fillStyle = "rgba(235, 245, 255, .35)"; c.fillRect(0, 0, ancho, alto);
  }
}

// Recorta la foto con un degradado: opaca en el centro, transparente en el borde (como la neblina de
// los juegos viejos). Se hace aquí y no en Python para no mandar un PNG enorme por el puente.
export function difuminarBordes(imagen, fraccion = 0.18) {
  const c = document.createElement("canvas");
  c.width = imagen.width; c.height = imagen.height;
  const g = c.getContext("2d");
  g.drawImage(imagen, 0, 0);
  g.globalCompositeOperation = "destination-in";
  const franja = (x0, y0, x1, y1) => {
    const d = g.createLinearGradient(x0, y0, x1, y1);
    d.addColorStop(0, "rgba(0,0,0,0)"); d.addColorStop(fraccion, "rgba(0,0,0,1)");
    d.addColorStop(1 - fraccion, "rgba(0,0,0,1)"); d.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = d; g.fillRect(0, 0, c.width, c.height);
  };
  franja(0, 0, c.width, 0);
  franja(0, 0, 0, c.height);
  return c;
}

export const NEBLINA = { satelite: ["#56635c", "#05080f"], calles: ["#dcd8d0", "#0b0f16"] };

export function puntoEnPoligono(x, y, poligono) {
  let dentro = false;
  for (let i = 0, j = poligono.length - 1; i < poligono.length; j = i++) {
    const [xi, yi] = poligono[i], [xj, yj] = poligono[j];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) dentro = !dentro;
  }
  return dentro;
}
