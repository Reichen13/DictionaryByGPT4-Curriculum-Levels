# Superpowers Roadmap Review

Date: 2026-03-26

Source of review:

- `obra/superpowers` repository
- Core skills reviewed: `using-superpowers`, `brainstorming`, `writing-plans`

## Executive Summary

当前路线图方向是对的，但还偏“产品待办列表”，不够“工程执行系统”。

按照 Superpowers 的方法，这个项目接下来最重要的补充不是再增加一批功能，而是把后续开发组织成：

1. 先写 spec
2. 再写 implementation plan
3. 再分步执行
4. 每步都验证
5. 每个里程碑只解决一个清晰边界的问题

这意味着：

- `ROADMAP.md` 可以保留为产品路线图
- 但每个下一阶段都应该拆成独立 spec 和独立 plan，而不是直接进编码

## What Superpowers Would Likely Keep

以下判断基本不需要改：

- 先做 lesson 导入和内容生产链，而不是继续零散修 UI
- 先把静态站的内容生产能力做好，再考虑更复杂的后台
- 神经 TTS 不应优先于内容生产链
- 当前产品已经跨过“玩具 Demo”阶段，但还没有跨过“可规模化维护”阶段

## Key Additions From Superpowers

### 1. 把 M3 再拆成三个独立子项目

当前 M3 叫“内容生产链”，方向对，但范围还是太大。

建议拆成：

#### M3-A Lesson Source Schema

目标：

- 定义 lesson 原始输入格式

产物：

- `docs/specs/lesson-source-schema.md`
- `lessons/*.json` 或 `imports/*.json`
- 字段规范、时间字段规范、资源路径规范

完成标准：

- 任何新 lesson 都能按统一格式描述

#### M3-B Import Pipeline

目标：

- 把原始 lesson 输入转换成前端可消费的数据

产物：

- `scripts/import_lessons.py`
- 生成后的 catalog / lookup / media manifest
- 对错误输入的清晰报错

完成标准：

- 不手改 `study.html`
- 不手改主 catalog JSON

#### M3-C Lesson Expansion

目标：

- 用前两个子项目真正补出更多 lesson

产物：

- 至少 9 个 lesson

完成标准：

- 小学 3、初中 3、高中 3
- 全部可以在学习页切换和学习

这三个阶段比一个大 M3 更符合 Superpowers 的“单一边界、可验证、可交付”要求。

### 2. 每个子项目都要先写 spec，再写 plan

Superpowers 强调：

- 粗想法不能直接变实现
- 先把设计写清楚，再写任务计划

对这个项目的实际做法应该是：

#### 对 M3-A

- 先写 lesson schema spec
- 再写 import/生成逻辑计划

#### 对 M3-B

- 先写 pipeline spec
- 再写逐步 implementation plan

#### 对 M3-C

- 先写内容扩容 spec
- 再补课程数据

建议目录：

- `docs/specs/`
- `docs/plans/`

## 3. “未来路线图”里要增加验证门槛

当前路线图里对“做完”的定义还偏产品角度。

Superpowers 风格会额外补这些验证门槛：

- 生成脚本必须有最小测试覆盖
- 关键 JSON 输出必须有 schema 校验
- lesson 导入失败必须有明确错误信息
- 页面必须能在本地静态服务器下完成最小 smoke test
- 新增 lesson 不应要求修改前端模板文件

## 4. 不要把“更拟人 TTS”写成单一大项

这个方向也建议拆开：

#### TTS-A Audio Source Abstraction

- 前端先支持多个音频源
- 本地录音 / 浏览器 TTS / 神经 TTS 用统一接口切换

#### TTS-B Offline Audio Generation

- 选择一个神经 TTS 服务
- 批量生成句子音频

#### TTS-C Quality / Cost Policy

- 哪些 lesson 用神经音频
- 哪些仍保留浏览器 TTS
- 如何控制仓库体积和成本

这样做比直接“接入更真人的声音”更稳。

## 5. 增加“工作方式路线图”

Superpowers 的重点不只是做什么，还包括怎么做。

建议补一个轻量执行规则：

### For every next milestone

1. Brainstorm and agree on scope
2. Write a design spec
3. Review the spec
4. Write an implementation plan
5. Execute in small verified steps
6. Review before declaring done

这能防止项目重新回到“想到什么改什么”的状态。

## Recommended Next Sequence

结合当前项目状态，Superpowers 风格下最合理的下一步顺序应为：

1. 写 `M3-A lesson schema spec`
2. 写 `M3-B import pipeline plan`
3. 实现 `import_lessons.py`
4. 用 pipeline 补 3 个小学 lesson
5. 再补初中和高中 lesson
6. 最后才考虑神经 TTS

## Concrete Recommendation

如果立刻进入下一轮开发，最建议做的不是继续改 `study.html`，而是先做这一个小目标：

### Next Target

定义统一的 lesson 输入格式，并让当前 3 个 demo lesson 全部迁移到这个格式。

这是当前最关键的基础设施。

原因：

- 它会直接决定课程能不能扩容
- 它会降低后续前端改动频率
- 它会让 TTS、字幕、导入、导出都建立在稳定数据模型上

## Bottom Line

Superpowers 对当前路线图最核心的补充可以浓缩成一句话：

把“路线图”进一步收敛成“一个个边界清晰、先设计、再计划、再验证的小项目”。
