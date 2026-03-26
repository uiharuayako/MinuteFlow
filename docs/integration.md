# 集成说明

## 安装依赖

基础能力：

```bash
uv sync
```

启用基础转写：

```bash
uv sync --extra transcription
```

启用说话人分离：

```bash
uv sync --extra transcription --extra diarization
```

启用 `whisperx`：

```bash
uv sync --extra whisperx
```

检查本地环境：

```bash
uv run minuteflow doctor check
```

## 直接运行工作流

```bash
uv run minuteflow workflow run \
  --media /absolute/path/to/meeting.mp4 \
  --doc /absolute/path/to/agenda.md \
  --doc /absolute/path/to/slides.pptx \
  --output-dir /absolute/path/to/output
```

## GenMate 接入

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

## Codex 接入

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

Codex 侧 Skill 源位于：

- `skills/meeting-orchestrator/SKILL.md`

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
uv sync --extra transcription
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

这里最重要的前提是：远程 MCP 服务只能读取“远程主机本身可访问的文件路径”。

也就是说，如果你要把 `transcription` 或 `pipeline` 放到 Linux 上运行，下面至少满足一个：

- 媒体文件本来就在 Linux 上
- 本机和 Linux 共享同一个挂载目录
- 工作流在调用前会先把文件同步到 Linux

否则，即使 MCP 服务已经远程跑起来，也不能直接处理仅存在于本机的私有路径。

## 远程 MCP 启动方式

MinuteFlow 的 MCP CLI 现在支持：

- `--transport stdio`
- `--transport sse`
- `--transport streamable-http`

本机集成优先用 `stdio`。

远程部署优先推荐 `streamable-http`；如果上游客户端只支持 SSE，再使用 `sse`。

### Linux GPU 上启动转写服务

```bash
export MINUTEFLOW_TRANSCRIPTION_BACKEND=faster-whisper
export MINUTEFLOW_WHISPER_DEVICE=cuda
export MINUTEFLOW_WHISPER_COMPUTE_TYPE=float16
export MINUTEFLOW_WHISPER_MODEL=small

export FASTMCP_HOST=0.0.0.0
export FASTMCP_PORT=8001

uv run minuteflow mcp transcription --transport streamable-http
```

### Linux GPU 上启动 SSE

```bash
export FASTMCP_HOST=0.0.0.0
export FASTMCP_PORT=8001

uv run minuteflow mcp transcription --transport sse
```

### 何时把 `pipeline` 一起放到远端

只有在下面情况更建议把 `pipeline` 也放到 Linux：

- 文件路径已经统一到 Linux / NAS
- 你希望远端一次性完成转写、抽帧和多模态分析
- 你不介意所有输出目录也写在远端机器上

如果媒体文件仍主要保存在本机，通常更适合：

- 本机跑 `pipeline`
- 远端只承担高负载的转写 / 视觉阶段

但要注意：当前仓库默认提供的是按服务所在机器本地路径读写文件的 MCP 工具，而不是自动上传文件的远程任务系统。

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

运行结束后，请优先查看：

- `demo_runs/.../outputs/meeting_packet.json`
- `demo_runs/.../transcription/transcript.md`
- `demo_runs/.../video/visual_analysis.json`
