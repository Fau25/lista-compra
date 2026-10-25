"""Busca en Wikimedia Commons una foto libre por receta y la guarda reducida en web/fotos/.
- scripts/fotos_busqueda.json: receta → búsqueda.
- scripts/fotos_elegidas.json (opcional): receta → "File:Nombre.jpg" para forzar una foto concreta.
- Las recetas que ya tienen foto no se vuelven a buscar (borra la foto o pon REHACER=slug1,slug2).
"""
import json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "MiCompra/1.0 (app personal; github.com/Fau25/lista-compra)"}
MALAS = re.compile(r"logo|map|mapa|menu|men[uú]|sign|cartel|package|packaging|label|etiqueta|restaurant|plant|planta|field|campo|stamp|coat of arms", re.I)


def slug(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def api(params):
    params.update({"format": "json", "formatversion": "2"})
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def limpiar(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()[:80]


def candidatos(busqueda=None, archivo=None):
    p = {"action": "query", "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": "500"}
    if archivo:
        p["titles"] = archivo
    else:
        p.update({"generator": "search", "gsrsearch": f"{busqueda} filetype:bitmap", "gsrnamespace": "6", "gsrlimit": "12"})
    paginas = api(p).get("query", {}).get("pages", [])
    paginas.sort(key=lambda x: x.get("index", 0))
    for pg in paginas:
        ii = (pg.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
            continue
        if not archivo and (ii.get("width", 0) < 500 or MALAS.search(pg["title"])):
            continue
        meta = ii.get("extmetadata", {})
        yield {
            "url": ii.get("thumburl") or ii.get("url"),
            "pagina": ii.get("descriptionurl"),
            "autor": limpiar(meta.get("Artist", {}).get("value")) or "Autor desconocido",
            "licencia": limpiar(meta.get("LicenseShortName", {}).get("value")) or "Licencia libre",
        }


REG = []


def log(t):
    print(t); REG.append(t)


def descargar(url):
    for intento in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and intento < 4:
                time.sleep(int(e.headers.get("Retry-After") or 0) or 15 * (intento + 1)); continue
            raise


def main():
    busquedas = json.load(open("scripts/fotos_busqueda.json", encoding="utf-8"))
    elegidas = json.load(open("scripts/fotos_elegidas.json", encoding="utf-8")) if os.path.exists("scripts/fotos_elegidas.json") else {}
    os.makedirs("web/fotos", exist_ok=True)
    ruta_cred = "web/fotos/creditos.json"
    cred = json.load(open(ruta_cred, encoding="utf-8")) if os.path.exists(ruta_cred) else {}
    rehacer = set(filter(None, os.environ.get("REHACER", "").split(",")))
    nuevas = fallos = seguidos = 0
    for receta, q in busquedas.items():
        s = slug(receta)
        destino = f"web/fotos/{s}.jpg"
        if os.path.exists(destino) and s in cred and s not in rehacer:
            continue
        try:
            vieja = cred.get(s, {}).get("pagina") if s in rehacer else None
            c = next((x for x in (candidatos(archivo=elegidas[receta]) if receta in elegidas else candidatos(q)) if x["pagina"] != vieja), None)
            if not c:
                log(f"sin foto: {receta} ({q})"); fallos += 1; continue
            datos = descargar(c["url"])
            with open(destino, "wb") as f:
                f.write(datos)
            cred[s] = {"autor": c["autor"], "licencia": c["licencia"], "pagina": c["pagina"]}
            nuevas += 1
            log(f"ok: {receta}")
        except Exception as e:
            log(f"error: {receta}: {e}"); fallos += 1
            if "429" in str(e):
                seguidos += 1
                if seguidos >= 2:
                    log("Wikimedia pide esperar: se sigue en la próxima pasada"); break
                time.sleep(60); continue
        seguidos = 0
        time.sleep(6)
    json.dump(cred, open(ruta_cred, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    log(f"{nuevas} fotos nuevas, {fallos} sin foto, {len(cred)} en total")
    open("scripts/fotos_registro.txt", "w", encoding="utf-8").write("\n".join(REG) + "\n")


if __name__ == "__main__":
    main()
