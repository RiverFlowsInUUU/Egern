<div align="center">

# 🛡️ Egern 配置模板

*让 DNS 无处可漏*

[![Egern](https://img.shields.io/badge/Egern-iOS%20%7C%20macOS-1f6feb?style=flat-square)](https://github.com/RiverFlowsInUUU/Egern)
[![Profiles](https://img.shields.io/badge/Profiles-lazy%20%7C%20routing-0969da?style=flat-square)](https://github.com/RiverFlowsInUUU/Egern)
[![Groups](https://img.shields.io/badge/Groups-4%20%7C%2027-8250df?style=flat-square)](https://github.com/RiverFlowsInUUU/Egern)
[![DNS](https://img.shields.io/badge/DNS-Zero%20Leak-2ea043?style=flat-square)](https://github.com/RiverFlowsInUUU/Egern)
[![License](https://img.shields.io/badge/License-MIT-dfb317?style=flat-square)](docs/10-图标与许可.md)

</div>

## 📥 两全其美，皆合心意

🪶 **懒人版** · 至简 · 省心

```
https://raw.githubusercontent.com/RiverFlowsInUUU/Egern/main/profiles/lazy.min.yaml
```

🧭 **分流版** · 可控 · 随心

```
https://raw.githubusercontent.com/RiverFlowsInUUU/Egern/main/profiles/routing_v2.4.min.yaml
```

---

## 🧭 井然有序

懒人版 4 组、分流版 27 组，自上而下：

| 组 | 🪶 懒人版 | 🧭 分流版 |
|:---|:---:|:---:|
| 🚀 `Proxy` | ✅ | ✅ |
| ⚡ `Smart` | - | ✅ |
| 🤖 `ChatGPT` · `Gemini` · `Claude` · `AI` | ✅ | ✅ |
| 🎵 `Spotify` · 🎶 `YouTubeMusic` · ▶️ `YouTube` | - | ✅ |
| 🐙 `GitHub` · 🔎 `Google` · 🪟 `Microsoft` | - | ✅ |
| ✈️ `Telegram` · 🐦 `Twitter` · 💚 `WeChat` | - | ✅ |
| 🛑 `AD` | ✅ | ✅ |
| 🇭🇰 `Hong Kong` · 🇺🇸 `USA` · 🇯🇵 `Japan` · 🇨🇳 `Taiwan`<br>🇸🇬 `Singapore` · 🇰🇷 `Korea` · 🇦🇶 `Other Regions` | - | ✅ |
| 💧 `MAX` | - | ✅ |
| 🌐 `Final` | ✅ | ✅ |

> 🪶 懒人版无订阅槽位，`Proxy` 自己填节点，长期沿用无版本号。
> 🧭 分流版 = `routing_v2.4`（历代见 [`docs/07`](docs/07-文件版本沿革.md)），导入前填 2 处订阅槽位 `urls`（`Airport-A` / `Airport-B`）。
> 🔍 选路、地区筛法与规则顺序见 [`docs/04`](docs/04-模板逐段讲解.md)；带注释的原始文件见 [`profiles/`](profiles/)。

---

## 📋 分流顺序

自上而下匹配，第一条命中即决定去向。

| # | 匹配什么 | 🧭 分流版 | 🪶 懒人版 |
|:-:|:-----|:--------|:------|
| 🛡️ | 白名单域名 | 直连 | 同左 |
| 🚫 | 广告域名 | `AD` | 同左 |
| 🏠 | 内网 | 直连 | 同左 |
| 🤖 | 按应用 | 13 类应用各自成组 | AI 服务 → `AI` |
| 🍎 | Apple 服务 | 直连 | ✂️ 无 |
| 💚 | 微信 | 直连 | ✂️ 无 |
| 🇨🇳 | 国内域名 | 直连 | 同左 |
| 🌏 | 国内 IP | 直连 | 同左 |
| 🌐 | 其余全部 | `Final` | `Final` |

**应用组的默认出口**

| 应用组默认出口 | 备注 |
|:---------------|:-----|
| 🤖 `ChatGPT` · `Gemini` · `AI` | 走 `Proxy` |
| 🎭 `Claude` | 中国台湾，首项 `Taiwan` |
| 🔎 `Google` | 首项 `Gemini` → `Proxy` |
| 🎵 `Spotify` · 🎶 `YouTubeMusic` · ▶️ `YouTube` | 走 `Proxy` |
| ✈️ `Telegram` · 🐦 `Twitter` | 走 `Proxy` |
| 🐙 `GitHub` | 走 `Proxy` |
| 🪟 `Microsoft` | 直连，首项 `DIRECT` |
| 💚 `WeChat` | 直连，把微信从兜底里摘出来 |

> ⚠️ 白名单必须排在最前，顺序不可调整。

---

## 🌐 隐私至上 · 无 DNS 泄露

| | |
|:--|:--|
| 🚫 设备硬编码的明文 `:53` | `hijack_dns: '*'` 全量接管 |
| 🔐 解析上游 | 4 个加密端点（DoH + DoT × 2 机构），全部 IP 字面量 |
| 🛡️ 明文回退 | catch-all 兜住全部域名，永不落到 `bootstrap` |
| 🧭 节点域名 | `proxy_nameservers` 专用通道、强制直连，与业务解析分离 |
| 🧩 规则匹配 | IP 类规则带 `no_resolve`；域名直连规则与之成对交付 |
| 📋 审计读数 | 自带审计脚本 **0 high** · 路由覆盖 **15/15** |

> 🔍 完整推导见 [`DetailsReadme` §2](DetailsReadme/DetailsReadme.md#2-防泄露原理从机制到推导) 与 [`docs/02`](docs/02-DNS为什么会泄露.md)。

---

## 📁 文件结构

| | 路径 | 内容 |
|:--:|:-----|:-----|
| 📁 | [`profiles/`](profiles/) | 14 份配置：lazy + routing_v1~v2.4，各含带注释 / 纯配置 |
| 🖼️ | [`icons/`](icons/) | 策略组图标 |
| 📚 | [`docs/`](docs/) | 11 篇专题 |
| 📘 | [`DetailsReadme/`](DetailsReadme/DetailsReadme.md) | 完整技术文档 |
| 🗓️ | [`CHANGELOG.md`](CHANGELOG.md) | 版本记录 |
| 🧪 | [`skill/`](skill/) | 审计脚本 + 回归测试 |

---

## 📖 更多文档

- 📘 [`DetailsReadme/`](DetailsReadme/) —— 逐段详解 · 原理推导 · 配置迭代谱系 f1–f10 · 18 项审计清单 · 已知取舍 · FAQ
- 📂 [`docs/`](docs/) —— 全部 11 篇：DNS 怎么工作 / 为什么泄露 / 加固清单 / 逐段讲解 / `no_resolve` 成对交付 / 实测谱系 / 文件版本沿革 / 审计读数 / 注意事项 / 图标与许可 / 规则集与来源
- 📚 [`docs/11`](docs/11-规则集与来源.md) —— 规则集与来源
- ⚠️ [`docs/09`](docs/09-注意事项.md) —— 使用前必看
- 🎨 [`docs/10`](docs/10-图标与许可.md) —— 图标与许可
- 🧪 [`skill/`](skill/) —— 审计脚本 · 回归测试 · 方法论
- 🗓️ [`CHANGELOG.md`](CHANGELOG.md)

---

<div align="center">

🐈 让 DNS 无处可漏 · MIT License · [图标与许可](docs/10-图标与许可.md)

</div>
