# -*- coding: utf-8 -*-
"""扫图库 -> index.json（含 10x10 dHash 视觉指纹）

用法: python3 build_index.py --gallery ./gallery [--out ./gallery/index.json]
依赖: pillow imagehash
"""
import argparse, json
from pathlib import Path
from PIL import Image
import imagehash


def build(gallery: Path, out: Path, hash_size: int = 10):
    meta_path = gallery / "meta.json"
    if not meta_path.exists():
        raise SystemExit(f"[build_index] 缺少 {meta_path}，先按 references/gallery-schema.md 建 meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    items, missing = [], []
    for m in meta:
        img = gallery / m["img"]
        if not img.exists():
            missing.append(m["img"])
            continue
        with Image.open(img) as im:
            w, h = im.size
            dh = str(imagehash.dhash(im, hash_size=hash_size))
        items.append({**m, "dhash": dh, "w": w, "h": h})
    idx = {"gallery": gallery.name, "count": len(items), "hash_size": hash_size, "items": items}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[build_index] {len(items)} 题 -> {out}")
    if missing:
        print(f"[build_index] 跳过缺失图片 {len(missing)} 张: {missing[:5]}")
    return idx


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gallery", default="./gallery")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    g = Path(a.gallery).resolve()
    build(g, Path(a.out).resolve() if a.out else g / "index.json")
