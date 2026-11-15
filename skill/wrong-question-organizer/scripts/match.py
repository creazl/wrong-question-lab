# -*- coding: utf-8 -*-
"""把"照片指纹"与图库索引做三级匹配。

用法:
  python3 match.py --index ./gallery/index.json --features probe.json
  python3 match.py --index ./gallery/index.json --features-dir ./probes --out matches.json
"""
import argparse, json
from pathlib import Path


def norm(s):
    return "".join(str(s).split()).replace("　", "").replace("_", "").lower()


def toks(nums):
    out = set()
    for n in nums or []:
        t = norm(n).replace("−", "-").replace("′", "'")
        out.add(t)
        digits = "".join(c for c in t if c.isdigit() or c in ".-")
        if digits:
            out.add(digits)
    return out


def bigrams(s):
    s = norm(s)
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}


def jaccard(a, b):
    return 0.0 if not a or not b else len(a & b) / len(a | b)


def overlap(a, b):
    """偏向召回：以较短的一方为分母"""
    return 0.0 if not a or not b else len(a & b) / min(len(a), len(b))


def hamming(h1, h2):
    try:
        from imagehash import hex_to_hash
        return hex_to_hash(h1) - hex_to_hash(h2)
    except Exception:
        return 99


def score(item, probe, w=(0.45, 0.30, 0.20, 0.05)):
    n = overlap(toks(probe.get("numbers")), toks(item["fingerprint"]["numbers"]))
    f = jaccard({norm(x) for x in probe.get("formulas") or []},
                {norm(x) for x in item["fingerprint"]["formulas"]})
    t = jaccard(bigrams(probe.get("stem_keywords") or ""), bigrams(item.get("stem_text") or ""))
    vis = 0.0
    if probe.get("dhash") and item.get("dhash"):
        vis = max(0.0, 1.0 - hamming(probe["dhash"], item["dhash"]) / 40.0)
    total = w[0] * n + w[1] * f + w[2] * t + w[3] * vis
    return round(total, 4), {"numbers": round(n, 3), "formulas": round(f, 3),
                             "text": round(t, 3), "visual": round(vis, 3)}


def match(index_path, probe, topk=3):
    idx = json.loads(Path(index_path).read_text(encoding="utf-8"))
    scored = []
    for it in idx["items"]:
        s, detail = score(it, probe)
        scored.append({"id": it["id"], "subject": it["subject"], "score": s, "detail": detail,
                       "stem_text": it.get("stem_text", ""), "img": it["img"],
                       "answer": it.get("answer", ""), "knowledge": it.get("knowledge", []),
                       "my_answer": it.get("my_answer", ""), "why": it.get("why", ""),
                       "error_type": it.get("error_type", ""), "source": it.get("source", {})})
    scored.sort(key=lambda x: -x["score"])
    top = scored[:topk]
    best = top[0]["score"] if top else 0.0
    action = "auto" if best >= 0.80 else ("confirm" if best >= 0.45 else "reject")
    return {"probe": probe, "action": action, "best": best, "candidates": top,
            "gap": round(top[0]["score"] - (top[1]["score"] if len(top) > 1 else 0), 3)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="./gallery/index.json")
    ap.add_argument("--features", default=None)
    ap.add_argument("--features-dir", default=None)
    ap.add_argument("--out", default="./matches.json")
    a = ap.parse_args()

    results = []
    if a.features_dir:
        for p in sorted(Path(a.features_dir).glob("*.features.json")):
            probe = json.loads(p.read_text(encoding="utf-8"))
            r = match(a.index, probe)
            r["photo"] = p.name.replace(".features.json", ".jpg")
            results.append(r)
            print(f"[match] {r['photo']:<28} -> {r['candidates'][0]['id'] if r['candidates'] else '-':<12} "
                  f"score={r['best']:.3f} action={r['action']}")
    elif a.features:
        results = [match(a.index, json.loads(Path(a.features).read_text(encoding="utf-8")))]
        print(json.dumps(results[0], ensure_ascii=False, indent=2))
    else:
        raise SystemExit("需要 --features 或 --features-dir")

    if a.features_dir:
        acc = sum(1 for r in results if r["candidates"] and r["photo"].startswith(r["candidates"][0]["id"]))
        print(f"[match] 命中率 {acc}/{len(results)} = {acc / max(len(results), 1):.0%}")
    Path(a.out).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[match] -> {a.out}")
