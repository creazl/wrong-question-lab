---
name: wrong-question-organizer
display_name: "错题整理成册"
description: >-
  把错题照片整理成可打印的 A4 错题本。用「图库匹配」替代「去除手写」：先建一份纯净题干图库并生成索引，
  拍照后用多模态模型抽取题干指纹（数值/化学式/关键词），与图库检索比对，命中即取图库原图作为干净题面，
  再合成含"我的错解/正确解/错在哪/复习节奏"的错题卡并输出单题不跨页的 A4 PDF。
  适用于：拍照整理错题、试卷错题归档、生成错题本/错题册、把错题做成可打印 PDF、按知识点或错因归类错题、
  给错题排艾宾浩斯复习节奏、批量整理教材或教辅题目建立图库。
  触发词：错题、错题本、错题整理、错题成册、拍照记错题、组卷打印、错题 PDF、图库匹配。
---

# 错题整理成册

## 这个 skill 解决什么

传统错题整理的死结是"把手写答案从印刷题面上擦掉"——贵、慢、擦不干净，擦不干净就是复习时的二次污染。
本 skill 换一条路：**命中图库就不需要擦**，直接用图库里的纯净原图作为题面。

```
照片 ──(多模态抽指纹)──► 指纹 ──(本地检索打分)──► 候选
                                                  ├ 命中 → 图库原图（干净题面）
                                                  └ 未命中 → 存原照片 + 进补库队列
                                        ↓
                              错题卡 JSON → A4 PDF
```

分工是死的：**模型只负责"看懂照片说了什么"，不负责"猜这是哪道题"**。检索、打分、分页全部走脚本，
因为匹配是可验证的算术，不是可以拍脑袋的文学。

## 工作流

### 阶段 0 · 检查图库（每次任务开头必做）

```bash
ls <gallery>/index.json || python3 scripts/build_index.py --gallery <gallery>
```

- 有 `index.json` → 直接进入阶段 2；图库有新增图片则重跑 `build_index.py`（增量覆盖，幂等）。
- 没有图库 → 先读 `references/gallery-schema.md`，按其中"冷启动"一节建库，再回来。
- 题量为 0 或过小（< 20 题）要主动告诉用户：命中率会很低，此时多数题会退化为"存原照片"。

### 阶段 1 · 抽指纹（唯一的模型环节）

对每张照片输出如下 JSON，字段宁缺勿滥，读不出的留空——**不要编数字**：

```json
{"numbers": ["6 V", "1 Ω"], "formulas": ["R1=2Ω"], "stem_keywords": "电源电动势 内阻 闭合开关", "dhash": "可选"}
```

- `numbers`：题干里出现的所有数值+单位（含角度、系数），这是最硬的指纹。
- `formulas`：化学式、物理量符号、LaTeX 片段。
- `stem_keywords`：题干开头 12–20 个字，原样抄，不要改写、不要概括。
- 照片本身干净（无手写、无歪斜）时可附 `dhash`（见 `references/match-protocol.md`）。

### 阶段 2 · 检索与判定

```bash
python3 scripts/match.py --index <gallery>/index.json --features <probe.json> --out matches.json
```

判定看 `action` 字段，**不要自己改判**：

| action | 分数 | 必须做什么 |
|---|---|---|
| `auto` | ≥ 0.80 | 直接用图库原图，无需问用户 |
| `confirm` | 0.45–0.80 | 把 top1 题干前 20 字念给用户，明确问"是这道吗"，得到确认才用 |
| `reject` | < 0.45 | 不得猜题：保留原照片裁切图作为题面，并提示"未在图库中，建议补库" |

### 阶段 3 · 合成错题卡

把匹配结果与图库元数据合并成 `notebook.json`（用 `scripts/build_notebook.py`）。
错因 `error_type` 与知识点 `knowledge` 必须从 `references/error-taxonomy.md` 的枚举里选，**禁止自由文本**。

### 阶段 4 · 出 PDF

```bash
python3 scripts/render_pdf.py --notebook notebook.json --out 错题本.pdf
```

版式规格见 `references/card-layout.md`。默认 A4、每页最多 3 题、单题不跨页、四角裁切角标、纯白底黑线。

### 阶段 5 · 交付前自检（不通过不许交付）

```bash
python3 scripts/render_pdf.py --notebook notebook.json --out 错题本.pdf --verify
```

必须全绿：单题跨页 = 0、重复题号 = 0、空题面 = 0、知识点不在词表 = 0。
再把第 1 页渲染成图片肉眼过一遍：题面是否清晰、公式有没有丢、标签有没有挤行。

## 铁律

1. **不猜题**。置信不足就走 `confirm` 或 `reject`，宁可让用户说一句话，也不要把错题的题面换成另一道题。
2. **不重画题面**。题面只能来自图库原图或用户原照片，禁止用文字"复述"题目替代图片。
3. **不编数值**。指纹里的数字必须能在照片上指出来。
4. **受控词表**。知识点、错因只能取枚举值，这是后面统计可用的唯一前提。
5. **原图不外传**。试卷图片按用户本地目录处理，不主动上传到公网。

## 文件导览

| 文件 | 什么时候读 |
|---|---|
| `references/gallery-schema.md` | 建图库、改索引字段、冷启动 |
| `references/match-protocol.md` | 调阈值、加视觉指纹、定位误匹配 |
| `references/card-layout.md` | 改版式、改每页题数、改裁切线 |
| `references/error-taxonomy.md` | 定知识点词表、定错因分类 |
| `scripts/build_index.py` | 建/更新索引 |
| `scripts/match.py` | 检索打分 |
| `scripts/build_notebook.py` | 合并成卡片数据 |
| `scripts/render_pdf.py` | 出 PDF + 自检 |
| `assets/card_template.html` | PDF 版式模板（改样式改这里） |
