# MinuteFlow

MinuteFlow 是一个面向本地会议场景的多阶段 AI 工作流：它读取视频 / 音频 / 会议材料，完成转写、说话人区分、文档解析、关键帧抽取、多模态理解，并把结果整理成可复用的会议证据包，供 Codex、GenMate 插件或你自己的上层 Agent 持续调用。

项目当前采用 **多个 MCP Server + 一个调度 Skill + 一个本地 CLI** 的组合方式，目标不是做单点“总结器”，而是沉淀一套可以在不同 Agent 平台复用的会议理解基础设施。

## 适用场景

- 本地会议录屏、会议音频、访谈录音的整理与总结
- 结合议程、需求文档、PPT、纪要草稿的多源理解
- 针对“谁在什么时候说了什么”进行追问
- 针对视频中的幻灯片、界面演示、白板内容做补充分析
- 给 Codex / GenMate 提供可编排、可扩展、可本地化部署的会议能力

## 当前能力

### 输入

- 本地媒体：`mp4`、`mov`、`mkv`、`mp3`、`wav` 等
- 会议材料：`md`、`txt`、`docx`、`pptx`、`pdf`、`xlsx`、`csv`
- 用户问题：例如“总结本次评审结论”“列出风险项”“谁反对了这个方案”

### 处理链路

1. 媒体探测：识别音视频属性，必要时抽取音轨
2. 转写：生成带时间戳的转写结果
3. 说话人分离：在可选依赖与令牌齐备时补充 speaker 标签
4. 材料解析：把多种文档转为统一文本上下文
5. 视频抽帧：按间隔提取关键帧作为视觉证据
6. 多模态分析：可选调用兼容 OpenAI 接口的视觉模型
7. 总结与问答：可选调用兼容 OpenAI 接口的文本模型
8. 证据打包：生成统一的 `meeting_packet.json`

### 输出

每次运行会在输出目录生成独立 run 目录，常见产物包括：

- `transcription/transcript.json`
- `transcription/transcript.md`
- `documents/documents.json`
- `video/frames/`
- `video/visual_analysis.json`
- `outputs/meeting_packet.json`
- `outputs/meeting_summary.md`
- `outputs/answer.md`

## 架构概览

MinuteFlow 拆成两层：

- 能力层：4 个可独立调用的 MCP Server
- 编排层：1 个 Meeting Orchestrator Skill

### MCP Servers

- `minuteflow-media`：媒体探测、音轨抽取、视频抽帧
- `minuteflow-documents`：会议材料解析与统一文本化
- `minuteflow-transcription`：音视频转写、时间戳切分、说话人分离
- `minuteflow-pipeline`：端到端工作流编排与会议证据包生成

### Skill

- Codex Skill 源：`skills/meeting-orchestrator/SKILL.md`
- GenMate 工作区 Skill：`.genmate/skills/meeting-orchestrator/SKILL.md`

Skill 负责决定：

- 何时直接跑整条工作流
- 何时分步调用各个 MCP 排查问题
- 何时需要视觉分析
- 在未配置模型时如何退化到基于证据包回答

## 为什么这个项目不是单一开源项目替代品

目前没有一个现成开源项目可以同时稳定满足下面几件事：

- 本地文件导入
- 多格式会议材料解析
- 说话人区分与时间戳转写
- 视频关键帧语义理解
- 被 Codex 和 GenMate 以 MCP / Skill 方式共同复用

所以 MinuteFlow 采用“**开源能力组件 + 自定义编排层**”路线：

- 转写默认使用 `faster-whisper`
- 可选切换到 `whisperx`
- 可选接入 `pyannote.audio` 做 diarization
- 文档解析使用本地 Python 生态库
- 视频处理依赖 `ffmpeg`
- 多模态与文本总结使用可配置的 OpenAI-compatible 接口

这让它即使在 **没配模型** 的情况下，也能先稳定产出转写、材料文本、关键帧和 `meeting_packet.json`，后续再逐步增强总结与问答能力。

## 快速开始

### 前置条件

在本机调试前，建议先确认这些前置条件：

- Python `3.11+`
- `uv`
- `ffmpeg` 与 `ffprobe` 已在 PATH 中可用
- 如需 `whisperx` / `pyannote.audio`，建议准备 CPU / CUDA 对应环境
- 如需说话人分离，准备 Hugging Face Token 并接受相关模型协议
- 如需总结 / 问答 / 视频语义分析，准备兼容 OpenAI 接口的模型端点

### 1. 安装基础依赖

```bash
uv sync
```

说明：

- 仓库默认不提交 `uv.lock`，避免在无 GPU、ARM、或异构 Linux 环境下被不必要的重型依赖锁定
- `transcription` / `diarization` / `whisperx` 已移出根 `pyproject.toml`，改为独立 requirements 配置，基础 `uv sync` 不会再解析它们
- 如需最小 CPU 安装，优先直接按当前平台解析依赖

### 2. 启用转写能力

```bash
uv run minuteflow deps install transcription
```

如需运行测试，再补上开发依赖：

```bash
uv sync --group dev
```

### 3. 如需说话人分离

```bash
uv run minuteflow deps install transcription
uv run minuteflow deps install diarization
```

### 4. 如需 WhisperX 路线

```bash
uv run minuteflow deps install whisperx
```

如果你在无 GPU 机器上部署，尤其是 ARM Linux / aarch64 环境，建议：

- 不要安装 `whisperx`
- 不要安装 `diarization`
- 仅安装 `transcription` 配置
- 将总结 / 问答 / 多模态理解交给远程 API

### 补充：离线下载模型（适合无外网机器）

如果目标机器无法直接访问 Hugging Face，而且无网机器只需要继续调用你内网现成的大模型 API，那么最推荐的做法是：

- 本地只离线准备 `faster-whisper` 转写模型
- 总结 / 问答继续走内网 `MINUTEFLOW_LLM_*` API
- 多模态分析继续走内网 `MINUTEFLOW_MM_*` API

这样维护成本最低，也最容易排障。

MinuteFlow 当前本地模型相关部分主要分三类：

- `faster-whisper` 转写模型
- `whisperx` 的转写 / 对齐模型
- `pyannote.audio` 的说话人分离模型

#### 方案 A：直接去网页下载 `faster-whisper` 模型

这是最适合“有网机器手动下载，再拷到无网机器”的方案。

推荐直接下载 SYSTRAN 提供的 CTranslate2 版本模型仓库：

- `tiny`：[Systran/faster-whisper-tiny](https://huggingface.co/Systran/faster-whisper-tiny)
- `base`：[Systran/faster-whisper-base](https://huggingface.co/Systran/faster-whisper-base)
- `small`：[Systran/faster-whisper-small](https://huggingface.co/Systran/faster-whisper-small)

如果是中文会议，初次使用通常建议先从 `base` 开始；机器更弱时用 `tiny`，想换更高准确率再试 `small`。

1. 在有网机器打开上面的模型页面。

2. 进入 `Files and versions`，把该仓库中的文件完整下载下来。

至少要保证这些文件和目录都在同一个模型目录里：

- `config.json`
- `tokenizer.json`
- `vocabulary.*`
- `preprocessor_config.json`
- `model.bin`

3. 在本地整理成一个独立目录，例如：

```text
/models/faster-whisper-base/
```

目录内应当能看到类似：

```text
/models/faster-whisper-base/config.json
/models/faster-whisper-base/model.bin
/models/faster-whisper-base/tokenizer.json
```

4. 把整个目录拷贝到无网机器，例如：

```text
/opt/minuteflow/models/faster-whisper-base
```

5. 在无网机器安装运行依赖：

```bash
uv sync
uv run minuteflow deps install transcription
```

6. 直接把 `MINUTEFLOW_WHISPER_MODEL` 指向本地模型目录：

```bash
export MINUTEFLOW_TRANSCRIPTION_BACKEND=faster-whisper
export MINUTEFLOW_WHISPER_MODEL=/opt/minuteflow/models/faster-whisper-base
export MINUTEFLOW_WHISPER_DEVICE=cpu
export MINUTEFLOW_WHISPER_COMPUTE_TYPE=int8
```

7. 如果无网机器还能访问你的内网大模型 API，可以同时这样配置：

```bash
export MINUTEFLOW_LLM_BASE_URL=http://your-internal-openai-compatible-endpoint/v1
export MINUTEFLOW_LLM_MODEL=your-text-model
export MINUTEFLOW_LLM_API_KEY=your-key

export MINUTEFLOW_MM_BASE_URL=http://your-internal-openai-compatible-endpoint/v1
export MINUTEFLOW_MM_MODEL=your-mm-model
export MINUTEFLOW_MM_API_KEY=your-key
```

8. 先做一次自检，再实际跑一段音频或视频验证：

```bash
uv run minuteflow doctor check
```

说明：

- 这里的关键点不是把模型放进 Hugging Face 缓存，而是直接把 `MINUTEFLOW_WHISPER_MODEL` 设为本地目录路径
- 这种方式最适合手工网页下载，不依赖有网机器先执行一次 Python 预热
- 如果你下载的是 `tiny` 或 `small`，只需要把环境变量里的路径改成对应目录即可

#### 方案 B：先在有网机器预热缓存，再整体迁移

如果你不想手动逐个点网页文件，或者后续还想顺手带上 `whisperx` / `pyannote.audio` 的缓存，可以继续使用“先缓存、再打包”的方式。

建议统一指定缓存目录，便于打包和迁移：

```bash
export HF_HOME=/absolute/path/to/model-cache/huggingface
export XDG_CACHE_HOME=/absolute/path/to/model-cache
mkdir -p "$HF_HOME"
```

#### 方案 B-1：只离线准备 `faster-whisper` 模型

这是最推荐的离线方案，依赖最少，也最容易在 CPU 机器上稳定运行。

1. 在有网机器安装依赖：

```bash
uv sync
uv run minuteflow deps install transcription
```

2. 选择你要预下载的模型，例如 `tiny`、`base`、`small`：

```bash
export MINUTEFLOW_WHISPER_MODEL=base
export MINUTEFLOW_WHISPER_DEVICE=cpu
export MINUTEFLOW_WHISPER_COMPUTE_TYPE=int8
```

3. 用一次最小化加载把模型下载到缓存：

```bash
uv run python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"
```

如果你想下载别的模型，把上面命令里的 `base` 改成需要的型号即可，例如：

```bash
uv run python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
```

4. 打包缓存目录并拷贝到目标机器：

```bash
tar -C /absolute/path/to/model-cache -czf minuteflow-model-cache.tar.gz huggingface
```

5. 在离线机器解压，并保持同样的环境变量：

```bash
mkdir -p /absolute/path/to/model-cache
tar -C /absolute/path/to/model-cache -xzf minuteflow-model-cache.tar.gz

export HF_HOME=/absolute/path/to/model-cache/huggingface
export XDG_CACHE_HOME=/absolute/path/to/model-cache
export MINUTEFLOW_TRANSCRIPTION_BACKEND=faster-whisper
export MINUTEFLOW_WHISPER_MODEL=base
export MINUTEFLOW_WHISPER_DEVICE=cpu
export MINUTEFLOW_WHISPER_COMPUTE_TYPE=int8
```

6. 先做一次自检，再执行工作流：

```bash
uv run minuteflow doctor check
```

说明：

- `doctor check` 主要检查环境与依赖，不保证逐个验证模型文件是否完整
- 最稳妥的验证方式，是在离线机器上实际跑一次转写
- 如果离线机器和下载机器的架构差异很大，优先保证 Python 依赖重新按目标机器安装；模型缓存只负责权重，不替代依赖安装

#### 方案 B-2：离线准备 `whisperx` 与说话人分离模型

如果你需要时间对齐或 diarization，可以额外预热 `whisperx` 和 `pyannote.audio`。这条路线依赖更重，建议只在确实需要时使用。

1. 在有网机器安装相关依赖：

```bash
uv sync
uv run minuteflow deps install whisperx
uv run minuteflow deps install diarization
```

2. 配置 Hugging Face Token：

```bash
export MINUTEFLOW_HF_TOKEN=your-huggingface-token
```

3. 预下载 WhisperX 转写模型：

```bash
uv run python -c "import whisperx; whisperx.load_model('base', 'cpu', compute_type='int8')"
```

4. 可选：再预下载对齐模型与说话人分离模型：

```bash
uv run python -c "import whisperx; whisperx.load_align_model(language_code='zh', device='cpu')"
uv run python -c "from pyannote.audio import Pipeline; Pipeline.from_pretrained('pyannote/speaker-diarization-3.1', use_auth_token='$MINUTEFLOW_HF_TOKEN')"
```

5. 然后和方案 A 一样，整体拷贝 `HF_HOME` / `XDG_CACHE_HOME` 对应缓存目录到离线机器。

注意：

- `pyannote.audio` 相关模型通常要求你先在 Hugging Face 网页端接受协议
- `whisperx` 的对齐模型会随语言不同而变化；如果你的会议主要是中文，建议至少预热一次 `language_code='zh'`
- 如果离线环境只是做普通会议转写，优先使用 `faster-whisper`，维护成本更低
- 如果你只是想“网页手工下载后直接拷贝使用”，优先用上面的方案 A，不建议把 `whisperx` 作为首选

#### 不在本教程覆盖范围内的模型

README 里提到的文本模型和多模态模型，当前接入方式是兼容 OpenAI 接口的远程端点：

- `MINUTEFLOW_LLM_*`
- `MINUTEFLOW_MM_*`

这两类不是 MinuteFlow 直接在本地下载和管理的模型权重，因此不适用上面的离线缓存流程。若你要完全离线部署这两类能力，通常需要先在你自己的推理服务里把模型部署好，再把 `BASE_URL` / `MODEL` 指向那个本地或局域网端点。

### 5. 检查环境

```bash
uv run minuteflow doctor check
```

### 6. 直接执行一次工作流

```bash
uv run minuteflow workflow run \
  --media /absolute/path/to/meeting.mp4 \
  --doc /absolute/path/to/agenda.md \
  --doc /absolute/path/to/slides.pptx \
  --output-dir /absolute/path/to/output
```

## 本机调试

如果你想在本机快速验证 MinuteFlow 是否跑通，建议按下面顺序排查。

### 1. 准备环境变量

先从示例文件复制一份本地配置：

```bash
cp .env.example .env
```

默认只需要调整这些项：

- `MINUTEFLOW_WHISPER_MODEL`：本机调试建议先用 `tiny` 或 `base`
- `MINUTEFLOW_TRANSCRIPTION_LANGUAGE`：已知会议语言时可显式指定，如 `zh`
- `MINUTEFLOW_HF_TOKEN`：仅在启用 diarization 时需要
- `MINUTEFLOW_LLM_*`：仅在启用总结 / 问答时需要
- `MINUTEFLOW_MM_*`：仅在启用视频语义分析时需要

### 2. 先做环境自检

```bash
uv run minuteflow doctor check
```

建议至少确认：

- Python 版本符合要求
- `ffmpeg` / `ffprobe` 可执行
- 你选择的转写依赖已经安装
- 如果启用 diarization，`MINUTEFLOW_HF_TOKEN` 已配置

### 无 GPU / ARM 环境避坑

如果你在无 GPU 的 Linux 机器，特别是 `aarch64` / ARM 环境里执行 `uv sync`，曾遇到 `triton`、`torch`、`nvidia-*`、`nvidia_cusolver_cu12` 之类错误，根因通常不是 MinuteFlow 的主链路，而是 `whisperx` / `pyannote.audio` 这类重型依赖在解析阶段被带入。

推荐安装方式：

```bash
rm -rf .venv
uv run minuteflow deps install transcription
```

如需测试：

```bash
uv sync --group dev
```

不建议在这类环境默认安装：

```bash
uv run minuteflow deps install transcription
uv run minuteflow deps install diarization
uv run minuteflow deps install whisperx
```

推荐运行时配置：

```bash
export MINUTEFLOW_TRANSCRIPTION_BACKEND=faster-whisper
export MINUTEFLOW_WHISPER_DEVICE=cpu
export MINUTEFLOW_WHISPER_COMPUTE_TYPE=int8
export MINUTEFLOW_WHISPER_MODEL=base
```

### 3. 用最小命令跑通一条链路

如果只想验证“媒体读取 + 转写 + 打包”是否正常，可先关闭视觉与总结：

```bash
uv run minuteflow workflow run \
  --media /absolute/path/to/meeting.mp4 \
  --output-dir /absolute/path/to/output \
  --no-visual \
  --no-summary
```

这样即使没配 LLM / 多模态端点，也能确认：

- 媒体探测是否正常
- 音轨抽取是否正常
- 转写是否正常
- `meeting_packet.json` 是否生成

### 4. 分阶段调试

如果端到端执行失败，建议拆开看：

```bash
uv run minuteflow mcp media
uv run minuteflow mcp documents
uv run minuteflow mcp transcription
uv run minuteflow mcp pipeline
```

以及运行测试：

```bash
uv run python -m pytest -q
```

### 5. 调试时最有用的信息

如果你准备把问题贴到 issue 或发给协作者，建议一并提供：

- 操作系统与 CPU / GPU 信息
- Python 版本、`uv --version`、`ffmpeg -version`
- 安装命令，例如 `uv run minuteflow deps install transcription`
- 使用的输入文件类型，例如 `mp4` / `wav` / `pptx`
- 是否配置了 `MINUTEFLOW_HF_TOKEN`
- 是否配置了 `MINUTEFLOW_LLM_*` / `MINUTEFLOW_MM_*`
- 失败命令全文
- 输出目录中的 `transcription/transcript.json`
- 输出目录中的 `outputs/meeting_packet.json`
- 完整报错堆栈

## 接入 Codex 与 GenMate

### Codex

打印 MCP 配置片段：

```bash
uv run minuteflow config codex
```

自动安装 Skill 与 MCP 配置：

```bash
uv run minuteflow install codex
```

### GenMate

打印 MCP JSON：

```bash
uv run minuteflow config genmate
```

写入工作区 MCP 配置并尝试自动安装：

```bash
uv run minuteflow install genmate
```

如果本机未能自动定位 GenMate 配置文件，MinuteFlow 仍会保留工作区内的 `.genmate/mcpServers.json`，你可以在插件设置中直接导入或粘贴。

## 模型配置

如果你希望在流水线内部直接完成视觉理解、总结和问答，可设置以下环境变量。

### 文本模型

```bash
export MINUTEFLOW_LLM_BASE_URL=http://your-openai-compatible-endpoint/v1
export MINUTEFLOW_LLM_MODEL=your-text-model
export MINUTEFLOW_LLM_API_KEY=your-key
```

### 多模态模型

```bash
export MINUTEFLOW_MM_BASE_URL=http://your-openai-compatible-endpoint/v1
export MINUTEFLOW_MM_MODEL=your-mm-model
export MINUTEFLOW_MM_API_KEY=your-key
```

### Hugging Face Token

```bash
export MINUTEFLOW_HF_TOKEN=your-huggingface-token
```

## 部署建议

### 场景 1：本机无显卡，但有文本模型和多模态模型 API

这是当前最推荐、也最容易稳定落地的配置方式：

- 本机负责：媒体探测、抽音轨、CPU 转写、文档解析、抽帧
- 远程 API 负责：总结 / 问答 / 视频关键帧语义理解
- 可选跳过：说话人分离（CPU 上通常更慢）

建议环境变量：

```bash
export MINUTEFLOW_TRANSCRIPTION_BACKEND=faster-whisper
export MINUTEFLOW_WHISPER_DEVICE=cpu
export MINUTEFLOW_WHISPER_COMPUTE_TYPE=int8
export MINUTEFLOW_WHISPER_MODEL=base
export MINUTEFLOW_TRANSCRIPTION_LANGUAGE=zh

export MINUTEFLOW_LLM_BASE_URL=http://your-openai-compatible-endpoint/v1
export MINUTEFLOW_LLM_MODEL=your-text-model
export MINUTEFLOW_LLM_API_KEY=your-key

export MINUTEFLOW_MM_BASE_URL=http://your-openai-compatible-endpoint/v1
export MINUTEFLOW_MM_MODEL=your-mm-model
export MINUTEFLOW_MM_API_KEY=your-key
```

建议安装：

```bash
uv run minuteflow deps install transcription
```

建议运行方式：

```bash
uv run minuteflow workflow run \
  --media /absolute/path/to/meeting.mp4 \
  --doc /absolute/path/to/agenda.md \
  --output-dir /absolute/path/to/output
```

如果你只想先验证 CPU 机器上的本地处理链路，可以先关闭总结或视觉分析：

```bash
uv run minuteflow workflow run \
  --media /absolute/path/to/meeting.mp4 \
  --output-dir /absolute/path/to/output \
  --no-summary
```

或者：

```bash
uv run minuteflow workflow run \
  --media /absolute/path/to/meeting.mp4 \
  --output-dir /absolute/path/to/output \
  --no-visual
```

### 场景 2：本机无显卡，但另有一台带 GPU 的 Linux 机器

这种场景是否更适合把服务部署到 Linux，关键取决于“媒体文件最终由谁读取”。

更适合部署到 Linux GPU 机器的情况：

- 会议视频 / 音频本来就存放在 Linux 机器上
- 或者 PC 与 Linux 共享同一份 NAS / 挂载目录
- 或者你的上层系统本身就会先把文件同步到 Linux 再发起处理

不太适合直接远程部署的情况：

- 文件只在本机 PC 上，Linux 机器无法直接访问这些本地路径
- 希望远端 MCP 直接读取类似 `/Users/...` 或 `C:\\...` 这类仅本机存在的路径

原因是当前 MinuteFlow 的 MCP 工具接受的是“服务所在机器可访问的本地文件路径”。

在这种双机架构里，我更建议：

- Linux GPU 机器负责转写、可选 diarization、可选视觉分析
- 你的 PC 负责调用远程 MCP 服务，或只负责上层 Agent 编排
- 文本总结 / 多模态理解继续走你已有的 API，也可以直接从 Linux 发起

### 远程 MCP 传输方式

MinuteFlow 当前支持把 MCP 服务以以下方式运行：

- `stdio`
- `sse`
- `streamable-http`

如果是本机集成 Codex / GenMate，优先继续用 `stdio`。

如果是部署到 Linux 供远程访问，更推荐 `streamable-http`；`sse` 适合兼容旧客户端，但不建议作为新部署的首选。

远程运行时，可通过 `FASTMCP_HOST` / `FASTMCP_PORT` 控制监听地址：

```bash
export FASTMCP_HOST=0.0.0.0
export FASTMCP_PORT=8001
```

例如在 Linux GPU 机器上启动转写服务：

```bash
MINUTEFLOW_TRANSCRIPTION_BACKEND=faster-whisper \
MINUTEFLOW_WHISPER_DEVICE=cuda \
MINUTEFLOW_WHISPER_COMPUTE_TYPE=float16 \
MINUTEFLOW_WHISPER_MODEL=small \
FASTMCP_HOST=0.0.0.0 \
FASTMCP_PORT=8001 \
uv run minuteflow mcp transcription --transport streamable-http
```

如果你需要兼容只支持 SSE 的客户端，也可以这样启动：

```bash
FASTMCP_HOST=0.0.0.0 \
FASTMCP_PORT=8001 \
uv run minuteflow mcp transcription --transport sse
```

更完整的建议是把 `media`、`transcription`、`pipeline` 中真正需要远程运行的部分按职责拆开部署，而不是默认把所有服务都放到远端。

## 已验证状态

当前仓库已经跑通的内容包括：

- `uv sync`
- `uv run python -m pytest -q`
- `uv run minuteflow mcp media|documents|transcription|pipeline`
- `uv run minuteflow install codex`
- 基于样例媒体的端到端工作流执行

在未配置 LLM / 多模态模型时，MinuteFlow 仍然会继续产出：

- 转写文本
- 材料解析结果
- 视频关键帧
- `meeting_packet.json`

## 项目结构

- `src/minuteflow/`：核心实现与 CLI
- `src/minuteflow/mcp/`：4 个 MCP Server 入口
- `src/minuteflow/services/`：媒体、文档、转写、视频、流水线服务
- `skills/meeting-orchestrator/`：Codex 侧 Skill
- `.genmate/skills/meeting-orchestrator/`：GenMate 侧 Skill
- `docs/architecture.md`：架构说明
- `docs/integration.md`：集成说明
- `docs/oss-survey.md`：开源方案调研

## 贡献与许可

- 贡献方式见 `CONTRIBUTING.md`
- 开源许可证见 `LICENSE`（Apache-2.0）

## 下一步建议

如果你接下来要把它用于真实会议，我建议按这个顺序推进：

1. 用一段真实会议录音或录屏验证转写质量
2. 安装 diarization 依赖，验证说话人区分效果
3. 配置你本地可用的文本 / 多模态模型端点
4. 针对你的会议类型继续调优总结模板与追问策略
5. 在 Codex 和 GenMate 中分别跑一次真实使用链路
