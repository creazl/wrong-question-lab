# -*- coding: utf-8 -*-
"""
生成演示数据：
1) 图库题面（印刷体，干净） -> demo/gallery/img/*.png
2) 模拟手机拍摄照片（歪斜 + 红笔手写 + JPEG 压缩 + 灰底） -> demo/photos/*.jpg
3) 模拟"大模型抽指纹"的输出 -> demo/photos/*.features.json
4) 图库元数据 -> demo/gallery/meta.json

说明：真实的识别步骤由多模态模型完成；本脚本只负责造可复现的样本。
"""
import base64
import json
import os
import random
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
GAL = ROOT / "demo" / "gallery"
PHO = ROOT / "demo" / "photos"

QUESTIONS = [
    {
        "id": "q_hx_0001", "subject": "化学", "chapter": "物质结构与性质",
        "knowledge": ["物质结构/键角", "物质结构/VSEPR"],
        "no": 7,
        "stem": "下列分子中，键角最大的是",
        "options": ["A. H<sub>2</sub>O", "B. NH<sub>3</sub>", "C. CH<sub>4</sub>", "D. CO<sub>2</sub>"],
        "answer": "D",
        "numbers": ["104.5°", "107°", "109°28′", "180°"],
        "formulas": ["H2O", "NH3", "CH4", "CO2"],
        "source": {"book": "必修二", "page": 88},
        "write": "答案：C", "why": "把 CH₄ 的 109°28′ 当最大，忽略了 CO₂ 直线型的 180°",
        "error": "K01",
    },
    {
        "id": "q_hx_0002", "subject": "化学", "chapter": "物质结构与性质",
        "knowledge": ["物质结构/分子极性", "物质结构/杂化轨道"],
        "no": 9,
        "stem": "关于 SO<sub>2</sub> 与 CO<sub>2</sub> 两种分子的比较，下列说法正确的是",
        "options": ["A. 中心原子均为 sp 杂化", "B. 两者均为非极性分子",
                    "C. SO<sub>2</sub> 为 V 形，CO<sub>2</sub> 为直线形", "D. 键角均为 180°"],
        "answer": "C",
        "numbers": ["119.5°", "180°"],
        "formulas": ["SO2", "CO2"],
        "source": {"book": "必修二", "page": 91},
        "write": "选 A", "why": "SO₂ 的 S 是 sp² 杂化（含孤对电子），不是 sp",
        "error": "K01",
    },
    {
        "id": "q_wl_0001", "subject": "物理", "chapter": "恒定电流",
        "knowledge": ["电磁/闭合电路欧姆定律"],
        "no": 12,
        "stem": "如图，电源电动势 E=6 V，内阻 r=1 Ω，定值电阻 R<sub>1</sub>=2 Ω，R<sub>2</sub>=3 Ω，"
                "R<sub>2</sub> 与 R<sub>1</sub> 串联。闭合开关 S 后，电路中的电流为",
        "options": ["A. 0.5 A", "B. 1.0 A", "C. 1.2 A", "D. 2.0 A"],
        "answer": "B",
        "numbers": ["6 V", "1 Ω", "2 Ω", "3 Ω", "1.0 A"],
        "formulas": ["E=6V", "r=1Ω", "R1=2Ω", "R2=3Ω"],
        "source": {"paper": "十一月月考", "page": 3},
        "write": "I = 6/2 = 3A", "why": "分母漏掉内阻 r，且 R₁+R₂ 相加后也漏了",
        "error": "K03",
    },
    {
        "id": "q_wl_0002", "subject": "物理", "chapter": "磁场",
        "knowledge": ["电磁/洛伦兹力", "电磁/带电粒子在磁场中的运动"],
        "no": 15,
        "stem": "一质量为 m、电荷量为 q 的粒子以速度 v 垂直射入磁感应强度为 B 的匀强磁场，"
                "其做圆周运动的半径为",
        "options": ["A. mv/(qB)", "B. qB/(mv)", "C. mvB/q", "D. qvB/m"],
        "answer": "A",
        "numbers": ["90°"],
        "formulas": ["mv/(qB)", "qvB"],
        "source": {"paper": "十一月月考", "page": 4},
        "write": "选 C", "why": "把 r 与 vB 的关系记混，未用 qvB=mv²/r 推导",
        "error": "K02",
    },
    {
        "id": "q_sx_0001", "subject": "数学", "chapter": "导数及其应用",
        "knowledge": ["导数/极值", "导数/多项式求导"],
        "no": 18,
        "stem": "已知函数 f(x)=x<sup>3</sup>-3x<sup>2</sup>+2。<br>(1) 求 f′(x)；<br>"
                "(2) 求 f(x) 的极值点及极值。",
        "options": [],
        "answer": "f′(x)=3x²-6x；极大值 f(0)=2，极小值 f(2)=-2",
        "numbers": ["x^3", "-3x^2", "+2", "f(2)=-2"],
        "formulas": ["f'(x)=3x^2-6x"],
        "source": {"book": "选择性必修二", "page": 96},
        "write": "f'(x)=3x²-6x, 极值点 x=0", "why": "只解出一个驻点，漏了 x=2，且未判断极值类型",
        "error": "K02",
    },
    {
        "id": "q_sx_0002", "subject": "数学", "chapter": "计数原理",
        "knowledge": ["计数原理/二项式定理", "计数原理/常数项"],
        "no": 6,
        "stem": "二项式 (x + 1/x)<sup>6</sup> 展开式中的常数项为",
        "options": ["A. 15", "B. 20", "C. 6", "D. 1"],
        "answer": "B",
        "numbers": ["(x+1/x)^6", "15", "20"],
        "formulas": ["C(6,3)"],
        "source": {"book": "选择性必修三", "page": 31},
        "write": "选 A", "why": "通项 r 取错，应为 C(6,3)=20 而非 C(6,2)=15",
        "error": "K03",
    },
]


def stem_html(q):
    opts = ""
    if q["options"]:
        opts = "<div class='opts'>" + "".join(
            f"<span class='opt'>{o}</span>" for o in q["options"]) + "</div>"
    return f"""<div class="qno">{q['no']}.</div>
    <div class="stem">{q['stem']}</div>{opts}"""


PAGE_CSS = """
@page { size: A4; margin: 0; }
body { margin:0; font-family: "Noto Serif CJK SC","Source Han Serif SC",serif; background:#fff; }
.paper { width: 1000px; padding: 46px 52px; box-sizing: border-box; background:#fff; }
.qno { display:inline-block; font-weight:700; font-size:19px; color:#111; margin-right:6px; }
.stem { display:inline; font-size:20px; line-height:1.85; color:#111; }
.opts { margin-top:14px; display:flex; flex-wrap:wrap; gap:10px 34px; font-size:19px; color:#111; }
.opt { white-space:nowrap; }
sup, sub { font-size:0.72em; }
"""


def render_gallery(pw):
    """印刷体干净题面"""
    meta = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/local/bin/chromium", args=["--font-render-hinting=none","--no-sandbox"])
        pg = b.new_page(viewport={"width": 1000, "height": 400}, device_scale_factor=2)
        for q in QUESTIONS:
            html = f"<style>{PAGE_CSS}</style><div class='paper' id='p'>{stem_html(q)}</div>"
            pg.set_content(html)
            pg.wait_for_timeout(300)
            el = pg.query_selector("#p")
            out = GAL / "img" / f"{q['id']}.png"
            el.screenshot(path=str(out))
            meta.append({
                "id": q["id"], "subject": q["subject"], "chapter": q["chapter"],
                "knowledge": q["knowledge"], "stem_text": q["stem"],
                "fingerprint": {"numbers": q["numbers"], "formulas": q["formulas"]},
                "answer": q["answer"], "source": q["source"],
                "img": f"img/{q['id']}.png",
                "my_answer": q["write"], "error_type": q["error"], "why": q["why"],
            })
            print("gallery:", q["id"])
        b.close()
    (GAL / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def render_photos(pw, meta):
    """模拟手机拍：桌面灰底 + 纸张旋转 + 阴影 + 红笔手写 + JPEG 低质"""
    rnd = random.Random(20261115)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/usr/local/bin/chromium", args=["--font-render-hinting=none","--no-sandbox"])
        pg = b.new_page(viewport={"width": 1000, "height": 1320}, device_scale_factor=1.5)
        for q, m in zip(QUESTIONS, meta):
            img_path = GAL / m["img"]
            b64 = base64.b64encode(img_path.read_bytes()).decode()
            rot = rnd.choice([-3.4, -2.1, 2.6, 3.1, -1.6])
            hand = q["write"]
            html = f"""<style>
            body{{margin:0;background:radial-gradient(circle at 30% 20%,#b9b2a8,#8d867d 70%);
                  font-family:"Noto Serif CJK SC",serif;}}
            .sheet{{position:absolute;left:95px;top:80px;width:790px;height:1080px;background:#fff;
                    box-shadow:0 18px 40px rgba(0,0,0,.45);transform:rotate({rot}deg);
                    padding:46px 40px;box-sizing:border-box;}}
            .sheet img{{width:100%;display:block;filter:contrast(.94) brightness(.97);}}
            .hand{{margin-top:30px;font-family:"Noto Sans CJK SC",sans-serif;font-size:30px;
                   color:#c0392b;font-style:italic;transform:rotate(-2deg);
                   letter-spacing:1px;opacity:.9;}}
            .hand2{{font-size:22px;color:#e0503c;transform:rotate(1.4deg);margin-top:10px;opacity:.8;}}
            </style>
            <div class="sheet">
              <img src="data:image/png;base64,{b64}">
              <div class="hand">{hand}</div>
              <div class="hand2">过程略 …… {rnd.choice(['再算一遍','公式记错了','这里好像不对'])}</div>
            </div>"""
            pg.set_content(html)
            pg.wait_for_timeout(400)
            out = PHO / f"{q['id']}_photo.jpg"
            pg.screenshot(path=str(out), type="jpeg", quality=58)
            # 模拟"大模型抽指纹"结果：真实使用时这一步由多模态模型完成
            feat = {
                "id": q["id"], "confidence": round(rnd.uniform(0.86, 0.95), 2),
                "numbers": q["numbers"], "formulas": q["formulas"],
                "stem_keywords": q["stem"][:12],
                "detected_write": hand,
            }
            (PHO / f"{q['id']}_photo.features.json").write_text(
                json.dumps(feat, ensure_ascii=False, indent=2), encoding="utf-8")
            print("photo:", out.name)
        b.close()


if __name__ == "__main__":
    meta = render_gallery(None)
    render_photos(None, meta)
    print("done")
