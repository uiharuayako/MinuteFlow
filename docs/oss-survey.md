# 开源项目调研：本地视频会议总结工作流

更新时间：2026-03-26

## 结论

截至目前，没有看到一个成熟的开源项目可以**直接**完整覆盖你提出的全部需求：

- 本地视频/音频读取
- 说话人区分 + 时间戳转写
- 视频语义分析
- 融合 Markdown / DOCX / PPTX / PDF 等会议材料
- 以 MCP + Skill 的方式被通用 AI 平台和插件复用

但是，已经存在一组成熟度较高的开源组件，组合起来基本可以满足需求。最合理的路线是：

**使用成熟开源组件做能力层，再由我们自己实现 MCP Server + Skill 编排层。**

---

## 最值得复用的开源项目

### 1) WhisperX

项目地址：

- https://github.com/m-bain/whisperX

适合承担：

- 音频 / 视频转写
- 词级或片段级时间戳对齐
- 为后续说话人分离结果回填时间信息

优点：

- 在 Whisper 生态里非常接近你的需求
- 对齐能力强，适合做精确时间轴
- 社区使用广泛，适合作为基础模块

不足：

- 不是完整的会议理解系统
- 说话人分离能力通常仍要配合 `pyannote-audio`
- 不是为 MCP 或 Skill 编排直接设计的

结论：

- **强烈建议纳入核心栈**

---

### 2) pyannote-audio

项目地址：

- https://github.com/pyannote/pyannote-audio

适合承担：

- 说话人分离（speaker diarization）
- 说话人切分
- 多人会议的讲话区间识别

优点：

- 开源说话人分离领域非常主流
- 与 WhisperX 组合成熟
- 适合构建“谁在什么时间说了什么”的结构化结果

不足：

- 单独使用时不负责完整 ASR
- 在长音频、多语混说、重叠语音场景下仍要调优
- 部署与性能优化需要工程工作

结论：

- **建议和 WhisperX 绑定使用**

---

### 3) Docling

项目地址：

- https://github.com/docling-project/docling

适合承担：

- 会议材料解析
- PDF / DOCX / PPTX 等文档抽取
- 将文档统一转换为结构化文本或中间表示

优点：

- 面向复杂文档理解
- 对企业文档、版面和结构化抽取更友好
- 比仅做纯文本转换的工具更适合会议材料场景

不足：

- 主要解决文档侧问题，不覆盖音视频总结链路
- 仍需要你自己做结果融合和调度

结论：

- **非常适合做文档解析 MCP**

---

### 4) MarkItDown

项目地址：

- https://github.com/microsoft/markitdown

适合承担：

- 将常见办公文档转换为 Markdown
- 快速打通 DOCX / PPTX / HTML / PDF 等输入

优点：

- 上手快
- 对“统一转成 Markdown 再喂给 LLM”很方便
- 很适合做轻量化文档摄取层

不足：

- 对复杂版面、图表、版式恢复不如 Docling
- 更偏“转换器”，不是完整理解框架

结论：

- **适合轻量输入管道**
- 如果后面需要更强文档理解，可与 `Docling` 互补

---

### 5) VideoLLaMA3

项目地址：

- https://github.com/DAMO-NLP-SG/VideoLLaMA3

适合承担：

- 视频语义理解
- 对抽帧或视频片段进行多模态推理
- 识别演示画面、白板、界面切换、动作上下文

优点：

- 是更接近你“视频语义分析”需求的开源方向
- 可作为视频多模态模型后端

不足：

- 不是开箱即用的会议总结系统
- 通常仍需你自己控制抽帧、窗口切分、上下文聚合
- 本地部署成本高于纯语言模型

结论：

- **适合作为视频理解模块候选**
- 但必须配合自定义编排

---

## 接近需求的一体化 / 半一体化项目

这些项目有参考价值，但都不能完整满足你的目标。

### 6) Transcription Stream

项目地址：

- https://github.com/transcriptionstream/transcriptionstream

适合参考：

- 本地优先转写
- 会议或音视频内容分析
- 将转写与后续问答串起来

不足：

- 更偏应用层产品
- 对“会议材料融合”和“视频语义理解”覆盖有限
- 不以 MCP + Skill 复用为核心设计目标

结论：

- **适合作为应用流程参考，不适合作为最终底座**

---

### 7) meeting-minutes

项目地址：

- https://github.com/Zackriya-Solutions/meeting-minutes

适合参考：

- 会议纪要场景
- 本地或半本地会议转录后总结

不足：

- 功能重点仍在会议纪要生成
- 与你需要的“可复用通用能力 + MCP/Skill 编排 + 视频语义”还有明显距离

结论：

- **适合参考产品交互，不适合作为核心能力底座**

---

## 对你的目标工作流的映射建议

### 工作流 1：读取本地视频/音频与会议材料

建议：

- 本地文件访问由自定义 `filesystem/media` MCP 处理
- 文档解析优先接 `Docling` 或 `MarkItDown`

### 工作流 2：转写为带说话人和时间信息的文稿

建议：

- 核心组合：`WhisperX` + `pyannote-audio`

这是目前最成熟、最贴近需求的开源组合。

### 工作流 3：视频抽帧分析并融合会议材料总结

建议：

- 用 `ffmpeg` 做抽帧和切片
- 用 `VideoLLaMA3` 一类的视频多模态模型理解视频语义
- 用文档解析结果补充上下文
- 最终再交给总结层做跨模态融合

### 工作流 4：根据总结内容响应用户要求

建议：

- 这一层不要绑死在某个单一模型项目里
- 由 Skill 负责调度：
  - 什么时候调用多模态模型
  - 什么时候只调用语言模型
  - 什么时候回查原始时间轴、发言人、材料段落

---

## 我给你的最终判断

### 可以直接拿来用的部分

- `WhisperX`
- `pyannote-audio`
- `Docling`
- `MarkItDown`
- `VideoLLaMA3`

### 不能直接依赖现成项目解决的部分

- 统一工作流编排
- MCP Server 边界设计
- Skill 调度逻辑
- 视频语义、转写结果、会议材料三者的融合策略
- 供宿主 Agent / 插件调用的稳定接口

### 最推荐路线

不要找“一体化现成项目”做底座，而是：

1. 选成熟开源能力模块
2. 自己封装成多个 MCP Server
3. 再写一个总调度 Skill
4. 把最终能力暴露给 Codex / GenMate 等宿主

---

## 当前推荐技术栈（第一版）

### 必选

- 转写：`WhisperX`
- 说话人分离：`pyannote-audio`
- 文档解析：`Docling`

### 可选增强

- 轻量文档转换：`MarkItDown`
- 视频语义理解：`VideoLLaMA3`

### 建议自研

- `media_ingest_mcp`
- `transcription_mcp`
- `document_parse_mcp`
- `video_semantic_mcp`
- `meeting_orchestrator` Skill

---

## 参考链接

- WhisperX: https://github.com/m-bain/whisperX
- pyannote-audio: https://github.com/pyannote/pyannote-audio
- Docling: https://github.com/docling-project/docling
- MarkItDown: https://github.com/microsoft/markitdown
- VideoLLaMA3: https://github.com/DAMO-NLP-SG/VideoLLaMA3
- Transcription Stream: https://github.com/transcriptionstream/transcriptionstream
- meeting-minutes: https://github.com/Zackriya-Solutions/meeting-minutes
