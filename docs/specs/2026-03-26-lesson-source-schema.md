# Lesson Source Schema Design

Date: 2026-03-26

Status: Draft for review

## Goal

定义一个统一、可扩展、可批量导入的 lesson 输入格式，用来替代当前写死在 `scripts/generate_study_demo_assets.py` 里的示例数据。

这个 schema 的职责是描述“课程源数据”，而不是最终前端消费的生成结果。

## Current Context

当前学习页链路分成两层：

1. 源数据层
   - 现在并不存在单独的 lesson 源文件
   - 示例 lesson 直接内嵌在 `scripts/generate_study_demo_assets.py` 的 `LESSONS` 常量里

2. 生成结果层
   - `data/study_demo_catalog.json`
   - `data/study_demo_word_lookup.json`
   - `media/study-demo/<lesson-id>/lesson.mp4`
   - `media/study-demo/<lesson-id>/sentence-*.wav`

这导致几个问题：

- 新增 lesson 必须改 Python 脚本源码
- lesson 数据和生成逻辑耦合
- 未来无法方便支持 `srt/json/csv` 导入
- 不利于扩容到 9 个以上 lesson

## Design Principles

### 1. Source of Truth Must Be Files

lesson 原始输入必须是独立文件，而不是内嵌在脚本里。

### 2. Source Schema And Generated Schema Must Be Different

源 schema 用于人工编写和导入；
生成 schema 用于前端直接消费。

不要把前端字段原样拿来当编辑格式，否则会让人工维护过于笨重。

### 3. One Lesson, One Directory

每个 lesson 使用独立目录，目录中既包含元数据，也包含可选的字幕和媒体引用。

### 4. Progressive Enrichment

schema 必须允许从“只有句子文本”逐步升级到“带时间轴、带音频、带视频、带词级时间”的 richer lesson，而不破坏已有格式。

### 5. Static-Site Friendly

最终生成结果仍然适配当前静态站，不要求上后端。

## Proposed Directory Structure

新增目录：

```text
lessons/
  primary-school-morning/
    lesson.json
  junior-spring-city/
    lesson.json
  senior-learning-doors/
    lesson.json
```

后续如果需要原始字幕文件，也允许这样扩展：

```text
lessons/
  some-lesson/
    lesson.json
    subtitles.en.srt
    subtitles.zh.srt
    source-notes.md
```

## Proposed Source Schema

每个 lesson 使用一个 `lesson.json`。

### Top-Level Shape

```json
{
  "schemaVersion": 1,
  "id": "primary-school-morning",
  "stage": "primary",
  "title": "My School Morning",
  "subtitle": "小学示范课",
  "summary": "用小学阶段高频词做一个早晨上学场景练习。",
  "displayOrder": 10,
  "audioMode": "generated-per-sentence",
  "videoMode": "generated-slide-video",
  "source": {
    "type": "manual"
  },
  "sentences": [
    {
      "id": "s1",
      "en": "I walk to school with my best friend.",
      "zh": "我和我最好的朋友走路去学校。"
    }
  ]
}
```

## Field Definitions

### Required Top-Level Fields

- `schemaVersion`
  - integer
  - 当前固定为 `1`
  - 用于未来兼容升级

- `id`
  - string
  - 全仓库唯一
  - kebab-case
  - 同时作为目录名和生成产物名的一部分

- `stage`
  - enum
  - 允许值：
    - `primary`
    - `junior`
    - `senior`
    - `cet4`
    - `cet6`
    - `advanced`
    - `extended`

- `title`
  - string
  - 英文 lesson 标题

- `subtitle`
  - string
  - 短中文说明或课型标记

- `summary`
  - string
  - 用于学习页卡片说明

- `sentences`
  - array
  - 至少 1 条

### Optional Top-Level Fields

- `displayOrder`
  - integer
  - 同 stage 内排序
  - 缺省时由文件名或读取顺序补位

- `audioMode`
  - enum
  - 当前建议值：
    - `generated-per-sentence`
    - `recorded-per-sentence`
    - `external-track`

- `videoMode`
  - enum
  - 当前建议值：
    - `generated-slide-video`
    - `external-video`
    - `none`

- `source`
  - object
  - 描述 lesson 数据来源
  - 例：
    - `{"type":"manual"}`
    - `{"type":"csv-import","file":"sentences.csv"}`
    - `{"type":"srt-import","enFile":"subtitles.en.srt","zhFile":"subtitles.zh.srt"}`
    - `{"type":"manual","video":"clip.mp4"}`

- `tags`
  - array of string
  - 可选主题标签，如 `school`, `weather`, `habit`

## Sentence Schema

### Minimum Required Sentence Fields

```json
{
  "id": "s1",
  "en": "I walk to school with my best friend.",
  "zh": "我和我最好的朋友走路去学校。"
}
```

字段要求：

- `id`
  - string
  - lesson 内唯一
  - 建议 `s1`, `s2`, `s3`

- `en`
  - string
  - 英文句子

- `zh`
  - string
  - 中文对译

### Optional Sentence Fields

- `start`
  - number
  - 句子开始时间，单位秒

- `end`
  - number
  - 句子结束时间，单位秒

- `audio`
  - string
  - 如果已有现成句子音频，可直接引用相对路径

- `tokens`
  - array of string
  - 手工指定分词结果
  - 缺省时由导入脚本自动分词

- `notes`
  - string
  - 可选教师备注或导入备注

- `words`
  - array
  - 预留给未来的词级时间轴
  - 当前不要求实现

词级时间轴预留格式：

```json
{
  "id": "s1",
  "en": "I walk to school with my best friend.",
  "zh": "我和我最好的朋友走路去学校。",
  "words": [
    { "text": "I", "start": 0.00, "end": 0.18 },
    { "text": "walk", "start": 0.18, "end": 0.52 }
  ]
}
```

## Validation Rules

导入脚本至少要做这些校验：

- `schemaVersion` 必须存在且当前为 `1`
- `id` 必须与 lesson 目录名一致
- `stage` 必须属于允许枚举
- `title` / `subtitle` / `summary` 不能为空
- `sentences` 不能为空
- 每条 sentence 必须有唯一 `id`
- 每条 sentence 必须有非空 `en` 和 `zh`
- 如果提供 `start` / `end`，必须满足：
  - `start >= 0`
  - `end > start`
  - 句子顺序不倒退
- 如果提供 `audio`，文件必须存在

## Generation Rules

导入和生成链路按下面的原则工作：

### If timing is absent

- 脚本可根据句子音频时长自动补 `start/end/duration`
- 若无音频，则可先生成音频再推导时间轴

### If timing is present

- 以源文件时间轴为准
- 不再覆盖

### If tokens are absent

- 由脚本自动英文分词生成

### If stage label is absent

- 不在源 schema 中保存 `stageLabel`
- 由导出阶段根据 `stage` 和全局配置生成

### If generated asset paths are absent

- 不要求源文件保存最终 `./media/...` 路径
- 这些属于生成结果层，应由 pipeline 写入 `study_demo_catalog.json`

## Explicit Separation: Source vs Output

### Source Schema Should Contain

- 教学意义上的内容
- 课程元数据
- 可选时间轴
- 可选已有音频引用
- 可选导入来源说明

### Source Schema Should Not Contain

- `stageLabel`
- `duration` 总课时
- 前端专用相对资源 URL
- 词书 lookup 结果
- 自动生成的 token 列表（可选但不强制）
- 统计字段

这些都应由构建脚本生成。

## Migration Plan For Existing Demo Lessons

M3-A 的完成标准之一，是把当前 3 个示例 lesson 迁移到新 schema：

- `primary-school-morning`
- `junior-spring-city`
- `senior-learning-doors`

迁移时：

- 先按最小 schema 写入 `lesson.json`
- 先不手写 `start/end`
- 先不手写 `tokens`
- 继续允许由生成脚本根据句子音频推导输出

这样可以最小成本完成迁移。

## Non-Goals

本阶段明确不做：

- 不定义完整后台数据库模型
- 不做用户学习记录 schema
- 不做神经 TTS 供应商配置 schema
- 不做多语言 UI 配置系统
- 不强制引入真实词级时间轴

## Risks

### 1. Schema Too Close To Current Demo

如果 schema 完全照搬当前前端输出，就会继续把生成层和源数据层耦合。

### 2. Schema Too Abstract

如果一开始设计得过于通用，会导致导入脚本复杂度过高。

### 3. Timing Variants

未来可能同时出现：

- 无时间轴
- 句级时间轴
- 词级时间轴

所以 schema 必须允许渐进式增强，而不是一次性绑定最复杂格式。

## Recommendation

采用“最小 lesson source schema + 渐进增强”的设计。

第一版只强制：

- lesson 元数据
- 英文句子
- 中文句子

时间轴、音频引用、词级时间信息都作为可选增强字段。

这样最适合当前仓库阶段，也最利于尽快进入 `import_lessons.py` 的实现。

## Approval Gate

如果这份 spec 没问题，下一步就是：

1. 写 `import pipeline` implementation plan
2. 再实现 `scripts/import_lessons.py`
