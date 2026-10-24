# zh-ipi-bench

[English](README.md) · **简体中文**

[![tests](https://github.com/JiachengWu591/zh-ipi-bench/actions/workflows/tests.yml/badge.svg)](https://github.com/JiachengWu591/zh-ipi-bench/actions/workflows/tests.yml)
[![code: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![data: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-lightgrey.svg)](DATA_LICENSE.md)

*一个面向中文的间接提示注入（indirect prompt injection）基准：指令被藏在 LLM 应用当作“数据”读取的文档、网页、邮件和工具输出里。*

> **状态：v0.1，研究产物。** 单人作者、模板生成的数据、尚无第二标注者。下文每个数字都由
> `python -m zhipi.verify` 从已提交的结果行离线复现；[技术报告](paper/REPORT.md)（英文）
> 说明了每项结果能证明什么、不能证明什么。数据集在 Hugging Face：
> [JiachengWu591/zh-ipi-bench](https://huggingface.co/datasets/JiachengWu591/zh-ipi-bench)
> （配置 `v0`、`v1`、`v2`；数据集卡源文件：[release/DATASET_CARD.md](release/DATASET_CARD.md)）。
>
> 说明：本页是 [README.md](README.md) 的中文翻译；仓库内其余文档（报告、数据卡等）为英文。两者不一致时以英文版为准。

## 为什么做这个

公开的间接注入基准几乎都是英文的。我找到的少数多语言或中文资源，涵盖的是直接越狱或内容安全，
而不是植入在应用上下文里的注入（见 [docs/RELATED_WORK.md](docs/RELATED_WORK.md)，其中也列出了
我无法核实的部分）。中文文本有英文所没有的规避途径——全角字符、字符之间插入零宽字符、中英夹杂、
拼音、繁简混用——针对英文调好的防御对它们的表现可能不同，也可能相同。本项目的目的是把这件事
测出来，而不是假设。

它是 [injection-blast-radius](https://github.com/JiachengWu591/injection-blast-radius) 的配套项目。
后者的论点是：随着攻击变得更聪明，真正不会退化的防御层是架构隔离，而不是提示词层面的过滤。
这里要回答的是：*概率性*的防御层在中文输入上是否退化，以及*结构性*的防御层是否依然成立。

## 研究问题

1. 同一个意图，从英文载荷换成中文，防御的检出率如何变化？哪些变换（transform）造成了变化？
2. 防御对良性中文文本有什么影响（讨论注入的文本、对人下达祈使句的文本、提到配置的文本）？
3. 当概率性层被绕过时，基于 schema 约束的隔离是否仍能挡住中文注入？

详情：[docs/THREAT_MODEL.md](docs/THREAT_MODEL.md)。

## 结果速览

**一句话版。** 面对中文间接注入，只有强 LLM 评判器（检出 97%，误报 2%）和一个小型多语言分类器
（80% / 13%）勉强可用；其余现成检测器要么几乎把所有文本都标为注入，要么几乎什么都没发现。
我尝试的中文特有混淆，对能正常工作的检测器没有产生可测量的影响。在架构层面，一个“绝不让
不可信文本决定动作”的流水线（并绕过了它自带的审计步骤）在 239 次运行中一次也没有泄漏植入的
假密钥，而没有防护的弱本地模型泄漏率为 11%。

![左图：六个检测器在 v1 上的检出率与误报率。右图：无防护智能体与隔离流水线在三种端到端设置下的攻击成功率。](assets/results.svg)

*图由 `python -m zhipi.figure` 从已提交的结果行生成，并由 `python -m zhipi.verify` 校验。须线为
95% Wilson 区间；样本和运行被当作相互独立，因此区间比真实不确定性偏窄。图内文字为英文。*

| 问题 | 结论（v1 / v2 数据；区间见各报告） |
|---|---|
| 检测器在中文间接注入上有效吗？ | 强 LLM 评判器：检出 97%，误报 2%。小型多语言分类器：80% / 13%。某社区分类器把**所有文本**都标为注入；某纯英文分类器把 **55%** 的良性文本标为注入。 |
| H1：中文特有的变换会削弱检测吗？ | 对两个能正常工作的检测器**不成立**（全角、零宽、空格拆分、中英夹杂：均无可测量的影响）。检出*率*上的语言差距（97% 对 81%）主要是阈值校准问题（AUROC 0.97 对 0.94）。把载荷埋进长文档确实有影响（AUROC 0.94 → 0.89）。 |
| H2：良性的“长得像” | 难例负样本能区分出只看检出率分不出的检测器（例如请求*真人*粘贴自己的配置）。 |
| H3：隔离能挡住注入吗？ | 绕过审计后，隔离流水线在 **239 次中 0 次** 泄漏植入的假密钥。强模型上无防护基线几乎不泄漏（2%），隔离能阻止的东西很少；换成弱本地模型（Qwen2.5-7B），基线在 **717 次中泄漏 81 次（11%）**。 |

没有展示的内容：无防护基线上的语言效应、任何关于真实攻击分布的结论，或边界不可被突破。
表格：[`results/`](results/)。完整说明：[`paper/REPORT.md`](paper/REPORT.md)。

## 复现表格（无需模型、密钥或网络）

```bash
uv venv && uv pip install -e ".[dev]"
python -m zhipi.verify        # 重建数据、重新生成所有表格和图，并与已提交文件比对
```

## 目录结构

```
src/zhipi/
  schemas.py      frozen dataclass：Intent、Sample（带校验，失败即拒绝）
  transforms.py   fullwidth · zero_width · space_split · code_mix   （更多计划中）
  carriers.py     5 种良性载体：issue · rag_doc · email · web_html · tool_output
  build.py        意图 × 载体 × 变换（+ 良性对照）-> JSONL
  defenses.py     Defense 协议、失败即拒绝的包装、关键词基线
  evaluate.py     运行一个防御，按组汇总并给出 95% Wilson 区间
  adapters/       prompt_guard · qwen3guard · deepseek_judge · ibr_adapter · ibr_e2e ·
                  openai_compat（每个检测器都是一个 Defense；ibr_e2e 是端到端的受害端）
  cache.py        仅追加的响应缓存（失败的响应从不缓存）
  run_eval.py     在数据集上运行检测器 -> 原始结果行 + 运行元数据
  report.py       检测器结果行 -> 表格，含 Wilson / McNemar / AUROC（从不调用模型）
  e2e.py          端到端攻击成功率：泄漏判定、可断点续跑的运行器
  run_e2e.py      对 injection-blast-radius 运行两种架构
  report_e2e.py   端到端结果行 -> 表格
  release.py      打包结果行、数据集清单、数据集发布目录
  verify.py       从已提交的结果行复现已发布的表格和图
  figure.py       结果图（assets/results.svg），纯标准库生成 SVG
  annotate.py     盲标注的第二标注者工具包：离线页面、答案密钥、一致性评分
data/seed/        手写的意图和难例良性文本
assets/           README 配图
results/          表格；results/rows/ 保存其背后的逐样本结果行
release/          数据集卡模板、校验和清单
paper/            技术报告
docs/             威胁模型、相关工作、路线图、数据卡
tests/            离线测试（不需要模型、网络或密钥）
```

数据：**v0**（226 条，已冻结；第一阶段的测量对象）和 **v1**（803 条：19 个意图、四个层级、
“埋在长文档里”的位置变体、11 个类别共 53 条良性样本），以及 **v2**（1,288 条：v1 加上
从 injection-blast-radius 语料移植的 12 种攻击，以及含 HTML 注释的良性 issue；v0 和 v1
由测试固定）。数据卡草稿：[docs/DATA_CARD.md](docs/DATA_CARD.md)。

## 快速开始

```bash
uv venv
uv pip install -e ".[dev]"
python -m pytest
python -m zhipi.build                    # v1 -> data/generated/v1.jsonl
python -m zhipi.build --version v0       # 冻结的第一阶段数据集
```

运行真实检测器（第一阶段；需要 `eval` 额外依赖，受限访问的 Prompt Guard 2 还需要
Hugging Face token，评判器需要 `DEEPSEEK_API_KEY`，会产生计费的 API 调用）：

```bash
uv pip install -e ".[eval]"
python -m zhipi.run_eval --defense qwen3guard --defense prompt-guard-2
python -m zhipi.run_eval --defense deepseek-judge --repeats 3 --dry-run   # 先数一下调用次数
python -m zhipi.run_eval --defense hf-classifier --hf-model Horizon-Labs/prompt-injection-guard-base \
    --hf-positive injection --hf-max-tokens 2048 --hf-stride 512   # 任意 Hub 上的注入分类器
python -m zhipi.report       # v1 -> results/v1.md（v0 加 --data data/generated/v0.jsonl）
```

针对 [injection-blast-radius](https://github.com/JiachengWu591/injection-blast-radius) 的端到端攻击
成功率（第四阶段；有计费的 API 调用，需要在 `IBR_REPO` 中放一份*专用的克隆*，因为运行会写入该
检出目录的 `sandbox/`）：

```bash
python -m zhipi.run_e2e --dry-run        # 先数样本数和调用次数
python -m zhipi.run_e2e                  # 基线 x3，隔离 x1
python -m zhipi.report_e2e               # -> results/v1_e2e.md
```

要在**同一个本地模型上运行两种架构**（免费；用于展示模型容易被劫持时边界的作用），用 llama.cpp 提供
一个兼容 OpenAI 接口的模型，再让运行指向它：

```bash
# llama.cpp b11829（CUDA 12.4 版）和官方 Qwen2.5-7B-Instruct Q4_K_M GGUF
llama-server -m qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf --jinja -ngl 99 -c 12288 \
    --host 127.0.0.1 --port 8080 --alias qwen2.5-7b-instruct
python -m zhipi.run_e2e --data data/generated/v2.jsonl --tag qwen25-7b \
    --victim-base-url http://127.0.0.1:8080/v1 --victim-model qwen2.5-7b-instruct \
    --tool-choice-mode required
python -m zhipi.report_e2e --data data/generated/v2.jsonl --tag qwen25-7b
```

（用 `required` 而不是 injection-blast-radius 发送的具名 tool choice，因为测试中 llama.cpp 没有遵守
具名选择；流水线仍会检查返回的是哪个工具及其参数。服务只绑定 127.0.0.1。）

## 健全性基线不是结果

`keyword-en` 和 `keyword-zh` 只用来测试测试框架本身。它们故意做得很朴素，测试只断言按构造必然
成立的事（例如插入零宽字符会让连续子串正则失效）。不要把它们当作关于真实检测器的证据；
真实检测器的结果在后面的阶段给出。

## 安全

所有载荷只针对本仓库自己的沙箱路径和一个固定的假占位密钥。没有任何内容针对真实产品、服务、
凭据或个人，每个注入样本都声明了其明文意图（`plaintext_intent`）以供审阅。预期用途：评估和加固
防御。

## 路线图

[docs/ROADMAP.md](docs/ROADMAP.md)：真实检测器 → 更多数据和变换 → 分析 → 结构层实验 → 发布。

## 许可、引用与贡献

代码为 MIT（[LICENSE](LICENSE)）；数据为 CC BY 4.0（[DATA_LICENSE.md](DATA_LICENSE.md)）。
引用方式见 [CITATION.cff](CITATION.cff)（GitHub 会显示“Cite this repository”按钮）。欢迎贡献：
[CONTRIBUTING.md](CONTRIBUTING.md)。负责任使用以及如何报告问题：[SECURITY.md](SECURITY.md)。

## 诚实的局限（目前）

合成的模板数据；19 个意图（其中 1 个 `judge_targeted`、2 个 `spoofed_structure`）；良性集只有
53 条；单一标注者；新颖性只在摘要层面核查过。每一项都记录在数据卡和路线图中。
