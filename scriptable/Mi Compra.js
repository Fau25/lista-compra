// Mi Compra · widget para Scriptable (iPhone / iPad)
// Muestra lo pendiente de la lista de la compra. Al tocarlo abre la app.
// Configuración: en el widget, «Parameter» = tu contraseña de Mi Compra.
// icon-color: deep-green; icon-glyph: shopping-basket;

const URL_SCRIPT = "https://script.google.com/macros/s/AKfycbxLGwL8uY56Q8Cl1CBQotiZIzz6NdHRpxFjn4kyqybkL5Or9g34nSiurC1aZ8VTjM6iaQ/exec";
const URL_APP = "https://fau25.github.io/lista-compra/web/";
const CLAVE = (args.widgetParameter || "").trim();

const fondo = Color.dynamic(new Color("#F5F1E8"), new Color("#1A201C"));
const texto = Color.dynamic(new Color("#1F2A24"), new Color("#E7EBE6"));
const suave = Color.dynamic(new Color("#6A675E"), new Color("#A9B0A7"));
const verde = Color.dynamic(new Color("#3E6B57"), new Color("#8CC4A8"));

async function pedirPendientes() {
  const fm = FileManager.local(), copia = fm.joinPath(fm.documentsDirectory(), "mi-compra-widget.json");
  try {
    const r = new Request(URL_SCRIPT);
    r.method = "POST";
    r.headers = { "Content-Type": "text/plain;charset=utf-8" };
    r.body = JSON.stringify({ clave: CLAVE, accion: "pendientes" });
    r.timeoutInterval = 20;
    const j = await r.loadJSON();
    if (!j.ok) return { error: j.error === "clave" ? "Contraseña incorrecta" : "Error del script" };
    j.hora = new Date().toISOString();
    fm.writeString(copia, JSON.stringify(j));
    return j;
  } catch (e) {
    if (fm.fileExists(copia)) { const j = JSON.parse(fm.readString(copia)); j.viejo = true; return j; }
    return { error: "Sin conexión" };
  }
}

function crear(d) {
  const w = new ListWidget();
  w.backgroundColor = fondo;
  w.url = URL_APP;
  w.setPadding(14, 16, 14, 16);
  const tam = config.widgetFamily || "medium";

  const cab = w.addStack(); cab.centerAlignContent();
  const t = cab.addText("Mi Compra"); t.font = Font.boldSystemFont(15); t.textColor = verde;
  cab.addSpacer();
  if (!d.error) {
    const n = cab.addText(d.pendientes.length ? `${d.pendientes.length} pendiente${d.pendientes.length === 1 ? "" : "s"}` : "Todo comprado");
    n.font = Font.semiboldSystemFont(13); n.textColor = texto;
  }
  w.addSpacer(8);

  if (!CLAVE) { const m = w.addText("Pon tu contraseña en «Parameter» al editar el widget."); m.font = Font.systemFont(12); m.textColor = suave; return w; }
  if (d.error) { const m = w.addText(d.error); m.font = Font.systemFont(13); m.textColor = suave; return w; }
  if (!d.pendientes.length) { const m = w.addText("La lista está vacía."); m.font = Font.systemFont(13); m.textColor = suave; return w; }

  const max = tam === "large" ? 16 : tam === "small" ? 4 : 8;
  const cols = tam === "small" ? 1 : 2, porCol = Math.ceil(Math.min(max, d.pendientes.length) / cols);
  const fila = w.addStack(); fila.topAlignContent();
  for (let c = 0; c < cols; c++) {
    const col = fila.addStack(); col.layoutVertically(); col.spacing = 3;
    d.pendientes.slice(c * porCol, (c + 1) * porCol).slice(0, max).forEach(it => {
      const l = col.addText("• " + it.n + (it.q > 1 ? " ×" + it.q : ""));
      l.font = Font.systemFont(12.5); l.textColor = texto; l.lineLimit = 1;
    });
    if (c < cols - 1) fila.addSpacer(10);
  }
  w.addSpacer();
  const resto = d.pendientes.length - max;
  const pie = w.addText((resto > 0 ? `y ${resto} más · ` : "") + (d.viejo ? "sin conexión" : "actualizado ") + (d.viejo ? "" : new Date(d.hora).toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })));
  pie.font = Font.systemFont(10.5); pie.textColor = suave;
  w.refreshAfterDate = new Date(Date.now() + 15 * 60 * 1000);
  return w;
}

const datos = await pedirPendientes();
const widget = crear(datos);
if (config.runsInWidget) Script.setWidget(widget); else await widget.presentMedium();
Script.complete();
