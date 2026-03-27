# 集成说明

这篇文档聚焦在“怎么把 MinuteFlow 接进你的 Agent 或运行环境”。

如果你只想快速理解项目和第一次上手，先看仓库根目录的 `README.md`。这里更偏向实际接入和部署。

## 先选接入方式

MinuteFlow 同时支持两种常见接入方式：

1. 本地调用：`stdio`
2. 远程调用：`SSE`

默认推荐本地 `stdio`，因为这是最容易接入、最容易排障、也是当前 CLI 默认的 transport。

### 什么时候选本地 `stdio`

适合场景：

- 你在自己的电脑上使用 Codex 或 GenMate
- 音视频和会议材料都在本机
- 你希望尽量少配网络和远程服务

结论：

- `uv run minuteflow mcp ...` 默认就是 `stdio`
- `uv run minuteflow config codex`
- `uv run minuteflow config genmate`

上面两个配置生成命令输出的也是本地 `stdio` 风格配置。

### 什么时候选远程 `SSE`

适合场景：

- 你需要把 MCP 服务部署到 Linux 机器
- 上游客户端支持或只支持 `SSE`
- 媒体文件路径对远程机器可见

结论：

- 远程可使用 `SSE`
- 如果你在建设新的远程接入，仍然更推荐 `streamable-http`
- 只有在上游客户端需要 SSE 时，再显式使用 `--transport sse`

## 本地接入前准备

### 安装基础依赖

```bash
uv sync
```

说明：

- 仓库默认不携带 `uv.lock`
- `transcription`、`diarization`、`whisperx` 已移出根 `pyproject.toml`
- 基础 `uv sync` 不会默认拉起这些重型依赖
- 这样可以减少无 GPU、ARM 或异构 Linux 环境被锁进 `torch`、`triton`、`nvidia-*` 依赖链的概率

### 启用基础转写

```bash
uv run minuteflow deps install transcription
```

### 如需说话人分离

```bash
uv run minuteflow deps install transcription
uv run minuteflow deps install diarization
```

### 如需 WhisperX

```bash
uv run minuteflow deps install whisperx
```

如果目标机器没有 GPU，尤其是 ARM Linux 或 `aarch64`，建议只安装：

```bash
uv run minuteflow deps install transcription
```

尽量避免默认安装：

```bash
uv run minuteflow deps install transcription
uv run minuteflow deps install diarization
uv run minuteflow deps install whisperx
```

### 检查本地环境

```bash
uv run minuteflow doctor check
```

## 先用 CLI 跑通

不管你最终要接 Codex、GenMate 还是远程服务，都建议先直接把本地工作流跑通。

```bash
uv run minuteflow workflow run \
  --media /absolute/path/to/meeting.mp4 \
  --doc /absolute/path/to/agenda.md \
  --doc /absolute/path/to/slides.pptx \
  --output-dir /absolute/path/to/output
```

如果你只是想先验证本地链路，不想依赖文本模型和多模态模型，可以先关闭总结或视觉分析：

```bash
uv run minuteflow workflow run \
  --media /absolute/path/to/meeting.mp4 \
  --output-dir /absolute/path/to/output \
  --no-visual \
  --no-summary
```

## 本地 `stdio` 接入

### 接入 Codex

打印 `config.toml` 片段：

```bash
uv run minuteflow config codex
```

安装 Skill 软链接：

```bash
uv run minuteflow install codex-skill
```

直接安装 Skill 与 MCP 配置：

```bash
uv run minuteflow install codex
```

Codex 侧 Skill 位于：

- `skills/meeting-orchestrator/SKILL.md`

生成出来的 MCP 配置会直接调用本地命令，例如：

```toml
[mcp_servers.minuteflow_media]
command = "uv"
args = ["run", "--directory", "/path/to/MinuteFlow", "minuteflow", "mcp", "media"]
cwd = "/path/to/MinuteFlow"
```

这里不需要额外写 `--transport`，因为默认就是 `stdio`。

### 接入 GenMate

打印 MCP JSON：

```bash
uv run minuteflow config genmate
```

工作区 Skill 位于：

- `.genmate/skills/meeting-orchestrator/SKILL.md`

安装工作区 MCP 配置，并尝试自动写入本机 GenMate 设置：

```bash
uv run minuteflow install genmate
```

该命令会：

- 生成 `.genmate/mcpServers.json`
- 自动搜索 JetBrains 配置目录下的 `GenMatePlugin.xml`
- 如果找到，则写入 `mcpServersJson`
- 如果没找到，则保留工作区 JSON，供你在插件设置页导入或粘贴

如果你已经知道配置文件位置，也可以显式指定：

```bash
uv run minuteflow install genmate --settings-file /absolute/path/to/GenMatePlugin.xml
```

## 远程 `SSE` 接入

### 先确认一个关键前提

远程 MCP 服务只能读取“远程主机本身可访问的文件路径”。

也就是说，如果你把 `transcription` 或 `pipeline` 放到 Linux 上运行，下面至少满足一个：

- 媒体文件本来就在 Linux 上
- 本机和 Linux 共享同一个挂载目录
- 工作流在调用前会先把文件同步到 Linux

否则，即使远程 MCP 服务已经跑起来，也不能直接处理仅存在于本机的私有路径。

### 远程可用的 transport

MinuteFlow 的 MCP CLI 目前支持：

- `--transport stdio`
- `--transport sse`
- `--transport streamable-http`

选择建议：

- 本机集成：优先 `stdio`
- 远程老客户端兼容：使用 `SSE`
- 新的远程部署：更推荐 `streamable-http`

### 在 Linux GPU 上启动 SSE

先准备环境变量：

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

启动 SSE：

```bash
uv run minuteflow mcp transcription --transport sse
```

其他服务同理：

```bash
uv run minuteflow mcp media --transport sse
uv run minuteflow mcp documents --transport sse
uv run minuteflow mcp pipeline --transport sse
```

### 如果你在做新的远程部署

更推荐：

```bash
uv run minuteflow mcp transcription --transport streamable-http
```

典型启动示例：

```bash
export MINUTEFLOW_TRANSCRIPTION_BACKEND=faster-whisper
export MINUTEFLOW_WHISPER_DEVICE=cuda
export MINUTEFLOW_WHISPER_COMPUTE_TYPE=float16
export MINUTEFLOW_WHISPER_MODEL=small

export FASTMCP_HOST=0.0.0.0
export FASTMCP_PORT=8001

uv run minuteflow mcp transcription --transport streamable-http
```

### 何时把 `pipeline` 一起放到远端

只有在下面情况更建议把 `pipeline` 也放到 Linux：

- 文件路径已经统一到 Linux 或 NAS
- 你希望远端一次性完成转写、抽帧和多模态分析
- 你不介意所有输出目录也写在远端机器上

如果媒体文件仍主要保存在本机，通常更适合：

- 本机跑 `pipeline`
- 远端只承担高负载的转写或视觉阶段

当前仓库默认提供的是按服务所在机器本地路径读写文件的 MCP 工具，而不是自动上传文件的远程任务系统。

## 模型环境变量

### 文本总结 / 问答

```bash
export MINUTEFLOW_LLM_BASE_URL=http://your-openai-compatible-endpoint/v1
export MINUTEFLOW_LLM_MODEL=your-text-model
export MINUTEFLOW_LLM_API_KEY=your-key
```

### 视频关键帧多模态分析

```bash
export MINUTEFLOW_MM_BASE_URL=http://your-openai-compatible-endpoint/v1
export MINUTEFLOW_MM_MODEL=your-mm-model
export MINUTEFLOW_MM_API_KEY=your-key
```

### 说话人分离

```bash
export MINUTEFLOW_HF_TOKEN=your-huggingface-token
```

## 推荐部署拓扑

### 方案 A：CPU 本机 + 远程文本 / 多模态 API

适用于：

- 本机没有 GPU
- 但已经有可用的文本模型 API
- 也有可用的多模态模型 API

建议配置：

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

安装建议：

```bash
uv run minuteflow deps install transcription
```

这种模式下：

- CPU 本机完成音轨抽取、转写、文档解析、抽帧
- 文本模型 API 负责总结与问答
- 多模态模型 API 负责关键帧视觉理解

### 方案 B：CPU 本机 + Linux GPU 远程服务

适用于：

- 本机没有 GPU
- 有一台带 GPU 的 Linux 机器
- 会议文件能被 Linux 机器直接访问

这种模式下通常建议：

- Linux GPU 机器负责转写、可选 diarization、可选视觉分析
- 你的 PC 负责调用远程 MCP 服务或上层 Agent 编排
- 如果客户端只支持 SSE，则使用 `SSE`

## 本地样例命令

```bash
MINUTEFLOW_WHISPER_MODEL=tiny \
uv run minuteflow workflow run \
  --media demo_assets/sample.mp4 \
  --doc demo_assets/agenda.md \
  --output-dir demo_runs \
  --visual \
  --no-summary
```

运行结束后，建议优先查看：

- `demo_runs/.../outputs/meeting_packet.json`
- `demo_runs/.../transcription/transcript.md`
- `demo_runs/.../video/visual_analysis.json`
