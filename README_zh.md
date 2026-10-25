<div align="center">

[English](README.md) | [简体中文](README_zh.md)

# EvaOmni：一个证据锚定的音视频推理基准

<a href="https://scholar.google.com/citations?user=zBM8_XkAAAAJ&amp;hl=zh-CN">Xiaoxing Hu</a><sup>†</sup>, <a href="https://openreview.net/profile?id=~Wenxi_Yao1">Wenxi Yao</a><sup>&#42;</sup>, <a href="https://openreview.net/profile?id=~Chaoyuan_Shi1">Chaoyuan Shi</a><sup>&#42;</sup>, <a href="https://scholar.google.com/citations?user=GA0gV5cAAAAJ&amp;hl=zh-CN">Ziqi Ye</a><sup>&#42;</sup>, <a href="https://openreview.net/profile?id=~Xiaorong_Guo1">Xiaorong Guo</a>, <a href="https://openreview.net/profile?id=~Peixuan_Li3">Peixuan Li</a>, <a href="https://openreview.net/profile?id=~Zhuoran_Sun2">Zhuoran Sun</a>, <a href="https://cuzyoung.github.io/ZiyangGong.github.io/">Ziyang Gong</a>, <a href="https://zzppppy.github.io/">Peiyuan Zhang</a>, <a href="https://openreview.net/profile?id=~Mingxin_Liu3">Mingxin Liu</a>, <a href="https://openreview.net/profile?id=~Shuran_Ma1">Shuran Ma</a>, <a href="https://scholar.google.com/citations?user=GcgqbCUAAAAJ&amp;hl=zh-CN">Hongbo Liu</a>, <a href="https://openreview.net/profile?id=~Xiaomin_Yu1">Xiaomin Yu</a>, <a href="https://t1ans1r.github.io/">Yu Tian</a>, <a href="https://scholar.google.com.hk/citations?user=CX-o0V4AAAAJ&amp;hl=zh-CN">Wentao Wang</a>, <a href="https://github.com/jayyoung0802">Zhenjie Yang</a>, <a href="https://lwpyh.github.io/">Jian Hu</a>, <a href="https://shenyunhang.github.io/">Yunhang Shen</a>, <a href="https://scholar.google.com/citations?user=LV8ejn8AAAAJ&amp;hl=zh-CN">Haoyu Cao</a>, and <a href="https://yangxue.site/">Xue Yang</a><sup>✉</sup>

<sup>†</sup> 项目负责人 · <sup>&#42;</sup> 核心贡献 · <sup>✉</sup> 通讯作者

<p>
  <a href="https://modelscope.cn/datasets/VisionXLab/EvaOmni-Dataset"><img src="https://img.shields.io/badge/ModelScope-Dataset-624AFF?style=flat" alt="ModelScope Dataset"></a>
  <a href="https://huggingface.co/datasets/VisionXLab/EvaOmni-Dataset"><img src="https://img.shields.io/badge/Hugging%20Face-Dataset-FFD21E?style=flat&logo=huggingface" alt="Hugging Face Dataset"></a>
  <a href="https://arxiv.org/pdf/2610.28444"><img src="https://img.shields.io/badge/arXiv-2610.28444-B31B1B?style=flat&logo=arxiv&logoColor=white" alt="arXiv: 2610.28444"></a>
  <a href="https://xiaoxing2001.github.io/EvaOmni.github.io/"><img src="https://img.shields.io/badge/Project-Homepage-007EC6?style=flat" alt="Project Homepage"></a>
</p>

**如果 EvaOmni 对你的研究有帮助，欢迎为我们点一个 Star 并引用我们的工作！ ⭐⭐⭐**

</div>

## 📖 动机与概述

EvaOmni 是一个用于评估全模态大模型音视频推理能力的**证据锚定**基准。现有多选题基准通常只判断模型是否选对了选项，因此模型可能依靠文本、逻辑或单一模态的"捷径"得分，却无法指出支撑其答案的证据。EvaOmni 要求模型同时给出答案，以及带时间戳的音频证据与视觉证据。基准在报告答案准确率之外，还报告证据覆盖率与时间定位质量，从而衡量"正确答案"是否真的建立在两个模态中对应的关键时刻之上。

<p align="center">
  <img src="assets/shortcut.png" width="100%" alt="各基准上的捷径评估，以及文本、音频、视觉捷径示例">
</p>

*各基准上的捷径评估，以及纯文本、纯音频、纯视觉捷径的示例。*

## ✨ 亮点

- **证据锚定评测：** 模型同时输出答案与音频、视觉证据区间。
- **音视频推理：** 问题的设计要求模型综合两个模态的互补信息才能作答。
- **捷径筛查：** 数据构建阶段包含纯文本、纯音频、纯视觉的对照检查。
- **细粒度分类体系：** 来自 392 个视频的 1,027 道问题，覆盖 3 个推理等级下的 15 项能力。
- **锚定指标：** 覆盖率锚定得分（Coverage Grounded Score, C.G.）衡量证据覆盖程度；瓶颈锚定得分（Bottleneck Grounded Score, B.G.）取两个模态定位得分中较低者。
- **评测过程透明：** 本次发布包含可运行的指标评测器、Gemini 与 MiMo 适配脚本、预测结果格式规范以及完整示例。

<p align="center">
  <img src="assets/example.png" width="100%" alt="EvaOmni 标注流程，以及一个带时间戳音视频证据的示例">
</p>

*标注流程，以及一个带时间戳音频与视觉证据的锚定问题示例。*

## 📊 基准统计

| 项目 | 数值 |
|---|---:|
| 视频数 | 392 |
| 问答对 | 1,027 |
| 细粒度能力 | 15 |
| 推理等级 | 3 |
| 视频时长 | 1–12 分钟 |
| 评测帧率 | 1.0 FPS |
| 评测分辨率 | 长边 480 像素 |

<p align="center">
  <img src="assets/distribution.png" width="100%" alt="能力分类体系，以及视频时长、token 长度、证据和视频类别的分布">
</p>

*能力分类体系与数据集统计，包括视频时长、token 长度、证据和视频类别分布。*

### 能力等级

- **等级 1 —— 检索与锚定：** 时间对齐、事件绑定、实体绑定。
- **等级 2 —— 基础理解：** 因果推理、情绪理解、意图理解、氛围理解、隐含事件推理、语义消歧、时间理解、空间理解、条件计数。
- **等级 3 —— 复杂推理：** 多跳推理、长程推理、多证据链。

## 🔥 基准表现

当前论文评测了 **7 个开源全模态模型与 17 个闭源全模态模型**，并给出人类专家参考基线。下表报告三个能力等级以及总体的 Acc.、C.G. 与 B.G.。所有数值均为百分比，越高越好。在每个模型分组内，**加粗**表示最佳结果，<ins>下划线</ins>表示次佳结果。以下为论文结果，并非本仓库代码运行产出。

<table>
  <thead>
    <tr>
      <th rowspan="2">模型</th>
      <th colspan="3">等级 1 R.&amp;G.</th>
      <th colspan="3">等级 2 B.U.</th>
      <th colspan="3">等级 3 C.R.</th>
      <th colspan="3">总体</th>
    </tr>
    <tr><th>Acc.</th><th>C.G.</th><th>B.G.</th><th>Acc.</th><th>C.G.</th><th>B.G.</th><th>Acc.</th><th>C.G.</th><th>B.G.</th><th>Acc.</th><th>C.G.</th><th>B.G.</th></tr>
  </thead>
  <tbody>
    <tr><th colspan="13">开源 Omni 大模型</th></tr>
    <tr><td>Qwen2.5-Omni-7B</td><td align="right">16.6</td><td align="right">1.2</td><td align="right">0.6</td><td align="right">17.4</td><td align="right">0.5</td><td align="right">0.0</td><td align="right">13.7</td><td align="right">0.3</td><td align="right">0.0</td><td align="right">16.4</td><td align="right">0.8</td><td align="right">0.3</td></tr>
    <tr><td>Qwen3-Omni-Instruct-30B-A3B</td><td align="right">28.6</td><td align="right">5.1</td><td align="right">0.6</td><td align="right">22.4</td><td align="right">3.4</td><td align="right">0.4</td><td align="right">22.2</td><td align="right">2.4</td><td align="right">0.1</td><td align="right">25.2</td><td align="right">4.0</td><td align="right">0.4</td></tr>
    <tr><td>Qwen3-Omni-Thinking-30B-A3B</td><td align="right">26.3</td><td align="right">11.4</td><td align="right">4.8</td><td align="right">24.4</td><td align="right">6.2</td><td align="right">1.2</td><td align="right">21.6</td><td align="right">4.1</td><td align="right">0.6</td><td align="right">24.8</td><td align="right">8.3</td><td align="right">2.8</td></tr>
    <tr><td>Nemotron3-Nano-Omni-30B-A3B</td><td align="right">30.7</td><td align="right">15.0</td><td align="right">5.3</td><td align="right">22.1</td><td align="right">13.1</td><td align="right">3.9</td><td align="right">10.5</td><td align="right">4.7</td><td align="right">0.7</td><td align="right">24.2</td><td align="right">12.6</td><td align="right">4.0</td></tr>
    <tr><td>MiMo-V2.5-310B-A15B</td><td align="right"><strong>65.4</strong></td><td align="right"><strong>61.3</strong></td><td align="right"><strong>30.8</strong></td><td align="right"><strong>52.3</strong></td><td align="right"><strong>42.3</strong></td><td align="right"><strong>15.1</strong></td><td align="right">45.1</td><td align="right"><strong>29.6</strong></td><td align="right"><strong>6.7</strong></td><td align="right"><strong>56.8</strong></td><td align="right"><strong>48.4</strong></td><td align="right"><strong>20.5</strong></td></tr>
    <tr><td>MiMo-V2.6-Flash-310B-A15B</td><td align="right"><ins>61.3</ins></td><td align="right"><ins>55.3</ins></td><td align="right"><ins>29.0</ins></td><td align="right"><ins>48.6</ins></td><td align="right"><ins>41.4</ins></td><td align="right"><ins>14.5</ins></td><td align="right"><ins>45.8</ins></td><td align="right"><ins>28.6</ins></td><td align="right"><ins>5.9</ins></td><td align="right"><ins>53.6</ins></td><td align="right"><ins>45.3</ins></td><td align="right"><ins>19.3</ins></td></tr>
    <tr><td>MiMo-V2.6-Pro-1T-A42B</td><td align="right">60.1</td><td align="right">51.3</td><td align="right">28.8</td><td align="right">44.3</td><td align="right">35.2</td><td align="right">12.0</td><td align="right"><strong>49.7</strong></td><td align="right">26.6</td><td align="right">5.0</td><td align="right">51.8</td><td align="right">40.7</td><td align="right">18.1</td></tr>
    <tr><th colspan="13">闭源 Omni 大模型</th></tr>
    <tr><td>Doubao-Seed-2.0-Lite</td><td align="right">54.1</td><td align="right">36.4</td><td align="right">10.8</td><td align="right">54.1</td><td align="right">36.1</td><td align="right">11.7</td><td align="right">62.7</td><td align="right">32.2</td><td align="right">5.9</td><td align="right">55.4</td><td align="right">35.6</td><td align="right">10.4</td></tr>
    <tr><td>Doubao-Seed-2.1-Lite</td><td align="right">78.8</td><td align="right">74.8</td><td align="right">38.0</td><td align="right">67.0</td><td align="right">61.5</td><td align="right">22.6</td><td align="right">59.5</td><td align="right">42.7</td><td align="right">9.4</td><td align="right">70.9</td><td align="right">64.3</td><td align="right">27.2</td></tr>
    <tr><td>Qwen3.5-Omni-Flash</td><td align="right">47.5</td><td align="right">41.9</td><td align="right">15.5</td><td align="right">30.9</td><td align="right">24.0</td><td align="right">7.2</td><td align="right">29.4</td><td align="right">15.7</td><td align="right">2.7</td><td align="right">37.7</td><td align="right">30.4</td><td align="right">10.0</td></tr>
    <tr><td>Qwen3.5-Omni-Plus</td><td align="right">58.1</td><td align="right">52.0</td><td align="right">22.1</td><td align="right">42.3</td><td align="right">26.0</td><td align="right">8.6</td><td align="right">42.5</td><td align="right">19.8</td><td align="right">3.3</td><td align="right">49.0</td><td align="right">36.0</td><td align="right">13.5</td></tr>
    <tr><td>Qwen3.8-Omni-Flash</td><td align="right">65.0</td><td align="right">53.6</td><td align="right">19.3</td><td align="right">52.3</td><td align="right">41.4</td><td align="right">11.8</td><td align="right">56.2</td><td align="right">35.9</td><td align="right">7.8</td><td align="right">58.2</td><td align="right">45.7</td><td align="right">14.4</td></tr>
    <tr><td>Gemini2.5-Flash</td><td align="right">59.2</td><td align="right">55.2</td><td align="right">26.7</td><td align="right">39.3</td><td align="right">31.4</td><td align="right">11.8</td><td align="right">41.8</td><td align="right">24.6</td><td align="right">4.0</td><td align="right">48.1</td><td align="right">40.4</td><td align="right">16.9</td></tr>
    <tr><td>Gemini2.5-Flash-Lite</td><td align="right">53.0</td><td align="right">47.2</td><td align="right">22.1</td><td align="right">30.9</td><td align="right">22.4</td><td align="right">8.0</td><td align="right">27.5</td><td align="right">14.8</td><td align="right">2.2</td><td align="right">39.7</td><td align="right">31.8</td><td align="right">13.1</td></tr>
    <tr><td>Gemini2.5-Pro</td><td align="right">76.5</td><td align="right">73.8</td><td align="right">42.3</td><td align="right">65.0</td><td align="right">55.0</td><td align="right">22.5</td><td align="right">72.5</td><td align="right">45.8</td><td align="right">9.4</td><td align="right">71.0</td><td align="right">61.6</td><td align="right">28.9</td></tr>
    <tr><td>Gemini3.1-Flash-Lite</td><td align="right">59.4</td><td align="right">52.8</td><td align="right">24.2</td><td align="right">36.6</td><td align="right">30.7</td><td align="right">10.5</td><td align="right">32.0</td><td align="right">19.0</td><td align="right">3.0</td><td align="right">45.6</td><td align="right">38.3</td><td align="right">15.2</td></tr>
    <tr><td>Gemini3.1-Flash-Lite-Preview</td><td align="right">59.7</td><td align="right">53.6</td><td align="right">25.2</td><td align="right">39.3</td><td align="right">31.1</td><td align="right">10.3</td><td align="right">38.6</td><td align="right">23.2</td><td align="right">3.3</td><td align="right">47.8</td><td align="right">39.4</td><td align="right">15.6</td></tr>
    <tr><td>Gemini3.1-Pro-Preview</td><td align="right">74.7</td><td align="right">72.8</td><td align="right">41.5</td><td align="right">68.6</td><td align="right">59.8</td><td align="right">24.8</td><td align="right">76.5</td><td align="right"><ins>48.7</ins></td><td align="right">11.2</td><td align="right">72.3</td><td align="right">63.7</td><td align="right">29.8</td></tr>
    <tr><td>Gemini3.5-Flash</td><td align="right">64.1</td><td align="right">59.4</td><td align="right">28.8</td><td align="right">69.5</td><td align="right">61.4</td><td align="right"><ins>27.4</ins></td><td align="right"><ins>77.8</ins></td><td align="right">47.8</td><td align="right"><ins>11.3</ins></td><td align="right">68.5</td><td align="right">58.6</td><td align="right">25.6</td></tr>
    <tr><td>Gemini3.5-Flash-Lite</td><td align="right">60.6</td><td align="right">55.6</td><td align="right">26.5</td><td align="right">38.2</td><td align="right">27.9</td><td align="right">10.7</td><td align="right">42.5</td><td align="right">24.2</td><td align="right">3.5</td><td align="right">48.3</td><td align="right">39.1</td><td align="right">16.3</td></tr>
    <tr><td>Gemini3.6-Flash</td><td align="right">80.9</td><td align="right">78.0</td><td align="right">44.7</td><td align="right">68.4</td><td align="right">61.3</td><td align="right">26.1</td><td align="right">73.2</td><td align="right">44.2</td><td align="right">10.6</td><td align="right">74.4</td><td align="right">65.8</td><td align="right">31.7</td></tr>
    <tr><td>Gemini3.7-Flash</td><td align="right"><strong>85.3</strong></td><td align="right"><strong>84.0</strong></td><td align="right"><strong>49.1</strong></td><td align="right"><ins>73.6</ins></td><td align="right"><strong>65.3</strong></td><td align="right"><strong>29.2</strong></td><td align="right"><strong>79.1</strong></td><td align="right"><strong>49.1</strong></td><td align="right"><strong>12.3</strong></td><td align="right"><strong>79.4</strong></td><td align="right"><strong>70.8</strong></td><td align="right"><strong>35.1</strong></td></tr>
    <tr><td>Gemini3.8-Flash</td><td align="right"><ins>83.4</ins></td><td align="right"><ins>81.9</ins></td><td align="right"><ins>48.4</ins></td><td align="right"><strong>73.9</strong></td><td align="right"><ins>63.3</ins></td><td align="right"><ins>27.4</ins></td><td align="right">74.5</td><td align="right">43.1</td><td align="right">9.5</td><td align="right"><ins>78.0</ins></td><td align="right"><ins>68.2</ins></td><td align="right"><ins>33.6</ins></td></tr>
    <tr><td>Gemini4-Argon</td><td align="right">67.1</td><td align="right">55.9</td><td align="right">29.3</td><td align="right">52.0</td><td align="right">33.7</td><td align="right">13.0</td><td align="right">72.5</td><td align="right">33.5</td><td align="right">7.5</td><td align="right">61.4</td><td align="right">43.0</td><td align="right">19.1</td></tr>
    <tr><th colspan="13">参考基线</th></tr>
    <tr><td>人类专家</td><td align="right">97.8</td><td align="right">97.8</td><td align="right">95.8</td><td align="right">96.5</td><td align="right">94.8</td><td align="right">93.2</td><td align="right">94.4</td><td align="right">93.8</td><td align="right">93.0</td><td align="right">96.8</td><td align="right">96.0</td><td align="right">94.3</td></tr>
  </tbody>
</table>

Gemini3.7-Flash 的总体准确率达到 79.4%，但 B.G. 仅为 35.1%。这一差距说明答案正确性与证据定位能力需要放在一起评估。需注意，人类专家基线允许暂停与回放视频，其观看条件与模型推理并不相同。

## 📦 数据集

数据集分别托管在 Hugging Face 与 ModelScope 上，任选其一即可：[ModelScope](https://modelscope.cn/datasets/VisionXLab/EvaOmni-Dataset) 或 [Hugging Face](https://huggingface.co/datasets/VisionXLab/EvaOmni-Dataset)：

- [ModelScope: VisionXLab/EvaOmni-Dataset](https://modelscope.cn/datasets/VisionXLab/EvaOmni-Dataset)
- [Hugging Face: VisionXLab/EvaOmni-Dataset](https://huggingface.co/datasets/VisionXLab/EvaOmni-Dataset)

下载命令：

```bash
pip install modelscope
modelscope download --dataset VisionXLab/EvaOmni-Dataset --local_dir ./data
```

或者

```bash
pip install huggingface_hub
huggingface-cli download --repo-type dataset --resume-download VisionXLab/EvaOmni-Dataset --local-dir ./data
```

> [!NOTE]
> 复现论文结果请使用 **`resized_video`**；如果需要自定义预处理，请使用 **`rawvideo`**（原始视频）。

## 🚀 快速开始

克隆仓库：

```bash
git clone https://github.com/VisionXLab/EvaOmni.git
cd EvaOmni
```

### 1. 下载数据集

使用上面的任一命令下载数据集，得到的目录结构如下：

```text
data/
├── test_file.json
├── rawvideo/
│   ├── 001.mp4
│   ├── 002.mp4
│   └── ...
└── resized_video/
    ├── 001.mp4
    ├── 002.mp4
    └── ...
```

### 2. 选择适配脚本并运行评测

每个模型家族在 [`scripts/`](scripts/) 下都有独立适配脚本。所有脚本都从环境变量读取同样的三个配置项，代码中不硬编码任何凭据，`API_KEY` 也不会写入输出文件。可以把 [`.env.example`](.env.example) 复制为 `.env`（该文件已被 git 忽略）后填写，或者在当前 shell 中直接 export。

| 适配脚本 | 协议 | 支持的模型 |
|---|---|---|
| [`scripts/eval_gemini.py`](scripts/eval_gemini.py) | Gemini `generateContent` REST | Gemini 系列，如 `gemini-3.8-flash` |
| [`scripts/eval_mimo.py`](scripts/eval_mimo.py) | OpenAI 兼容的 chat completions | MiMo 系列，如 `mimo-v2.6-pro`、`mimo-v2.6-flash` |

通用环境变量：

| 变量 | 含义 |
|---|---|
| `BASE_URL` | 接口地址。各脚本支持的形式见下文说明。 |
| `API_KEY` | 服务商的 API key。Gemini 脚本以 `Authorization: Bearer` 发送，MiMo 脚本通过 OpenAI SDK 传入。 |
| `MODEL_NAME` | 传给服务商的模型标识。 |

> [!NOTE]
> MiMo-v2.5 已不再由官方 API 提供。请使用 `mimo-v2.6-pro` 或 `mimo-v2.6-flash`。

#### Gemini 系列

`BASE_URL` 支持两种写法：一种是前缀，脚本会自动在其后拼接 `/${MODEL_NAME}:generateContent`；另一种是包含 `{model}` 占位符的完整模板，脚本会原样替换后使用：

```bash
# 写法一：前缀形式，脚本自动补 /<model>:generateContent
export BASE_URL="https://<your-host>/v1beta/models"

# 写法二：模板形式，适用于路径不同的中转服务
export BASE_URL="https://<your-host>/v1beta/models/{model}:generateContent"
```

```bash
export BASE_URL="https://<your-host>/v1beta/models"
export API_KEY="<your-api-key>"
export MODEL_NAME="gemini-3.8-flash"

python scripts/eval_gemini.py \
  --annotation data/test_file.json \
  --video-root data/resized_video \
  --results-dir outputs/gemini \
  --workers 4 \
  --retries 3
```

脚本启动时会打印**解析后的真实请求地址**，因此中转路径配置错误在上传任何视频之前就能被发现。封装脚本 [`scripts/eval.sh`](scripts/eval.sh) 执行同样的命令，并支持通过 `ANNOTATION_FILE`、`VIDEO_ROOT`、`RESULTS_DIR`、`WORKERS`、`RETRIES`、`LIMIT` 覆盖默认值：

```bash
MODEL_NAME="gemini-3.8-flash" bash scripts/eval.sh
```

#### MiMo 系列

`BASE_URL` 填 OpenAI 兼容接口的 base 地址，通常以 `/v1` 结尾。视频以 base64 data URL 内联发送，无需单独上传。

```bash
export BASE_URL="https://<your-host>/v1"
export API_KEY="<your-api-key>"
export MODEL_NAME="mimo-v2.6-flash"

python scripts/eval_mimo.py \
  --annotation data/test_file.json \
  --video-root data/resized_video \
  --results-dir outputs/mimo \
  --workers 4 \
  --retries 3
```

把 `MODEL_NAME` 换成 `mimo-v2.6-pro` 即可评测 Pro 版本。不同模型请使用不同的 `--results-dir`，避免断点文件互相混淆；也可以在同目录下用 `--tag mimo_pro` 区分。`--fps` 控制发送给服务商的抽帧率，默认 `1.0`，与基准评测协议一致。

#### 冒烟测试

两个脚本都支持 `--limit N`，只评测前 N 道题。请把结果指向单独的目录，避免这次不完整的运行被误当作完整断点：

```bash
MODEL_NAME="mimo-v2.6-flash" python scripts/eval_mimo.py --limit 5 --results-dir outputs/smoke
MODEL_NAME="gemini-3.8-flash" python scripts/eval_gemini.py --limit 5 --results-dir outputs/smoke
```

也可以用 `--qa-ids 1,2,3` 指定具体题目，或用 `--levels 1,2` 指定推理等级。

#### 断点续跑与输出

两个脚本都会实时显示进度，并逐条保存已完成的结果。重跑同一条命令即可续跑：成功的题目会被跳过，失败的题目会重试。即使某道题被尝试多次，汇总统计中也只按一道题计入。原始响应与可读日志都保存在结果目录中。

> **TODO：** 论文中评测的其余模型家族（Qwen-Omni、Nemotron-Omni、Doubao-Seed，以及本地 vLLM 推理流程）的适配脚本将逐步开源。

如需自行适配其他服务商，或想在不发网络请求的情况下检查整条流程，请参考 [`scripts/eval_example.py`](scripts/eval_example.py)。该示例支持 `--mock --limit 8`，可在不访问网络的情况下生成锚定指标快照。

## 📚 引用

```bibtex
@article{hu2026evaomni,
  title={EvaOmni: An Evidence-Grounded Benchmark for Audio-Visual Reasoning},
  author={Hu, Xiaoxing and Yao, Wenxi and Shi, Chaoyuan and Ye, Ziqi and Guo, Xiaorong and Li, Peixuan and Sun, Zhuoran and Gong, Ziyang and Zhang, Peiyuan and Liu, Mingxin and Ma, Shuran and Liu, Hongbo and Yu, Xiaomin and Tian, Yu and Wang, Wentao and Yang, Zhenjie and Hu, Jian and Shen, Yunhang and Cao, Haoyu and Yang, Xue},
  journal={arXiv preprint arXiv:2610.28444},
  year={2026}
}
```

## 📄 许可证

仓库代码以 [MIT 许可证](LICENSE) 发布。数据集标注与媒体素材的使用条款，请参阅[数据集托管页面](https://huggingface.co/datasets/VisionXLab/EvaOmni-Dataset)。

## 🙏 致谢

感谢所有标注者、审稿人以及开源社区，是你们的工作让这个基准得以完成。如果发现失效链接、标注问题或评测结果不一致，欢迎提交 issue。
