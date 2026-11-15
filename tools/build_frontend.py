# -*- coding: utf-8 -*-
"""
把图库 + 样张照片 + 预置指纹打成一个自包含的数据对象，并生成 web / app 两个单文件前端。
产物全部内联，双击 index.html（file://）即可运行，无需后端。

用法： python3 tools/build_frontend.py
"""
import base64, json, re
from io import BytesIO
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GAL = ROOT / "demo/gallery"
PHO = ROOT / "demo/photos"
TPL = ROOT / "tools/templates/app_template.html"


def data_url(path, max_w):
    with Image.open(path) as im:
        im = im.convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        buf = BytesIO()
        im.save(buf, format="JPEG", quality=72, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def build_data():
    idx = json.loads((GAL / "index.json").read_text(encoding="utf-8"))
    items = []
    for it in idx["items"]:
        items.append({
            "id": it["id"], "subject": it["subject"], "chapter": it.get("chapter", ""),
            "knowledge": it["knowledge"], "stem_text": it["stem_text"],
            "numbers": it["fingerprint"]["numbers"], "formulas": it["fingerprint"]["formulas"],
            "answer": it["answer"], "my_answer": it.get("my_answer", ""),
            "why": it.get("why", ""), "error_type": it.get("error_type", ""),
            "source": it.get("source", {}), "dhash": it["dhash"],
            "thumb": data_url(GAL / it["img"], 520),
            "img": data_url(GAL / it["img"], 1200),
        })
    samples = []
    for p in sorted(PHO.glob("*.jpg")):
        f = p.with_suffix(".features.json")
        feat = json.loads(f.read_text(encoding="utf-8"))
        samples.append({"file": p.name, "thumb": data_url(p, 520), "features": feat})
    return {"items": items, "samples": samples,
            "knowledge_vocab": sorted({k for it in items for k in it["knowledge"]})}


def render_html(data, mode):
    tpl = TPL.read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False)
    html = tpl.replace("__MODE__", mode).replace("__DATA__", payload)
    return html


if __name__ == "__main__":
    data = build_data()
    for mode, out in (("web", ROOT / "web/index.html"), ("app", ROOT / "app/index.html")):
        out.write_text(render_html(data, mode), encoding="utf-8")
        print(f"[build_frontend] {mode} -> {out} ({out.stat().st_size/1024:.0f} KB)")
    # PWA 附加文件
    (ROOT / "app/manifest.webmanifest").write_text(json.dumps({
        "name": "错题整理", "short_name": "错题本", "start_url": "./index.html",
        "display": "standalone", "background_color": "#ffffff", "theme_color": "#111111",
        "icons": [{"src": "icon.svg", "sizes": "any", "type": "image/svg+xml"}]
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "app/sw.js").write_text(
        "const C='wqn-v1';const A=['./index.html','./manifest.webmanifest','./icon.svg'];\n"
        "self.addEventListener('install',e=>e.waitUntil(caches.open(C).then(c=>c.addAll(A))));\n"
        "self.addEventListener('fetch',e=>e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request))));\n",
        encoding="utf-8")
