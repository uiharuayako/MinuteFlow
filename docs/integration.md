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
