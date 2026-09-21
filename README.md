<div align="center">

# 🛡️ Egern 防 DNS 泄露配置

**让 DNS 无处可漏**

*不绑节点，不绑订阅*

[![Egern](https://img.shields.io/badge/Egern-iOS%20%7C%20macOS-1f6feb?style=flat-square)](https://github.com/RiverFlowsInUUU/egern-anti-dns-leak)
[![DNS](https://img.shields.io/badge/DNS-Zero%20Leak-2ea043?style=flat-square)](https://github.com/RiverFlowsInUUU/egern-anti-dns-leak)
[![Profiles](https://img.shields.io/badge/Profiles-v2.5%20%7C%20v0-0969da?style=flat-square)](https://github.com/RiverFlowsInUUU/egern-anti-dns-leak)
[![Groups](https://img.shields.io/badge/Groups-27%20%7C%204-8250df?style=flat-square)](https://github.com/RiverFlowsInUUU/egern-anti-dns-leak)
[![License](https://img.shields.io/badge/License-MIT-dfb317?style=flat-square)](docs/10-图标与许可.md)

</div>

## 📥 两份配置

⭐ **v2.5** · 完整分流（推荐）

```
https://raw.githubusercontent.com/RiverFlowsInUUU/egern-anti-dns-leak/main/profiles/v2.5.min.yaml
```

🪶 **v0** · 一个出口

```
https://raw.githubusercontent.com/RiverFlowsInUUU/egern-anti-dns-leak/main/profiles/v0.min.yaml
```

选中一条，点右上角复制 → Egern **配置 → 从 URL 下载** → 粘贴。

---

## ⭐ v2.5

`profiles/v2.5.yaml` · `profiles/v2.5.min.yaml`

27 组 / 24 条规则。先按应用分，再按地区分。

**✈️ 节点来源** —— 2 个订阅槽位

- 🅰️ `Airport-A` · `external` · `smart` —— 订阅槽位 ①
- 🅱️ `Airport-B` · `external` · `smart` —— 订阅槽位 ②（另带一条 `urls_disabled` 示例）

| | |
|:--|:--|
| 🧭 `Proxy` | 主入口，手动选路（首项 `MAX`） |
| 🧠 `Smart` | 智能选优，`flatten` 展开到节点级 |
| ⚡ `MAX` | 带筛选的 `Smart`，只留倍率 < 1 |
| 🛑 `AD` | 手动开关（`REJECT` / `DIRECT`） |
| 🌐 `Final` | 兜底，未命中的流量走这里 |

**🤖 AI 组**

- 🧩 `AI` · `smart` —— 总入口，承接 `AI.list`
- 💬 `ChatGPT` · `fallback` —— `Proxy` + `flatten`，节点级故障转移
- ✨ `Gemini` · `fallback` —— 同上（`Google` 组首项，默认选中）
- 🧠 `Claude` · `smart` —— 默认指向 `Taiwan`

**🌍 地区组** —— `smart` + 正则筛节点，共 7 组

- 🇭🇰 `Hong Kong` · 🇺🇸 `USA` · 🇯🇵 `Japan` · 🇹🇼 `Taiwan` · 🇸🇬 `Singapore` · 🇰🇷 `Korea`
- 🗺️ `Other Regions` —— **负向断言**，排除以上全部

导入前只需填两处：订阅槽位的 `urls`（把占位 `sub.example.com` 换掉）· 可选填 `proxies` 自建节点。

---

## 🪶 v0

`profiles/v0.yaml` · `profiles/v0.min.yaml`

4 组 / 9 条规则。只做防泄露，不做分流。

| | |
|:--|:--|
| 🧭 `Proxy` | 唯一出口，空槽位需自己填 |
| 🤖 `AI` | AI 流量独立出口 |
| 🛑 `AD` | 只留 `REJECT`，想放行某域名加更靠前的直连规则 |
| 🌐 `Final` | 兜底（`Proxy`，已隐藏） |

没有订阅槽位，`Proxy` 必须自己填节点。

> 📄 **两份形态** —— `.yaml`（带注释）与 `.min.yaml`（纯配置）内容一致，只差注释，取用其一即可。
> 📦 其余 `profiles/*.yaml` 都是 `v2.5` 的历代旧版，保留以备对照 —— 逐版差异见 [`docs/07`](docs/07-文件版本沿革.md)。

---

## 📋 规则顺序

自上而下匹配，第一条命中即决定去向。

| # | 规则 | ⭐ v2.5 | 🪶 v0 |
|:-:|:-----|:--------|:------|
| 🛡️ | 白名单守卫 | `jinx white-guard` → `DIRECT` | 同左 |
| 🚫 | 广告拦截 | `jinx ads-delta` · `AWAvenue` → `AD` | `jinx ads` · `AWAvenue` → `AD` |
| 🏠 | 内网 | `Lan` → `DIRECT` | 同左 |
| 🤖 | 按应用 | 13 条，见下 | 1 条（`AI.list` → `AI`） |
| 🍎 | Apple 服务 | `Apple_All_No_Resolve` → `DIRECT` | ✂️ 无 |
| 💚 | 微信 | `WeChat` → `DIRECT` | ✂️ 无 |
| 🇨🇳 | 国内域名 | `direct.txt` + `.cn` 后缀 → `DIRECT` | 同左 |
| 🌏 | 国内 IP | `geoip: CN`（`no_resolve`）→ `DIRECT` | 同左 |
| 🌐 | 兜底 | `Final` | `Final` |

> 📌 上面是**分类**顺序。`v2.5` 里真正的匹配顺序在「按应用」之后还有一条 `Proxy.list`（`disabled: true`，不生效），随后才是 Apple → 微信。

**v2.5 的应用规则**

| 规则集 | 去向 |
|:-------|:-----|
| `OpenAI.list` | `ChatGPT` |
| `Gemini.list` | `Gemini` |
| `Anthropic.list` · `Claude.list` | `Claude` |
| `AI.list` | `AI` |
| `Spotify.list` | `Spotify` |
| `YouTubeMusic.list` | `YouTubeMusic` |
| `YouTube.list` | `YouTube` |
| `GitHub.list` | `GitHub` |
| `Google.list` | `Google` |
| `Microsoft.list` | `Microsoft` |
| `Telegram.list` | `Telegram` |
| `Twitter.list` | `Twitter` |
| `WeChat.list` | `WeChat` |

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

**三条排序约束**

1. 厂商专属规则（`OpenAI` / `Gemini` / `Anthropic` / `Claude`）排在 `AI.list` 之前，否则 AI 域名先被 `AI.list` 接走。
2. Apple / 微信排在 `direct.txt` 之前 —— 它们要抢在国内域名规则之前定去向。
3. `geoip: CN` 排最后，必须带 `no_resolve`，否则每个走到它的域名都会被强制本地解析一次。

---

## 🌐 防泄露原理

Egern 有两套 DNS。

| DNS | 负责 | 上游怎么选 |
|:---:|:-----|:-----------|
| 🌍 **默认 DNS** | 业务流量解析 | 按 `dns.forward` 匹配；未命中回退 `bootstrap` |
| 🔐 **代理 DNS** | 只解析节点 `server` 里的域名 | `dns.proxy_nameservers`，**强制直连** |

明文 `UDP:53` 只有 `bootstrap` 一条出口，而官方规定它有且只有两个用途：解析上游端点的主机名、作为最终回退。两条都堵上即可。

| 用途 | 机制 | 堵法 |
|:----:|:-----|:-----|
| 🚪 引导解析 | 端点写成主机名时，必须先明文解析一次 | `upstreams` / `proxy_nameservers` 全写 IP 字面量 |
| 🚪 最终回退 | 域名未命中 `forward` 时回退 `bootstrap` | 一条 `domain_wildcard: '*'` 的 catch-all 兜住全部域名 |
| 🚪 规则触发解析 | 不带 `no_resolve` 的 IP 类规则会主动发起解析 | IP 类规则一律带 `no_resolve`，另配 `direct.txt` 补回域名判定 |

启动期、节点域名解析、业务解析 —— 三条路径都不再接触明文 `:53`。

> 🔍 完整推导见 [`DetailsReadme` §2](DetailsReadme/DetailsReadme.md#2-防泄露原理从机制到推导) 与 [`docs/02`](docs/02-DNS为什么会泄露.md)。

---

## 📁 文件结构

```
egern-anti-dns-leak/
├── 📁 profiles/        # 16 份配置：v2.5 / v0 × 带注释 / 纯配置，另 6 份旧版
├── 🖼️ icons/           # 策略组图标
├── 📚 docs/            # 10 篇专题
├── 📘 DetailsReadme/   # 完整技术文档
├── 🗓️ CHANGELOG.md
└── 🧪 skill/           # 审计脚本 + 回归测试
```

---

## 📚 规则来源

- 🛑 [jinx-ads-rules](https://github.com/RiverFlowsInUUU/jinx-ads-rules) —— 广告拦截 · 白名单守卫
- 🧩 [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) —— 应用规则集
- 🤖 [ACL4SSR/ACL4SSR](https://github.com/ACL4SSR/ACL4SSR) —— `AI.list`
- 🇨🇳 [Loyalsoldier/surge-rules](https://github.com/Loyalsoldier/surge-rules) —— `direct.txt` · `Lan.list`
- 🗺️ [Loyalsoldier/geoip](https://github.com/Loyalsoldier/geoip) —— `Country.mmdb` · `GeoLite2-ASN.mmdb`
- 🛡️ [TG-Twilight/AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule) —— 广告拦截

---

## 📖 更多文档

- 📘 [`DetailsReadme/`](DetailsReadme/) —— 逐段详解 · 原理推导 · v1–v10 谱系 · 18 项审计清单 · 已知取舍 · FAQ
- 📂 [`docs/`](docs/) —— 全部 10 篇：DNS 怎么工作 / 为什么泄露 / 加固清单 / 逐段讲解 / `no_resolve` 成对交付 / 实测谱系 / 文件版本沿革 / 审计读数 / 注意事项 / 图标与许可
- ⚠️ [`docs/09`](docs/09-注意事项.md) —— 使用前必看
- 🎨 [`docs/10`](docs/10-图标与许可.md) —— 图标与许可
- 🧪 [`skill/`](skill/) —— 审计脚本 · 回归测试 · 方法论
- 🗓️ [`CHANGELOG.md`](CHANGELOG.md)

---

<div align="center">

🐈 让 DNS 无处可漏 · MIT License · [图标与许可](docs/10-图标与许可.md)

</div>
