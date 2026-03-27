# MinuteFlow

MinuteFlow 是一套面向本地会议场景的会议理解基础设施。它可以读取音视频和会议材料，完成转写、说话人分离、文档解析、关键帧抽取、多模态理解，并把结果整理成可复用的 `meeting_packet.json`，供 Codex、GenMate 或你自己的 Agent 持续追问和复用。

项目采用「多个 MCP Server + 一个编排 Skill + 一个本地 CLI」的组合方式。目标不是做一次性的会议总结器，而是沉淀一套可以反复接入、持续扩展、优先本地运行的工作流能力。

## README 怎么看

如果你是第一次接触 MinuteFlow，建议按这个顺序阅读：

1. 先看 [两种接入方式](#两种接入方式)，明确应该走本地 `stdio` 还是远程 `SSE`
2. 再看 [快速开始](#快速开始)，先把本地链路跑通
3. 最后按需要看 [接入 Agent](#接入-agent) 和 [部署建议](#部署建议)

## 它能做什么

### 输入

- 本地媒体文件：`mp4`、`mov`、`mkv`、`mp3`、`wav`
- 会议材料：`md`、`txt`、`docx`、`pptx`、`pdf`、`xlsx`、`csv`
- 用户问题：例如“总结结论”“列出风险项”“谁反对过这个方案”

### 处理链路

1. 媒体探测：识别音视频属性，必要时抽取音轨
2. 转写：生成带时间戳的转写结果
3. 说话人分离：在依赖和令牌齐备时补充 speaker 标签
4. 材料解析：把多种文档转成统一文本上下文
5. 视频抽帧：按间隔提取关键帧
6. 多模态分析：可选调用兼容 OpenAI 接口的视觉模型
7. 总结与问答：可选调用兼容 OpenAI 接口的文本模型
8. 证据打包：生成统一的 `meeting_packet.json`

### 常见输出

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

MinuteFlow 分成两层：

- 能力层：4 个可独立调用的 MCP Server
- 编排层：1 个 Meeting Orchestrator Skill

### MCP Servers

- `minuteflow-media`：媒体探测、音轨抽取、视频抽帧
- `minuteflow-documents`：会议材料解析与统一文本化
- `minuteflow-transcription`：音视频转写、时间戳切分、说话人分离
- `minuteflow-pipeline`：端到端工作流编排与会议证据包生成

### Skill

- Codex Skill：`skills/meeting-orchestrator/SKILL.md`
- GenMate 工作区 Skill：`.genmate/skills/meeting-orchestrator/SKILL.md`

Skill 负责决定：

- 何时直接跑完整工作流
- 何时分步调用 MCP 排查问题
- 何时需要视觉分析
- 未配置模型时如何退化到基于证据包回答

## 两种接入方式

MinuteFlow 现在给用户两条清晰的引导路径，并且同时支持本地 `stdio` 调用和远程 `SSE` 调用。

### 方式一：本地调用（默认推荐）

适合场景：

- 你在自己的电脑上使用 Codex 或 GenMate
- 音视频和文档都在本机
- 你希望配置最简单、排障最直接

结论：

- 默认使用 `stdio`
- 这也是 `minuteflow mcp ...` 的默认 transport
- `uv run minuteflow config codex` 和 `uv run minuteflow config genmate` 生成的也是本地 `stdio` 配置

### 方式二：远程调用（SSE）

适合场景：

- 你要把服务部署到另一台 Linux 机器
- 上游客户端支持或只支持 `SSE`
- 媒体文件路径对远程机器可见，或者文件本来就存放在远端

结论：

- 远程接入可使用 `SSE`
- 如果你在建设新的远程部署，仍然更推荐 `streamable-http`
- 只有在上游客户端需要 SSE 时，再显式使用 `--transport sse`

## 快速开始

### 前置条件

在本机调试前，建议先确认这些条件：

- Python `3.11+`
- `uv`
- `ffmpeg` 与 `ffprobe` 已在 `PATH` 中可用
- 如需 `whisperx` / `pyannote.audio`，准备对应 CPU 或 CUDA 环境
- 如需说话人分离，准备 Hugging Face Token 并接受相关模型协议
- 如需总结、问答、视频语义分析，准备兼容 OpenAI 接口的模型端点

### 1. 安装基础依赖

```bash
uv sync
```

说明：

- 仓库默认不提交 `uv.lock`
- `transcription`、`diarization`、`whisperx` 已移出根 `pyproject.toml`
- 基础 `uv sync` 不会默认拉起这些重型依赖

### 2. 启用基础转写

```bash
uv run minuteflow deps install transcription
```

如需运行测试，再补上开发依赖：

```bash
uv sync --group dev
```

### 3. 准备 `.env`

```bash
cp .env.example .env
```

本机第一次调试通常只需要关注这些配置：

- `MINUTEFLOW_WHISPER_MODEL`：建议先用 `tiny` 或 `base`
- `MINUTEFLOW_TRANSCRIPTION_LANGUAGE`：已知语言时建议显式指定，例如 `zh`
- `MINUTEFLOW_HF_TOKEN`：仅在启用 diarization 时需要
- `MINUTEFLOW_LLM_*`：仅在启用总结 / 问答时需要
- `MINUTEFLOW_MM_*`：仅在启用视觉分析时需要

### 4. 环境自检

```bash
uv run minuteflow doctor check
```

### 5. 先直接跑通一次工作流

先用 CLI 跑通，是最稳的起点：

```bash
uv run minuteflow workflow run \
  --media /absolute/path/to/meeting.mp4 \
  --doc /absolute/path/to/agenda.md \
  --doc /absolute/path/to/slides.pptx \
  --output-dir /absolute/path/to/output
```

如果你还没配置文本模型或多模态模型，可以先关闭相关阶段，只验证本地链路：

```bash
uv run minuteflow workflow run \
  --media /absolute/path/to/meeting.mp4 \
  --output-dir /absolute/path/to/output \
  --no-visual \
  --no-summary
```

这一步跑通后，再接入 Codex 或 GenMate 会轻松很多。

## 接入 Agent

### 路径 A：本地 `stdio` 接入

这是默认方式，也是 README 最推荐的方式。

#### Codex

打印可直接粘贴的配置片段：

```bash
uv run minuteflow config codex
```

自动安装 Skill 与 MCP 配置：

```bash
uv run minuteflow install codex
```

当前生成出来的 MCP 配置会直接调用本地命令，例如：

```toml
[mcp_servers.minuteflow_media]
command = "uv"
args = ["run", "--directory", "/path/to/MinuteFlow", "minuteflow", "mcp", "media"]
```

这里没有额外传 `--transport`，因为默认就是 `stdio`。

#### GenMate

打印 MCP JSON：

```bash
uv run minuteflow config genmate
```

自动写入工作区配置并尝试安装：

```bash
uv run minuteflow install genmate
```

如果本机未能自动定位 GenMate 配置文件，MinuteFlow 仍会保留工作区内的 `.genmate/mcpServers.json`，你可以在插件设置里直接导入或粘贴。

### 路径 B：远程 `SSE` 接入

当你需要把 MCP 服务跑在远程机器上，并通过网络访问时，可以使用 `SSE`。

#### 1. 在远程机器准备环境变量

```bash
export FASTMCP_HOST=0.0.0.0
export FASTMCP_PORT=8001
```

如果远程机器负责 GPU 转写，也可以一起配置：

```bash
export MINUTEFLOW_TRANSCRIPTION_BACKEND=faster-whisper
export MINUTEFLOW_WHISPER_DEVICE=cuda
export MINUTEFLOW_WHISPER_COMPUTE_TYPE=float16
export MINUTEFLOW_WHISPER_MODEL=small
```

#### 2. 启动 SSE 服务

```bash
uv run minuteflow mcp transcription --transport sse
```

其他服务同理：

```bash
uv run minuteflow mcp media --transport sse
uv run minuteflow mcp documents --transport sse
uv run minuteflow mcp pipeline --transport sse
```

#### 3. 使用前务必确认路径可见性

远程 MCP 读取的是“服务所在机器可访问的本地路径”，这点非常重要。

适合远程 `SSE` 的情况：

- 媒体文件本来就在 Linux 服务器上
- 你的 PC 和 Linux 共享同一份 NAS 或挂载目录
- 上层系统会先把文件同步到远端，再发起调用

不适合远程 `SSE` 的情况：

- 你希望远程服务直接读取仅存在于本机的 `/Users/...` 或 `C:\...` 路径

### transport 选择建议

可以简单理解成：

- 本地集成 Codex / GenMate：默认 `stdio`
- 远程老客户端兼容：使用 `SSE`
- 新的远程部署：更推荐 `streamable-http`

## 常见安装组合

### 最小 CPU 方案

适合无 GPU、本地先跑通链路：

```bash
uv sync
uv run minuteflow deps install transcription
```

推荐 `.env`：

```bash
MINUTEFLOW_TRANSCRIPTION_BACKEND=faster-whisper
MINUTEFLOW_WHISPER_DEVICE=cpu
MINUTEFLOW_WHISPER_COMPUTE_TYPE=int8
MINUTEFLOW_WHISPER_MODEL=base
```

### 需要说话人分离

```bash
uv run minuteflow deps install transcription
uv run minuteflow deps install diarization
```

并配置：

```bash
MINUTEFLOW_HF_TOKEN=your-huggingface-token
```

### 需要 WhisperX

```bash
uv run minuteflow deps install whisperx
```

如果你在无 GPU 机器上部署，尤其是 ARM Linux 或 `aarch64` 环境，建议：

- 不安装 `whisperx`
- 不安装 `diarization`
- 优先只安装 `transcription`
- 将总结、问答和多模态理解交给远程 API

## 模型配置

如果你希望在流水线内部直接完成总结、问答和视觉分析，建议把下面配置写进项目根目录 `.env`。

### 文本模型

```bash
MINUTEFLOW_LLM_BASE_URL=http://your-openai-compatible-endpoint/v1
MINUTEFLOW_LLM_MODEL=your-text-model
MINUTEFLOW_LLM_API_KEY=your-key
```

### 多模态模型

```bash
MINUTEFLOW_MM_BASE_URL=http://your-openai-compatible-endpoint/v1
MINUTEFLOW_MM_MODEL=your-mm-model
MINUTEFLOW_MM_API_KEY=your-key
```

### Hugging Face Token

```bash
MINUTEFLOW_HF_TOKEN=your-huggingface-token
```

## 部署建议

### 场景 1：本机 CPU + 远程文本 / 多模态 API

这是当前最容易稳定落地的方案：

- 本机负责媒体探测、抽音轨、CPU 转写、文档解析、抽帧
- 远程 API 负责总结、问答、视频关键帧语义理解
- 如无明确需要，可暂时跳过 diarization

建议配置：

```bash
MINUTEFLOW_TRANSCRIPTION_BACKEND=faster-whisper
MINUTEFLOW_WHISPER_DEVICE=cpu
MINUTEFLOW_WHISPER_COMPUTE_TYPE=int8
MINUTEFLOW_WHISPER_MODEL=base
MINUTEFLOW_TRANSCRIPTION_LANGUAGE=zh

MINUTEFLOW_LLM_BASE_URL=http://your-openai-compatible-endpoint/v1
MINUTEFLOW_LLM_MODEL=your-text-model
MINUTEFLOW_LLM_API_KEY=your-key

MINUTEFLOW_MM_BASE_URL=http://your-openai-compatible-endpoint/v1
MINUTEFLOW_MM_MODEL=your-mm-model
MINUTEFLOW_MM_API_KEY=your-key
```

### 场景 2：本机无 GPU，但另有一台 Linux GPU 机器

更适合远程部署到 Linux 的情况：

- 会议视频 / 音频本来就存放在 Linux 上
- PC 与 Linux 共享同一份 NAS 或挂载目录
- 你的系统会先把文件同步到 Linux 再处理

这种场景通常建议：

- Linux GPU 机器负责转写、可选 diarization、可选视觉分析
- 你的 PC 负责上层 Agent 编排
- 若客户端只支持 SSE，则使用 `SSE`

## 调试建议

### 本地分阶段排查

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

### 提问题时尽量附带这些信息

- 操作系统与 CPU / GPU 信息
- Python 版本、`uv --version`、`ffmpeg -version`
- 安装命令，例如 `uv run minuteflow deps install transcription`
- 使用的输入文件类型，例如 `mp4`、`wav`、`pptx`
- 是否配置了 `MINUTEFLOW_HF_TOKEN`
- 是否配置了 `MINUTEFLOW_LLM_*` / `MINUTEFLOW_MM_*`
- 失败命令全文
- 输出目录中的 `transcription/transcript.json`
- 输出目录中的 `outputs/meeting_packet.json`
- 完整报错堆栈

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

## 更多文档

- `docs/integration.md`：更完整的集成与远程部署说明
- `docs/architecture.md`：架构说明
- `docs/oss-survey.md`：相关开源方案调研
- `CONTRIBUTING.md`：贡献说明

## 项目结构

- `src/minuteflow/`：核心实现与 CLI
- `src/minuteflow/mcp/`：4 个 MCP Server 入口
- `src/minuteflow/services/`：媒体、文档、转写、视频、流水线服务
- `skills/meeting-orchestrator/`：Codex 侧 Skill
- `.genmate/skills/meeting-orchestrator/`：GenMate 侧 Skill

## 许可

开源许可证见 `LICENSE`，当前为 Apache-2.0。
