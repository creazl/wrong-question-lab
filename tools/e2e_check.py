# -*- coding: utf-8 -*-
"""端到端自检：跑一遍 web 与 app，截图 + 导出打印版 PDF"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOT = ROOT / "demo/output"


def run(html, mode, out_prefix, viewport):
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/local/bin/chromium", args=["--no-sandbox"])
        pg = b.new_page(viewport=viewport, device_scale_factor=2)
        pg.goto((ROOT / html).as_uri())
        pg.wait_for_timeout(800)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.screenshot(path=str(SHOT / f"{out_prefix}-1-初始.png"), full_page=True)

        # 逐个样张走"拍照 -> 匹配 -> 加入"
        n = pg.locator(".smp").count()
        for i in range(n):
            pg.locator(".smp").nth(i).click()
            pg.wait_for_timeout(300)
            if i == 0:
                pg.screenshot(path=str(SHOT / f"{out_prefix}-2-匹配.png"), full_page=True)
            btn = pg.locator("#matchBox [data-add]")
            if btn.count():
                btn.first.click()
                pg.wait_for_timeout(200)
        cnt = pg.locator(".card").count()
        pg.screenshot(path=str(SHOT / f"{out_prefix}-3-错题卡.png"), full_page=True)

        # 打印版 PDF
        pg.pdf(path=str(SHOT / f"{out_prefix}-4-打印版.pdf"), format="A4", print_background=True,
               margin={"top": "8mm", "bottom": "12mm", "left": "10mm", "right": "10mm"})
        print(f"[e2e] {mode}: 样张 {n}，入库 {cnt} 题，JS 报错 {len(errs)}")
        for e in errs:
            print("   ERR:", e)
        b.close()
        return cnt, errs


if __name__ == "__main__":
    c1, e1 = run("web/index.html", "web", "web", {"width": 1280, "height": 900})
    c2, e2 = run("app/index.html", "app", "app", {"width": 390, "height": 844})
    ok = c1 == 6 and c2 == 6 and not e1 and not e2
    print("[e2e] 结果:", "PASS" if ok else "CHECK")
    sys.exit(0 if ok else 1)
