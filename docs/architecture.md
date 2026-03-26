# 架构说明

## 目标

本项目提供一套可在 Codex 和 GenMate 中复用的本地会议理解能力，分成两层：

1. 能力层：多个 MCP Server
2. 调度层：一个 Meeting Orchestrator Skill

## MCP 划分

### `minuteflow-media`

负责：

- 媒体探测
- 抽取音轨
- 视频抽帧

### `minuteflow-documents`

负责：

- Markdown / TXT / DOCX / PPTX / PDF / XLSX / CSV 解析
- 输出统一文本

### `minuteflow-transcription`

负责：

- 音视频转写
- 时间戳切分
- 可选说话人分离

### `minuteflow-pipeline`

负责：

- 组合执行全链路
- 生成 meeting packet
- 可选调用外部多模态模型和语言模型

## 调度策略

Skill 不直接代替 MCP，而是定义：

- 什么时候一站式调用 `run_meeting_workflow`
- 什么时候需要分步排查
- 什么时候需要多模态
- 什么时候只能基于转写和材料回答

## 模型边界

### 多模态模型

通过环境变量配置：

- `MINUTEFLOW_MM_BASE_URL`
- `MINUTEFLOW_MM_MODEL`
- `MINUTEFLOW_MM_API_KEY`

用于：

- 基于关键帧总结视频视觉语义

### 语言模型

通过环境变量配置：

- `MINUTEFLOW_LLM_BASE_URL`
- `MINUTEFLOW_LLM_MODEL`
- `MINUTEFLOW_LLM_API_KEY`

用于：

- 生成会议总结
- 回答用户追问

## 输出产物

每次运行在 `artifacts/` 下生成独立 run 目录，常见产物包括：

- `transcription/transcript.json`
- `transcription/transcript.md`
- `documents/documents.json`
- `video/visual_analysis.json`
- `outputs/meeting_packet.json`
- `outputs/meeting_summary.md`
- `outputs/answer.md`

