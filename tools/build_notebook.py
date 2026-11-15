# -*- coding: utf-8 -*-
"""把匹配结果 + 图库元数据合并成 notebook.json（可直接喂给 render_pdf.py）"""
import base64, json, sys
from io import BytesIO
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def build(matches_path, gallery_dir, out_path):
    matches = json.loads(Path(matches_path).read_text(encoding="utf-8"))
    meta = {m["id"]: m for m in json.loads((gallery_dir / "meta.json").read_text(encoding="utf-8"))}
    cards = []
    for r in matches:
        best = r["candidates"][0]
        m = meta[best["id"]]
        img = gallery_dir / m["img"]
        with Image.open(img) as im:
            im = im.convert("RGB")
            if im.width > 1500:
                im = im.resize((1500, round(im.height * 1500 / im.width)), Image.LANCZOS)
            buf = BytesIO()
            im.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()
        src = m.get("source", {})
        cards.append({
            "id": m["id"], "subject": m["subject"], "knowledge": m["knowledge"],
            "answer": m["answer"], "my_answer": m["my_answer"],
            "error_type": m["error_type"], "why": m["why"],
            "source_text": f"{src.get('book') or src.get('paper') or ''} "
                           f"P{src.get('page', '')}".strip(),
            "match_score": r["best"], "action": r["action"],
            "img_data_url": f"data:image/png;base64,{b64}",
        })
    nb = {"title": "错题本 · 演示册", "generated_at": "2026-11-15", "cards": cards}
    Path(out_path).write_text(json.dumps(nb, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[build_notebook] {len(cards)} 张卡片 -> {out_path}")


if __name__ == "__main__":
    build(ROOT / "demo/output/matches.json", ROOT / "demo/gallery", ROOT / "demo/output/notebook.json")
