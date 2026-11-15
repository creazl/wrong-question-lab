# -*- coding: utf-8 -*-
"""匹配结果 + 图库元数据 -> notebook.json（喂给 render_pdf.py）

用法: python3 build_notebook.py --matches matches.json --gallery ./gallery --out notebook.json [--title 错题本]
"""
import argparse, base64, json
from io import BytesIO
from pathlib import Path
from PIL import Image


def build(matches_path, gallery_dir, out_path, title="错题本", max_w=1500):
    matches = json.loads(Path(matches_path).read_text(encoding="utf-8"))
    gallery_dir = Path(gallery_dir)
    idx = json.loads((gallery_dir / "index.json").read_text(encoding="utf-8"))
    by_id = {m["id"]: m for m in idx["items"]}

    cards, skipped = [], 0
    for r in matches:
        # reject 的题不许用图库图（可能不是同一道题），只能靠调用方提供原照片
        if r["action"] == "reject" or not r["candidates"]:
            skipped += 1
            continue
        best = r["candidates"][0]
        m = by_id.get(best["id"])
        if not m:
            skipped += 1
            continue
        img = gallery_dir / m["img"]
        with Image.open(img) as im:
            im = im.convert("RGB")
            if im.width > max_w:
                im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
            buf = BytesIO()
            im.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()

        src = m.get("source", {}) or {}
        cards.append({
            "id": m["id"], "subject": m.get("subject", ""), "knowledge": m.get("knowledge", []),
            "answer": m.get("answer", ""), "my_answer": m.get("my_answer", ""),
            "error_type": m.get("error_type", ""), "why": m.get("why", ""),
            "source_text": f"{src.get('book') or src.get('paper') or ''} P{src.get('page', '')}".strip(),
            "match_score": r["best"], "action": r["action"],
            "img_data_url": f"data:image/png;base64,{b64}",
        })

    nb = {"title": title, "cards": cards}
    Path(out_path).write_text(json.dumps(nb, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[build_notebook] {len(cards)} 张卡片 -> {out_path}")
    if skipped:
        print(f"[build_notebook] 跳过 {skipped} 条 reject/无效匹配（需改用原照片作题面）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches", default="./matches.json")
    ap.add_argument("--gallery", default="./gallery")
    ap.add_argument("--out", default="./notebook.json")
    ap.add_argument("--title", default="错题本")
    a = ap.parse_args()
    build(a.matches, a.gallery, a.out, a.title)
