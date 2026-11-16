# AURORA Browser

Privacy-first Chromium with **engine-level environment customization** and **native AI Agent support**.

> 让浏览器环境由用户说了算：引擎级（C++ 源码层）实现，非脚本注入。为 AI Agent 提供零配置附着、拟人交互与身份管理。

## 项目文档

- [PROJECT-BOOK.md](PROJECT-BOOK.md) — 项目书 v1.1（目标 / 架构 / 需求清单 32 条 / 工程路线）
- [docs/P0-RESULT.md](docs/P0-RESULT.md) — P0 实验结论：官方测试开关路线不可行，源码补丁是唯一路

## 架构（三层）

| 层 | 内容 |
|---|---|
| L1 内核 | AURORA-chromium：AURORA-FP 环境配置引擎（C++ 补丁） |
| L2 扩展 | 第三方能力对接扩展 + 标准 Chrome 扩展生态 |
| L3 Agent 层 | CDP 遥控 / 拟人交互 / 礼貌访问 / profile 信誉 / 多身份管理 |

## 仓库结构

```
patches/aurora-fp/   引擎补丁集（C++，按 F1-F13 编号）
persona/             profile 配置文件（persona.json 格式）
docs/                实验记录与设计文档
.github/workflows/   免费公共 CI（probe / content_shell 构建）
```

## 构建策略（零成本）

- GitHub Actions 免费公共 runner（4 vCPU / 16 GB）
- 目标产物：`content_shell`（Chromium 裸内核，含完整 WebGL 栈）——验证补丁生效的最小载体
- 浅克隆源码 + 排除测试数据 + sccache 增量缓存

## 里程碑

- [x] P0：官方测试开关路线判定（不可行，源码补丁唯一路）
- [ ] 第 1 期：仓库骨架 + CI probe（本仓库）
- [ ] 第 2 期：content_shell 首次构建 + UNMASKED 值改写实证
- [ ] 第 3 期：F1-F8 全配置面 + 一致性守卫
- [ ] 第 4 期：L3 Agent 层集成
- [ ] 第 5 期：完整浏览器发布版

---
发起：小皇帝 · 工程：kuroneko 🪼 · 全链路免费资源（公共 CI + 免费模型池）
