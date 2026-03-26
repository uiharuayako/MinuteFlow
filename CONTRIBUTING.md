# Contributing to MinuteFlow

感谢你对 MinuteFlow 的关注。

这个项目当前聚焦于“本地优先的会议理解工作流”，包括：

- 媒体探测与音轨抽取
- 转写与可选说话人分离
- 会议材料解析
- 视频关键帧提取与可选视觉分析
- MCP Server 暴露与 Skill 编排

为了让贡献更容易合并，请优先遵循下面的约定。

## 开始之前

提交 issue 或 PR 之前，建议先确认：

- 你的改动与项目目标直接相关
- 改动范围尽量小而聚焦
- 不顺手修复无关问题
- 本地已经验证相关功能

如果你准备做较大的功能改动，建议先开一个 issue 讨论设计方向。

## 本地开发

### 环境要求

- Python `3.11+`
- `uv`
- `ffmpeg`
- `ffprobe`

### 安装依赖

基础依赖：

```bash
uv sync
```

启用转写能力：

```bash
uv sync --extra transcription
```

安装测试依赖：

```bash
uv sync --group dev
```

### 本地检查

先检查运行环境：

```bash
uv run python -m minuteflow.cli doctor check
```

运行测试：

```bash
uv run python -m pytest -q
```

如果你在调试端到端流程，建议先关闭视觉分析和 LLM 总结，缩小排查范围：

```bash
uv run minuteflow workflow run \
  --media /absolute/path/to/meeting.mp4 \
  --output-dir /absolute/path/to/output \
  --no-visual \
  --no-summary
```

## 代码风格

请尽量保持与现有代码一致：

- 以小步提交为主
- 优先修复根因，而不是做表层绕过
- 避免无关重构
- 命名清晰，避免单字母变量
- 非必要不要增加内联注释

如果你修改了命令行行为、配置项或调试流程，请同步更新 `README.md` 或相关文档。

## 测试建议

提交前尽量至少覆盖你改动相关的验证：

- CLI 改动：补充或更新 `tests/test_cli.py`
- 文档解析改动：补充或更新 `tests/test_documents.py`
- 媒体处理改动：补充或更新 `tests/test_media.py`
- 工作流输出改动：补充或更新 `tests/test_pipeline_rendering.py`

如果改动无法方便自动化测试，请在 PR 描述中写清：

- 改动目的
- 手工验证步骤
- 预期结果

## Pull Request 指南

建议在 PR 描述中包含以下内容：

- 背景和目标
- 主要改动点
- 是否影响 CLI / MCP / Skill / 输出格式
- 测试方式与结果
- 是否需要更新文档

小而清晰的 PR 更容易被 review 和合并。

## Issue 指南

提 issue 时，尽量提供：

- 操作系统与 Python 版本
- 安装命令
- 输入文件类型
- 复现步骤
- 完整报错信息
- 如适用，附上 `meeting_packet.json` 或 `transcript.json` 的关键信息

涉及模型配置时，也请说明是否配置了：

- `MINUTEFLOW_HF_TOKEN`
- `MINUTEFLOW_LLM_*`
- `MINUTEFLOW_MM_*`

## 许可证

提交到本仓库的贡献默认按 `Apache-2.0` 许可证分发。
