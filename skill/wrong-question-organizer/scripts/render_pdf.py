# -*- coding: utf-8 -*-
"""notebook.json -> A4 错题本 PDF（版式在 assets/card_template.html 里改）

用法:
  python3 render_pdf.py --notebook notebook.json --out 错题本.pdf [--verify] [--keep-html]

--verify 会在出 PDF 之前做四项硬检查，任一项不为 0 退出码 = 1：
  1) 单题跨页（卡片高度 > 一页可用高度）
  2) 重复题号
  3) 空题面
  4) 知识点不在 references/error-taxonomy.md 的词表里
"""
import argparse, datetime, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
TEMPLATE = SKILL / "assets" / "card_template.html"
TAXONOMY = SKILL / "references" / "error-taxonomy.md"

ERROR_LABEL = {"K01": "K01 知识盲区", "K02": "K02 方法不会", "K03": "K03 计算失误",
               "K04": "K04 审题偏差", "K05": "K05 时间不够"}


def esc(s):
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def review_dates(base=None):
    base = base or datetime.date.today()
    return [(base + datetime.timedelta(days=d)).strftime("%m-%d") for d in (1, 2, 4, 7, 15, 30)]


def vocab():
    """从 error-taxonomy.md 抽出受控知识点词表（按空白切分，取含 '/' 的词与全大写缩写）"""
    if not TAXONOMY.exists():
        return set()
    txt = TAXONOMY.read_text(encoding="utf-8")
    words = set()
    for block in re.findall(r"```\n(.*?)```", txt, re.S):
        for line in block.splitlines():
            for tok in line.split():
                if "/" in tok or re.fullmatch(r"[A-Z]{2,}", tok):
                    words.add(tok)
    return words


def card_html(c, idx, vocab_set=None):
    src = c.get("img_data_url") or ""
    kn = "".join(f"<span class='tag'>{esc(k)}</span>" for k in c.get("knowledge", []))
    er = ERROR_LABEL.get(c.get("error_type", ""), c.get("error_type", ""))
    rd = " · ".join(review_dates())
    return f"""<div class="card" data-id="{esc(c.get('id'))}">
  <i class="cm1"></i><i class="cm2"></i>
  <div class="hd">
    <span class="no">[{esc(c.get('id'))}]</span>{kn}
    <span class="tag err">{esc(er)}</span>
    <span class="sp"></span>
    <span class="sub">{esc(c.get('subject', ''))} · {esc(c.get('source_text', ''))}</span>
  </div>
  <img class="qimg" src="{src}">
  <div class="grid">
    <div class="cell"><span class="k">我的错解</span><span class="wrong">{esc(c.get('my_answer') or '—')}</span></div>
    <div class="cell"><span class="k">正确解</span><span class="ok">{esc(c.get('answer') or '—')}</span></div>
    <div class="cell"><span class="k">错在哪</span>{esc(c.get('why') or '—')}</div>
    <div class="cell"><span class="k">复习节奏</span>{esc(rd)}</div>
  </div>
  <div class="foot">第 {idx} 题 · 图库命中 {c.get('match_score', '—')}</div>
</div>"""


def build_html(cards):
    tpl = TEMPLATE.read_text(encoding="utf-8")
    body = "".join(card_html(c, i + 1) for i, c in enumerate(cards)) or \
        '<div class="nothing">没有可排版的错题（全部为 reject，请改用原照片作题面）</div>'
    return tpl.replace("__CARDS__", body)


def check(nb):
    cards = nb["cards"]
    problems = {"dup_id": [], "no_image": [], "vocab_out": [], "overflow": []}
    vset = vocab()
    seen = set()
    for c in cards:
        cid = c.get("id")
        if cid in seen:
            problems["dup_id"].append(cid)
        seen.add(cid)
        if not c.get("img_data_url"):
            problems["no_image"].append(cid)
        if vset:
            for k in c.get("knowledge") or []:
                if k not in vset:
                    problems["vocab_out"].append(f"{cid}:{k}")
    return problems


def render(notebook_path, out_path, verify=False, keep_html=False):
    nb = json.loads(Path(notebook_path).read_text(encoding="utf-8"))
    problems = check(nb)
    html = build_html(nb["cards"])
    html_path = Path(out_path).with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/local/bin/chromium",
                              args=["--no-sandbox", "--font-render-hinting=none"])
        pg = b.new_page(viewport={"width": 794, "height": 1123})  # A4 @96dpi
        pg.goto(html_path.absolute().as_uri())
        pg.wait_for_timeout(500)
        # 单题跨页检查：卡片高度不得超过一页可用高度（277mm ≈ 1047px）
        heights = pg.evaluate("""() => {
          const mm = 96 / 25.4;
          const limit = 277 * mm;
          return [...document.querySelectorAll('.card')].map(el => ({
            id: el.dataset.id, h: el.getBoundingClientRect().height / mm, limit: 277 }));
        }""")
        for h in heights:
            if h["h"] > h["limit"]:
                problems["overflow"].append(f"{h['id']} {h['h']:.1f}mm")
        pg.pdf(path=str(out_path), format="A4", print_background=True,
               margin={"top": "8mm", "bottom": "12mm", "left": "10mm", "right": "10mm"})
        b.close()
    if not keep_html:
        html_path.unlink(missing_ok=True)

    bad = sum(len(v) for v in problems.values())
    print(f"[render_pdf] {len(nb['cards'])} 题 -> {out_path}")
    for k, v in problems.items():
        if v:
            print(f"[render_pdf] {k}: {v[:6]}")
    if verify:
        print(f"[verify] {'PASS' if bad == 0 else 'FAIL'} · 问题 {bad} 处")
        return 0 if bad == 0 else 1
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--notebook", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--keep-html", action="store_true")
    a = ap.parse_args()
    sys.exit(render(a.notebook, a.out, a.verify, a.keep_html))
