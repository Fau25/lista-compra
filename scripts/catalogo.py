"""Descarga el catálogo de Mercadona para un código postal y lo guarda en web/catalogo.json."""
import json, os, sys, time, urllib.request

BASE = "https://tienda.mercadona.es/api"
CP = os.environ.get("CP", "04230")
SECCIONES = [
    ("Fruta y verdura", ["Fruta y verdura"]),
    ("Carne", ["Carne"]),
    ("Pescado", ["Marisco y pescado"]),
    ("Charcutería y quesos", ["Charcutería y quesos"]),
    ("Lácteos y huevos", ["Huevos, leche y mantequilla", "Postres y yogures"]),
    ("Panadería", ["Panadería y pastelería"]),
    ("Despensa", ["Aceite, especias y salsas", "Arroz, legumbres y pasta", "Conservas, caldos y cremas",
                  "Cereales y galletas", "Cacao, café e infusiones", "Azúcar, caramelos y chocolate", "Aperitivos"]),
    ("Platos preparados", ["Pizzas y platos preparados"]),
    ("Congelados", ["Congelados"]),
    ("Bebidas", ["Agua y refrescos", "Zumos", "Bodega"]),
    ("Limpieza y hogar", ["Limpieza y hogar"]),
    ("Mascotas", ["Mascotas"]),
    ("Otros", []),  # cuidado personal, maquillaje, bebé, parafarmacia y lo nuevo
]
IMG = "https://prod-mercadona.imgix.net/images/"
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


def seccion(grupo):
    for i, (_, grupos) in enumerate(SECCIONES):
        if grupo in grupos:
            return i
    return len(SECCIONES) - 1


def numero(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return ""
    return f"{x:g}".replace(".", ",")


def formato(p):
    pi = p.get("price_instructions") or {}
    tam, uni = numero(pi.get("unit_size")), (pi.get("size_format") or "").strip()
    uni = {"l": "L", "ud": "ud", "kg": "kg", "g": "g", "ml": "ml"}.get(uni.lower(), uni)
    medida = f"{tam} {uni}".strip() if tam else ""
    if pi.get("is_pack") and pi.get("total_units") and pi.get("unit_name"):
        medida = f"{pi['total_units']} {pi['unit_name']}" + (f" · {medida}" if medida else "")
    return " ".join(x for x in [p.get("packaging") or "", medida] if x).strip()


def imagen(url):
    if url and url.startswith(IMG):
        return url[len(IMG):].split(".jpg")[0]
    return url


def main():
    wh = almacen()
    print(f"Código postal {CP} → almacén {wh}")
    raiz, _ = pedir(f"{BASE}/categories/?lang=es&wh={wh}")
    productos, vistos = [], set()
    for grupo in raiz.get("results", []):
        for sub in grupo.get("categories", []):
            datos, _ = pedir(f"{BASE}/categories/{sub['id']}/?lang=es&wh={wh}")
            for sec in datos.get("categories", []):
                for p in sec.get("products", []):
                    if p["id"] in vistos:
                        continue
                    vistos.add(p["id"])
                    productos.append({
                        "id": p["id"],
                        "n": p.get("display_name"),
                        "f": formato(p),
                        "i": imagen(p.get("thumbnail")),
                        "z": seccion(grupo["name"]),
                        "c": sub["name"],
                    })
            time.sleep(0.3)
    os.makedirs("web", exist_ok=True)
    salida = {"cp": CP, "almacen": wh, "secciones": [n for n, _ in SECCIONES],
              "productos": productos}
    with open("web/catalogo.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(productos)} productos, "
          f"{os.path.getsize('web/catalogo.json') // 1024} KB")


if __name__ == "__main__":
    main()
