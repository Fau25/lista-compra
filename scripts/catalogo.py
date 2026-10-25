"""Descarga el catálogo de Mercadona para un código postal y lo guarda en web/catalogo.json."""
import json, os, sys, time, urllib.request

BASE = "https://tienda.mercadona.es/api"
CP = os.environ.get("CP", "04230")
UA = {"User-Agent": "Mozilla/5.0 (lista-compra personal)", "Accept": "application/json"}


def pedir(url, metodo="GET", datos=None):
    cuerpo = json.dumps(datos).encode() if datos is not None else None
    cab = dict(UA, **({"Content-Type": "application/json"} if cuerpo else {}))
    for intento in range(4):
        try:
            req = urllib.request.Request(url, data=cuerpo, headers=cab, method=metodo)
            with urllib.request.urlopen(req, timeout=30) as r:
                texto = r.read().decode()
                return (json.loads(texto) if texto.strip() else {}), r.headers
        except Exception as e:
            print(f"  fallo {url}: {e}", file=sys.stderr)
            time.sleep(2 * (intento + 1))
    raise SystemExit(f"No se pudo descargar {url}")


def almacen():
    _, cab = pedir(f"{BASE}/postal-codes/actions/change-pc/", "PUT", {"new_postal_code": CP})
    wh = cab.get("x-customer-wh")
    if not wh:
        raise SystemExit("Mercadona no devolvió almacén para ese código postal")
    return wh


def main():
    wh = almacen()
    print(f"Código postal {CP} → almacén {wh}")
    raiz, _ = pedir(f"{BASE}/categories/?lang=es&wh={wh}")
    productos, cats = [], []
    for grupo in raiz.get("results", []):
        for sub in grupo.get("categories", []):
            cats.append({"id": sub["id"], "nombre": sub["name"], "grupo": grupo["name"]})
            datos, _ = pedir(f"{BASE}/categories/{sub['id']}/?lang=es&wh={wh}")
            for sec in datos.get("categories", []):
                for p in sec.get("products", []):
                    productos.append({
                        "id": p["id"],
                        "n": p.get("display_name"),
                        "f": p.get("packaging"),
                        "img": p.get("thumbnail"),
                        "g": grupo["name"],
                        "c": sub["name"],
                        "s": sec.get("name"),
                    })
            time.sleep(0.3)
    os.makedirs("web", exist_ok=True)
    salida = {"cp": CP, "almacen": wh,
              "categorias": cats, "productos": productos}
    with open("web/catalogo.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(cats)} categorías, {len(productos)} productos, "
          f"{os.path.getsize('web/catalogo.json') // 1024} KB")


if __name__ == "__main__":
    main()
