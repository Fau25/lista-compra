"""Genera web/recetas.json ligando cada ingrediente al producto más parecido del catálogo."""
import json, re, sys, unicodedata
sys.path.insert(0, "scripts")
from recetas_fuente import R

def norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ ]+", " ", s)).strip()

cat = json.load(open("web/catalogo.json", encoding="utf-8"))["productos"]
for p in cat:
    p["_w"] = norm(p["n"]).split()

def mejor(q):
    qs, res = norm(q).split(), []
    for p in cat:
        pts = 0
        for t in qs:
            k = next((i for i, w in enumerate(p["_w"]) if w.startswith(t)), -1)
            if k < 0:
                break
            pts += k
        else:
            res.append((pts * 2 + len(p["_w"]) + (20 if p["z"] in (7, 11, 12) else 0), p))
    res.sort(key=lambda x: x[0])
    return res[0][1] if res else None

salida, fallos = [], []
for n_, (nombre, t, rac, g, ing, bas, pasos) in enumerate(R):
    lista = []
    for n, q, c in ing:
        p = mejor(q)
        if not p:
            fallos.append(f"{nombre}: {n} ({q})")
        lista.append({"n": n, "q": q, "c": c, "pid": p["id"] if p else None})
        if "-v" in sys.argv:
            print(f"{nombre[:28]:28} | {q:22} → {p['n'] + ' · ' + p['f'] if p else '¡SIN PRODUCTO!'}")
    salida.append({"id": f"r{n_ + 1}", "n": nombre, "t": t, "r": rac, "g": g, "ing": lista, "b": bas, "p": pasos})

json.dump(salida, open("web/recetas.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(f"{len(salida)} recetas; ingredientes sin producto: {len(fallos)}")
for f in fallos:
    print("  ·", f)
