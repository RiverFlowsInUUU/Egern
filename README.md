<div align="center">

# 🛡️ Egern 防 DNS 泄露配置模板

### 让 DNS 无处可漏

*不绑定节点，不绑定订阅。只做一件事：消除 DNS 泄露面。*

[![Egern](https://img.shields.io/badge/Egern-Client-1f6feb?style=flat-square)](https://github.com/RiverFlowsInUUU/egern-anti-dns-leak)
[![DNS](https://img.shields.io/badge/DNS-Zero%20Leak-2ea043?style=flat-square)](https://github.com/RiverFlowsInUUU/egern-anti-dns-leak)
[![Profiles](https://img.shields.io/badge/Profiles-v2.4%20%7C%20v0-0969da?style=flat-square)](https://github.com/RiverFlowsInUUU/egern-anti-dns-leak)
[![Groups](https://img.shields.io/badge/Groups-27-8250df?style=flat-square)](https://github.com/RiverFlowsInUUU/egern-anti-dns-leak)
[![License](https://img.shields.io/badge/License-MIT-dfb317?style=flat-square)](docs/10-图标与许可.md)

[快速开始](#-快速开始) · [文件结构](#-文件结构) · [两个版本](#-两个版本) · [防泄露原理](#-防泄露原理) · [分流组结构](#-分流组结构) · [规则优先级](#-规则优先级) · [规则来源](#-规则来源) · [更多文档](#-更多文档)

</div>

<table align="center">
  <tr>
    <td align="center" width="33%">
      🔒<br><b>零明文 DNS</b><br><sub>启动期 / 节点解析 / 业务解析<br>三条路径都不碰 UDP:53</sub>
    </td>
    <td align="center" width="33%">
      🧩<br><b>不绑节点与订阅</b><br><sub>填两个订阅地址即可导入<br>换订阅不用改一行</sub>
    </td>
    <td align="center" width="33%">
      🎯<br><b>27 组完整分流</b><br><sub>AI / 流媒体 / 地区组齐全<br>规则集按天自动刷新</sub>
    </td>
  </tr>
</table>

---

## 🚀 快速开始

```
1️⃣ 挑配置   →   profiles/v2.4.yaml（推荐）
2️⃣ 填订阅   →   Airport-A / Airport-B 的 urls
3️⃣ 填节点   →   proxies 段（可选）
4️⃣ 导入     →   Egern
```

| 位置 | 怎么填 | 必填 |
|:-----|:-------|:----:|
| 两个订阅槽位的 `urls` | 占位 `sub.example.com` → 换成你的订阅地址 | ✅ |
| `proxies` | 占位 `[]` → 填你的自建节点 | ⬜ 可选 |

填完订阅即可导入，无需其他改动。

💡 只要防泄露、不要分流？改用 `profiles/v0.yaml`（极简懒人版）—— 它没有订阅槽位，需要自己填 `Proxy` 节点。

---

## 📁 文件结构

```
egern-anti-dns-leak/
├── 📁 profiles/            # 14 份配置（2 个可选版本 + 5 份旧版，各有带注释 / 纯配置两份）
├── 🖼️ icons/               # 分流组图标（已内置，不跨项目引用）
├── 📚 docs/                # 10 篇专题（原理 / 清单 / 谱系 / 版本沿革 / 审计读数 / 注意事项 等）
├── 📘 DetailsReadme/       # 完整技术文档
├── 🗓️ CHANGELOG.md         # 更新日志（按时间倒序）
└── 🧪 skill/               # 方法论（SKILL.md + reference/）+ 审计脚本 + 回归测试
```

---

## 📦 两个版本

只有两个可选版本。其余 `profiles/*.yaml` 都是 `v2.4` 的历代旧版，保留以备对照。

| 版本 | 策略组 | 规则 | 槽位 | 定位 |
|:----:|:------:|:----:|:----:|:-----|
| ⭐ **`v2.4`** | 27 | 24 | 2 | **推荐** · 完整分流 |
| 🪶 `v0` | 4 | 9 | 0 | 极简懒人版 · 只做防泄露 |

- ⭐ **`v2.4`** —— AI / 流媒体 / 地区组齐全。21 条 `rule_set` 带 `update_interval: 86400`，规则集按天自动刷新。
- 🪶 **`v0`** —— 只留 `Proxy` / `AI` / `AD` / `Final` 四个组。没有订阅槽位，`Proxy` 必须自己填节点。
- 📄 **两份形态** —— `.yaml`（带注释）与 `.min.yaml`（纯配置）内容一致，只差注释，取用其一即可。

旧版 `v1` → `v2.3` 的逐版差异、各版组 / 规则数与实测读数 → [`docs/07-文件版本沿革.md`](docs/07-文件版本沿革.md)。

> ⚠️ 文件名 `v0`…`v2.4` 是**文件版本**；[`docs/06`](docs/06-实测数据与版本谱系.md) 的「配置迭代谱系 v1~v10」是另一个维度。

---

## 🌐 防泄露原理

Egern 有两套 DNS。

| DNS | 负责 | 上游怎么选 |
|:---:|:-----|:-----------|
| 🌍 **默认 DNS** | 业务流量解析 | 按 `dns.forward` 匹配；未命中回退 `bootstrap` |
| 🔐 **代理 DNS** | 只解析节点 `server` 里的域名 | `dns.proxy_nameservers`，**强制直连** |

泄露只有一条出口：明文 `UDP:53` 的 `bootstrap`。三条原则让它无事可做：

- 🔌 **端点全写 IP 字面量** —— `upstreams` / `proxy_nameservers` 里没有任何主机名，没有待解析的目标。
- 🔗 **`no_resolve` 成对交付** —— 所有 IP 类规则带 `no_resolve`；用一份纯域名规则集（`direct.txt`，11 万条）补回域名判定。
- 🪃 **`forward` 塌缩为兜底** —— 配了 `proxy_nameservers` 后代理 DNS 会**跳过** `forward`，换订阅不用改一行。

启动期、节点域名解析、业务解析 —— 三条路径都不再接触明文 `:53`。

> 🔍 完整推导（含两个反直觉事实、兜底组「直连可达」判据）见 [`DetailsReadme` §2](DetailsReadme/DetailsReadme.md#2-防泄露原理从机制到推导) 与 [`docs/02`](docs/02-DNS为什么会泄露.md)。

---

## 🎯 分流组结构

以 **`v2.4`** 为例：27 个组 / 24 条规则。组与组可以互相引用，最终都收敛到 `Proxy` 或 `DIRECT`。

**✈️ 节点来源** —— 2 个订阅槽位

- 🅰️ `Airport-A` · `external` —— 订阅槽位 ①
- 🅱️ `Airport-B` · `external` —— 订阅槽位 ②（另带一条 `urls_disabled` 示例）

**🎛️ 核心组**

- 🧭 `Proxy` · `select` —— 主入口，手动选路（默认列出 `MAX` / `Smart` / 各地区）
- 🧠 `Smart` · `smart` —— 智能选优，上游 `Airport-A` · `B`
- ⚡ `MAX` · `smart` —— 带节点筛选的 `Smart`，只留**倍率 < 1** 的节点
- 🪣 `Final` · `select` —— 兜底组，未命中规则的流量走这里
- 🛑 `AD` · `select` —— 广告拦截，默认 `REJECT`，想临时放行切 `DIRECT`

**🤖 AI 组**

- 🧩 `AI` · `smart` —— 总入口，指向 `Proxy`，承接 `AI.list`
- 💬 `ChatGPT` · `fallback` —— 故障转移，`Proxy` + `flatten: true`
- ✨ `Gemini` · `fallback` —— 同上（`Google` 组首项，默认选中）
- 🧠 `Claude` · `smart` —— 默认指向 `Taiwan`

**🌍 地区组** —— `smart` + `filter` 正则，上游均为 `Airport-A` · `B`

| 策略组 | 筛选关键词（节选） |
|:-------|:------------------|
| 🇭🇰 `Hong Kong` | 香港 / HK / HKG |
| 🇺🇸 `USA` | 美国 / USA / LAX / SJC … |
| 🇯🇵 `Japan` | 日本 / 东京 / NRT / KIX … |
| 🇹🇼 `Taiwan` | 台湾 / TW / TPE |
| 🇸🇬 `Singapore` | 新加坡 / SG / SIN |
| 🇰🇷 `Korea` | 韩国 / KR / ICN |
| 🗺️ `Other Regions` | **负向断言**：排除以上全部 |

**🛎️ 服务组** —— 下列各组均承接同名规则集

- 🎵 `Spotify` · `YouTubeMusic` · `YouTube` —— 走 `Proxy`
- 🐙 `GitHub` —— 走 `Proxy`
- 🔎 `Google` —— 走 `Gemini` → `Proxy`
- 🪟 `Microsoft` —— 走 `DIRECT` → `Proxy`
- ✈️ `Telegram` · `Twitter` —— 走 `Proxy`
- 💚 `WeChat` —— 走 `DIRECT`

> 🧩 `flatten` 的含义、`MAX` 的筛选正则、`Other Regions` 负向断言的维护、`v0` 的专属调整 —— 见 [`DetailsReadme` §1.3](DetailsReadme/DetailsReadme.md#13-policy_groups--四种类型组间引用图标)。

---

## 📋 规则优先级

`rules` 是**有序的** —— 自上而下匹配，**第一条命中即决定去向**，后面的不再看。

| 分类 | 规则 / 规则集 | 去向 |
|:-----|:--------------|:----:|
| 🛡️ ① 白名单守卫 | `jinx white-guard` | 直连 |
| 🚫 ② 广告拦截 | `jinx ads` / `AWAvenue` | 拒绝 |
| 🏠 ③ 内网直连 | `Lan` | 直连 |
| 🤖 ④ AI 分流 | `OpenAI` / `Gemini` / `Anthropic` / `Claude` / `AI.list` | `AI` 组 |
| 🎵 ⑤ 流媒体 | `Spotify` / `YouTubeMusic` / `YouTube` | 代理 |
| 🔧 ⑥ 科技服务 | `GitHub` / `Google` / `Microsoft` | 代理 |
| 💬 ⑦ 社交 | `Telegram` / `Twitter` | 代理 |
| 🍎 ⑧ Apple 服务 | `Apple_All_No_Resolve` | 直连 |
| 🫧 ⑨ 微信 | `WeChat` | 直连 |
| 🇨🇳 ⑩ 国内直连 | `direct.txt` + `.cn` 后缀 | 直连 |
| 🌏 ⑪ GeoIP CN | 中国 IP（`no_resolve`） | 直连 |
| 🌐 ⑫ 兜底 | `default` | `Final` |

> 📌 完整的 24 条逐条清单见 [`DetailsReadme` §1.4](DetailsReadme/DetailsReadme.md#14-rules--匹配表与直连规则集)。

---

## 📚 规则来源

- 🧩 [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) —— 各分区规则集（ChatGPT / Google / Telegram …）
- 🤖 [ACL4SSR/ACL4SSR](https://github.com/ACL4SSR/ACL4SSR) —— `AI.list`
- 🇨🇳 [Loyalsoldier/surge-rules](https://github.com/Loyalsoldier/surge-rules) —— `direct.txt`，国内直连主力（11 万条纯域名）
- 🗺️ [Loyalsoldier/geoip](https://github.com/Loyalsoldier/geoip) —— `Country.mmdb` / `GeoLite2-ASN.mmdb`
- 🛑 [TG-Twilight/AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule) —— 广告拦截
- 🛡️ [RiverFlowsInUUU/jinx-ads-rules](https://github.com/RiverFlowsInUUU/jinx-ads-rules) —— 白名单守卫 + 广告拦截

---

## 📖 更多文档

- 📊 [`docs/08-审计读数.md`](docs/08-审计读数.md) —— 5 个审计脚本的读数 · 2 条 `LOW` 的含义 · 回归测试
- ⚠️ [`docs/09-注意事项.md`](docs/09-注意事项.md) —— 使用前必看：`v0` 的 `Proxy` · 规则集刷新 · 刻意不挂 CI
- 🎨 [`docs/10-图标与许可.md`](docs/10-图标与许可.md) —— 图标来源 · MIT 许可 · 第三方版权
- 🗓️ [`CHANGELOG.md`](CHANGELOG.md) —— 更新日志（按时间倒序，遵循 Keep a Changelog）
- 📘 [`DetailsReadme/`](DetailsReadme/) —— 逐段详解 · 原理推导 · v1–v10 谱系 · 18 项审计清单 · 已知取舍 · FAQ
- 📂 [`docs/`](docs/) —— 其余 7 篇专题：DNS 怎么工作 / 为什么泄露 / 加固清单 / 逐段讲解 / no_resolve 成对交付 / 实测谱系 / 文件版本沿革
- 🧪 [`skill/`](skill/) —— 审计脚本、回归测试与方法论

---

<div align="center">

🐈 让 DNS 无处可漏 · MIT License · [图标与许可](docs/10-图标与许可.md)

</div>
