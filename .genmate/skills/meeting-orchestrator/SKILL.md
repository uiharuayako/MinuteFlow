---
name: meeting-orchestrator
description: 用于本地视频会议总结、材料融合、时间轴问答和会议工作流编排。
---

# Meeting Orchestrator

当用户希望分析本地会议视频、会议录音、会议纪要材料、演示文档或追问会议细节时，优先使用这一套工作流。

## 目标

- 从本地媒体和会议材料中构建稳定的会议证据包
- 尽量复用 MCP，而不是让模型自己手工推断文件结构
- 在“需要视频语义”与“只需要文本总结”之间做清晰区分

## MCP 选择规则

优先使用以下 MCP Server：

- `minuteflow-pipeline`
- `minuteflow-transcription`
- `minuteflow-documents`
- `minuteflow-media`

## 推荐流程

### 一站式

如果用户要的是“整体总结 / 会议纪要 / 行动项 / 问答”，优先直接调用：

- `run_meeting_workflow`

并传入：

- `media_path`
- `document_paths`
- `output_dir`
- 如有明确问题，再传 `user_request`

### 分步调试

如果用户要排查某个阶段，按下面顺序使用：

1. `inspect_media`
2. `transcribe_media`
3. `parse_document` 或 `parse_documents`
4. `extract_frames`
5. `run_meeting_workflow`

## 多模态与语言模型边界

- 如果用户只关心“谁说了什么、什么时候说的”，优先只做转写和材料解析
- 如果用户关心“视频里演示了什么、白板写了什么、界面切换说明了什么”，需要视频抽帧和多模态分析
- 如果 MCP 返回“未配置 multimodal endpoint”，明确告诉用户当前只生成了关键帧，未完成视觉语义分析
- 如果 MCP 返回“未配置 text LLM endpoint”，可以改由宿主模型基于 `meeting_packet.json`、`transcript.md` 和材料 markdown 自行总结

## 输出要求

默认优先引用这些产物路径：

- `meeting_packet.json`
- `meeting_summary.md`
- `transcript.md`
- `documents/*.md`
- `visual_analysis.json`

回答用户时：

- 先给结论
- 再给证据来源
- 若存在缺口，要显式指出是“转写缺口 / 材料缺口 / 视频语义缺口 / 模型配置缺口”

