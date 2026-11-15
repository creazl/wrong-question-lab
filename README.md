# 错题整理实验台 · wrong-question-lab

同一套"图库匹配"内核，三种交付形态跑通后的对照实验：**Skill / 网页应用 / 手机应用（PWA）**。

核心主张：错题整理最难的一步不是识别，而是"把手写答案从印刷题面上擦掉"。
本仓库绕开这一步——**照片只用来抽指纹，命中的题目直接取图库里的纯净原图当作题面**。

```
照片 ──(多模态抽指纹)──► 指纹 ──(本地检索打分)──► 候选 ──► 错题卡 ──► A4 PDF
```

## 三个形态

| 形态 | 目录 | 运行方式 | 当前状态 |
|---|---|---|---|
| **Skill** | `skill/wrong-question-organizer/` | 在 Agent 里说"整理这些错题"，跑脚本出 PDF | ✅ 全链路通过（含自检） |
| **网页应用** | `web/index.html` | 双击打开，零后端、零依赖 | ✅ 端到端通过（6 题入库、打印 A4） |
| **手机应用** | `app/index.html` | PWA：`manifest` + `serviceWorker`，可添加到主屏 | ✅ 端到端通过（390×844 移动视口） |

三者共用同一份数据与同一套打分公式（Python 与前端 JS 权重完全一致：`0.45 数值 + 0.30 公式 + 0.20 文本 + 0.05 视觉`）。

## 快速开始

```bash
pip install pillow imagehash
# 1. 造演示数据：印刷体题面 + 模拟"手机拍摄"照片（歪斜/红笔/JPEG 压缩）
python3 tools/make_demo.py
# 2. 建索引
python3 skill/wrong-question-organizer/scripts/build_index.py --gallery demo/gallery
# 3. 匹配
python3 skill/wrong-question-organizer/scripts/match.py \
    --index demo/gallery/index.json --features-dir demo/photos --out demo/output/matches.json
# 4. 合成卡片
python3 skill/wrong-question-organizer/scripts/build_notebook.py \
    --matches demo/output/matches.json --gallery demo/gallery --out demo/output/notebook.json
# 5. 出 PDF（带四项硬自检）
python3 skill/wrong-question-organizer/scripts/render_pdf.py \
    --notebook demo/output/notebook.json --out demo/output/错题本-演示.pdf --verify
# 6. 生成两个前端
python3 tools/build_frontend.py
# 7. 端到端回归（截图 + PDF + JS 报错检查）
python3 tools/e2e_check.py
```

## 目录

```
wrong-question-lab/
├── skill/wrong-question-organizer/   # 可安装的 Skill（SKILL.md + references + scripts + assets）
├── web/index.html                    # 网页版：单文件，数据内联（构建产物，不入仓）
├── app/                              # PWA 版：index.html + manifest + sw.js（构建产物）
├── demo/gallery/                     # 图库：6 道示范题的印刷体题面 + meta.json
├── demo/photos/                      # 模拟手机拍摄的"脏照片" + 预置指纹
├── demo/output/                      # 实测产物：matches / notebook / 错题本 PDF（不入仓）
├── tools/                            # 造数据、打包前端、端到端回归
└── docs/                             # 方案对比与实测报告
```

> `web/`、`app/`、`demo/output/`、`demo/gallery/img/`、`demo/photos/*.jpg` 都是可由脚本重建的产物，
> 已写入 `.gitignore`；克隆后跑一遍上面的 1–7 步即可全部生成。

## 实测（详见 `docs/实测报告.md`）

- 匹配命中率 **6/6 = 100%**，分数区间 0.784–0.950，其中 3 题落在 `confirm`（0.45–0.80）需人工点确认。
- PDF 自检 4 项全 0；负向测试（故意塞入词表外标签 + 空题面）能正确 FAIL。
- 网页/PWA 端到端：6 题全部入库，JS 报错 0，打印产出 A4 单题不跨页。
- 全链路耗时 3.6s（建索引 0.33 / 匹配 0.09 / 合卡 0.66 / 出 PDF 2.55）。

## 已知边界（不装懂）

1. **照片识别这一步是模拟的**：演示用的指纹由 `tools/make_demo.py` 预先生成，真实使用时由多模态模型完成（本仓库不内置 API Key）。
2. **图库是瓶颈**：图库没建起来时命中率接近 0，题目会退化为"存原照片"。这是方案本身的成本，不是 bug。
3. **复习调度未实现**：PDF 上印出了 1/2/4/7/15/30 天节奏，但没有调度器与提醒。
4. 数学公式按 HTML 排版（`<sup>/<sub>`），未接 LaTeX 渲染。

## 参考

- 同类开源实现 [`wttwins/wrong-notebook`](https://github.com/wttwins/wrong-notebook)（Next.js + Prisma + SQLite，MIT，853 star）。
  它走"AI 去手写 + 知识点挂课标树 + 三态复习调度"，本仓库走"图库匹配"，两者的取舍见 `docs/方案对比.md`。
- Skill 结构遵循 Anthropic Agent Skills 的 progressive disclosure 约定（`SKILL.md` 轻量、细节进 `references/`、确定性逻辑进 `scripts/`）。

MIT License.
