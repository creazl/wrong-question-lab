# 图库规范（gallery-schema）

> 图库不是文件夹，是带索引的资产。没有 `index.json` 的图库对本 skill 等同于不存在。

## 目录结构

```
gallery/
├── index.json            # 检索唯一入口，脚本生成，不手改
├── meta.json             # 人工维护的题目元数据（源数据）
├── 化学/
│   ├── q_hx_0001.png
│   └── q_hx_0002.png
└── 物理/
    └── q_wl_0001.png
```

- 图片必须是**纯净题干**：无手写、无阴影、无手指、正拍（倾斜 < 2°）。
- 命名 `q_<学科两字母>_<四位序号>.png`，学科码：`hx` 化学 / `wl` 物理 / `sx` 数学 / `yw` 语文 / `yy` 英语 / `sw` 生物。
- 分辨率宽带 ≥ 1200px，格式 PNG（PDF 里 JPEG 压缩会让白底发灰）。

## meta.json 字段

```json
[{
  "id": "q_hx_0001",
  "subject": "化学",
  "chapter": "物质结构与性质",
  "knowledge": ["化学键/键角", "VSEPR"],
  "stem_text": "下列分子中，键角最大的是",
  "fingerprint": {"numbers": ["104.5°", "180°"], "formulas": ["H2O", "CH4", "CO2"]},
  "answer": "D",
  "my_answer": "答案：C",
  "error_type": "K01",
  "why": "把 CH4 的 109°28′ 当最大，忽略了 CO2 直线型的 180°",
  "source": {"book": "必修二", "page": 88},
  "img": "化学/q_hx_0001.png"
}]
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | ✓ | 全局唯一，PDF 上会印出来，重命名等于换题 |
| `subject` | ✓ | 中文全称，用于筛选与分册 |
| `knowledge` | ✓ | 取 `error-taxonomy.md` 的受控词表，可多个 |
| `stem_text` | ✓ | 题干纯文本，供文本相似度；**不填则文本项恒 0** |
| `fingerprint.numbers` | ✓ | 数值+单位，带符号原样抄 |
| `fingerprint.formulas` | ✓ | 化学式/物理量/LaTeX 片段 |
| `answer` | ✓ | 标准答案，可含简短解析 |
| `my_answer` | 空 | 当时写错的答案，复习对照用 |
| `error_type` | ✓ | K01–K05 枚举 |
| `why` | 空 | 一句话错因说明 |
| `source` | 空 | `book/paper` + `page` |
| `img` | ✓ | 相对 gallery 的路径 |

## index.json（脚本产物）

在 meta 每条基础上追加：

```json
{"gallery":"gallery","count":6,"hash_size":10,
 "items":[{...,"dhash":"c3e1f0...","w":1500,"h":260}]}
```

`dhash` 是 10×10 的差分哈希，容忍缩放与小角度旋转 ≤ 3°，但**不承担主检索职责**，只做加分与去重。

## 冷启动：三小时建出可用的图库

按性价比排序，别一上来就想全：

1. **教材/教辅 PDF 切图**（首选）：按页渲染 → 按题目边界切 → 批量写 meta（`stem_text` 可先留空，只填 numbers/formulas）。
   300–500 题足够覆盖当前学期，命中率约 60%–75%。
2. **旧错题照片回流**：只回流"照片本身干净"的；带手写的必须重拍，否则等于把脏数据存进图库。
3. **边用边补**：每次 `reject` 的题，问用户一句"要不要现在补进图库"，补完重跑 `build_index.py`。

## 建索引

```bash
python3 scripts/build_index.py --gallery /path/to/gallery
```

幂等：重复运行只覆盖 `index.json`，不动图片与 meta。新增图片后必须重跑，否则检索看不到。
