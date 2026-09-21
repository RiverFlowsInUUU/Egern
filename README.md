# Egern 防 DNS 泄露配置模板

<p align="center">
  <img src="https://img.shields.io/badge/Egern-Client-1f6feb?style=flat-square" alt="Egern">
  <img src="https://img.shields.io/badge/DNS-Zero%20Leak-2ea043?style=flat-square" alt="DNS Zero Leak">
  <img src="https://img.shields.io/badge/License-MIT-dfb317?style=flat-square" alt="License MIT">
</p>

<p align="center">
  <b>面向 Egern 的防 DNS 泄露配置模板</b><br>
  <i>不绑定任何节点与订阅 —— 只做一件事：消除 DNS 泄露面</i>
</p>

<p align="center">
  <a href="#-快速开始">快速开始</a> •
  <a href="#-文件结构">文件结构</a> •
  <a href="#-四个版本">四个版本</a> •
  <a href="#-防泄露原理">防泄露原理</a> •
  <a href="#-分流组结构">分流组结构</a> •
  <a href="#-规则优先级">规则优先级</a> •
  <a href="#-审计读数">审计读数</a> •
  <a href="#️-注意事项">注意事项</a> •
  <a href="#-更新日志">更新日志</a>
</p>

---

## 🚀 快速开始

```
1. 挑一份配置   →  推荐 profiles/v2.1.yaml
2. 填节点       →  proxies 段（模板为空 []）
3. 补分流组     →  把空的 policies: [] 填上节点名 / 订阅组名
4. 导入 Egern   →  完成
```

**必须动手的两处**（不填则代理不通）：

| 位置 | 现状 | 填什么 |
|:----:|:----:|:------:|
| `proxies` | `[]` | 你的节点 |
| `policy_groups` 里空的 `policies` | `[]` | 节点名或订阅组名 |

订阅方式：把 `external` 组里的 `sub.example.com?token=REPLACE_WITH_YOUR_TOKEN` 换成你自己的订阅地址。

---

## 📁 文件结构

```
egern-anti-dns-leak/
├── profiles/
│   ├── v2.1.yaml        # 推荐 · 带注释
│   ├── v2.1.min.yaml    # 推荐 · 纯配置
│   ├── v2.yaml          # 保留 · 带注释（与 v2.1 逻辑等价）
│   ├── v2.min.yaml      # 保留 · 纯配置
│   ├── v1.yaml          # 旧版 · 带注释
│   ├── v1.min.yaml      # 旧版 · 纯配置
│   ├── v0.yaml          # 极简 · 带注释
│   └── v0.min.yaml      # 极简 · 纯配置
├── icons/               # 分流组图标（已内置，不跨项目引用）
├── docs/                # 6 篇专题（原理 / 清单 / 谱系）
├── DetailsReadme/       # 完整技术文档
└── skill/               # 审计脚本 + 回归测试
```

---

## 📦 四个版本

| 版本 | 策略组 | 规则 | 定位 |
|:----:|:------:|:----:|:-----|
| **`v2.1`** ⭐ | 29 | 24 | **推荐** · `v2` 的精简后继（少 52 行冗余） |
| `v2` | 29 | 24 | 保留原样 · 与 `v2.1` 逻辑逐项等价 |
| `v1` | 29 | 24 | 旧版 · `dns` 段 40 行，功能等价 |
| `v0` | 4 | 9 | 极简裁剪 · 只留 `Proxy` / `AI` / `AD` / `Final` |

- **同版本的两份**（`.yaml` 带注释 / `.min.yaml` 纯配置）**内容完全一致**，只差注释，取用其一即可。
- **`v1` 与 `v2.1` 的差别只在 `dns` 段**（40 行 vs 22 行），其余段逐行相同。防泄露能力经审计脚本实测**逐项等价**。
- **`v2.1` 与 `v2` 的差别只有 52 行**，且全是「值等于官方默认值」的冗余行（`ipv6: false` / `compat_route: false` / `include_all_networks: false` / `include_apns: false` / `flatten: false` / `hidden: false` / `disabled: false`）。这些值写与不写对 Egern 是**同一份配置**，所以两者逻辑**逐项等价** —— 4 个审计脚本的输出完全一致。
- ⚠️ 别把文件名 `v0` / `v1` / `v2` / `v2.1` 与 [`docs/06`](docs/06-实测数据与版本谱系.md) 里的 **v1~v10 迭代谱系**混淆 —— 前者是**文件版本**，后者是配置**自身的历史迭代**，两个维度。

---

## 🌐 防泄露原理

**Egern 有两套 DNS**，理解这一点就够了：

| DNS | 负责 | 上游怎么选 |
|:---:|:----:|:----------:|
| **默认 DNS** | 业务流量解析 | 按 `dns.forward` 匹配；未命中回退到 `bootstrap` |
| **代理 DNS** | 只解析节点 `server` 里的域名 | `dns.proxy_nameservers`，**强制直连**（代理还没通，不可能让它解析自己的地址） |

**泄露只有一条出口：明文 `UDP:53` 的 `bootstrap`。** 本模板用三条原则让它无事可做：

| # | 原则 | 做法 |
|:-:|:----:|:-----|
| ① | **端点全写 IP 字面量** | `upstreams` / `proxy_nameservers` 里没有任何主机名 ⇒ 没有待解析的目标 |
| ② | **`no_resolve` 成对交付** | 所有 IP 类规则带 `no_resolve`；代价是用一份纯域名规则集（`direct.txt`，11 万条）补回域名判定 |
| ③ | **`forward` 塌缩为兜底** | 配了 `proxy_nameservers` 后代理 DNS 会**跳过** `forward` ⇒ 换订阅不用改一行 |

启动期、节点域名解析、业务解析 —— 三条路径都不再接触明文 `:53`。

> 完整推导（含两个反直觉事实、兜底组「直连可达」判据）见 [`DetailsReadme` §2](DetailsReadme/DetailsReadme.md#2-防泄露原理从机制到推导) 与 [`docs/02`](docs/02-DNS为什么会泄露.md)。

---

## 🎯 分流组结构

以 **`v2.1`** 为例（29 个组 / 24 条规则）。**组与组可以互相引用**，最终都收敛到 `Proxy` 或 `DIRECT`。

> `v0` 只留 4 组 9 条，另有两处不同：`AD` 组**只有 `REJECT`**（没有 `DIRECT` 兜底）、`Final` 组**被隐藏**（`hidden: true`，它只有一个子策略 `Proxy`，没有手动切换的意义）。详见其文件内注释。

### ✈️ 节点来源

| 策略组 | 类型 | 说明 |
|:------:|:----:|:-----|
| `Airport-A` / `Airport-B` / `Airport-C` | `external` | 从订阅 URL 拉节点（模板是 `sub.example.com` 占位，**必须换成你的**） |
| `Airport-Free` | `smart` | 免费节点组，同样带订阅 URL |

### 🚀 核心组

| 策略组 | 类型 | 说明 |
|:------:|:----:|:-----|
| `Proxy` | `select` | **主入口** · 手动选路（默认列出 `MAX` / `Smart` / 各地区） |
| `Smart` | `smart` | 智能选优 · 组内多轮测速，按延迟 / 抖动 / 可靠性打分 |
| `MAX` | `smart` | 倍率筛选 · `filter: 0\.(?:01\|1)` |
| `Final` | `select` | **兜底组** · 所有未命中规则的流量走这里 |
| `AD` | `select` | 广告拦截 · 默认 `REJECT`，想临时放行切 `DIRECT`（`v0` 无此选项） |

### 🤖 AI 组

| 策略组 | 类型 | 说明 |
|:------:|:----:|:-----|
| `AI` | `smart` | **总入口** · 指向 `Proxy`，承接 `AI.list` |
| `ChatGPT` | `fallback` | 故障转移 · 按顺序取第一个可用（当前 `[]` 待填） |
| `Gemini` | `fallback` | 同上 |
| `Claude` | `smart` | 默认指向 `Taiwan` |

### 🌍 地区组（`smart` + `filter` 正则）

| 策略组 | 筛选关键词（节选） | 上游 |
|:------:|:------------------:|:----:|
| `Hong Kong` | 香港 / HK / HKG | Airport-A · B |
| `USA` | 美国 / USA / LAX / SJC … | Airport-A · B |
| `Japan` | 日本 / 东京 / NRT / KIX … | Airport-C · A · B |
| `Taiwan` | 台湾 / TW / TPE | Airport-A · B |
| `Singapore` | 新加坡 / SG / SIN | Airport-A · B |
| `Korea` | 韩国 / KR / ICN | Smart · Airport-A · B |
| `Other Regions` | **负向断言**：排除以上全部 | Airport-A · B |

> ⚠️ 「按正则把节点归类」是 **`filter`** 干的，不是 `smart` 本身 —— `smart` 只负责在筛出来的节点里选最优。

### 📦 服务组

| 策略组 | 默认策略 | 承接的规则集 |
|:------:|:--------:|:------------:|
| `Spotify` | `Proxy` | Spotify |
| `YouTubeMusic` | `Proxy` | YouTubeMusic |
| `YouTube` | `Proxy` | YouTube |
| `GitHub` | `Proxy` | GitHub |
| `Google` | `Gemini` → `Proxy` | Google |
| `Microsoft` | `DIRECT` → `Proxy` | Microsoft |
| `Telegram` | `Proxy` | Telegram |
| `Twitter` | `Proxy` | Twitter |
| `WeChat` | `DIRECT` | WeChat |

---

## 📋 规则优先级

`rules` 是**有序的** —— 自上而下匹配，**第一条命中即决定去向**，后面的不再看。

```
 1. 🛡️ 白名单守卫   jinx white-guard             → 直连
 2. 🚫 广告拦截     jinx ads / AWAvenue           → 拒绝
 3. 🏠 内网直连     Lan                           → 直连
 4. 🤖 AI 分流      OpenAI / Gemini / Anthropic / Claude / AI.list → AI 组
 5. 🎵 流媒体       Spotify / YouTubeMusic / YouTube → 代理
 6. 🔧 科技服务     GitHub / Google / Microsoft   → 代理
 7. 💬 社交         Telegram / Twitter            → 代理
 8. 🍎 Apple 服务   Apple_All_No_Resolve          → 直连
 9. 🫧 微信         WeChat                        → 直连
10. 🇨🇳 国内直连    direct.txt + .cn 后缀         → 直连
11. 🌏 GeoIP CN    中国 IP（no_resolve）          → 直连
12. 🌐 兜底        default                        → Final
```

> 完整的 24 条逐条清单见 [`DetailsReadme` §1.4](DetailsReadme/DetailsReadme.md#14-rules--匹配表与直连规则集)。

---

## ✅ 审计读数

本仓库自带审计脚本，可直接对模板运行（[`skill/scripts/`](skill/scripts/)）：

| 脚本 | 读数 |
|:----:|:----:|
| `check_egern_dns.py` | ✅ **0 high**（退出码 0），另有 2 条 `LOW` |
| `audit_ruleset_noresolve.py` | ✅ 全部通过（v1 / v2 / v2.1 各 21 个规则集 · v0 为 6 个） |
| `audit_routing_coverage.py` | ✅ 15/15 国内探针命中 `DIRECT` |
| `audit_dns_forward.py` | ✅ 通过（带 / 不带 `--drill` 都通过） |

**那 2 条 `LOW` 不是缺陷，是设计取舍** —— ① 设置了 `proxy_nameservers`（它成为代理侧解析的唯一出口）；② 兜底指向国内组（需要本地解析的境外域名会拿到国内答案，实际影响面仅限 `DIRECT` 域名）。详见 [`DetailsReadme` §6](DetailsReadme/DetailsReadme.md#6-已知代价与取舍)。

**回归测试**：`bash skill/tests/run.sh` —— 5 个 fixture × 2 个脚本 = 10 个断言，退出码非 0 即失败。

---

## 📚 规则来源

| 来源 | 用在哪 |
|:----:|:------:|
| [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) | 各分区规则集（ChatGPT / Google / Telegram …） |
| [ACL4SSR/ACL4SSR](https://github.com/ACL4SSR/ACL4SSR) | `AI.list` |
| [Loyalsoldier/surge-rules](https://github.com/Loyalsoldier/surge-rules) | `direct.txt` —— 国内直连主力（11 万条纯域名） |
| [Loyalsoldier/geoip](https://github.com/Loyalsoldier/geoip) | `Country.mmdb` / `GeoLite2-ASN.mmdb` |
| [TG-Twilight/AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule) | 广告拦截 |
| [RiverFlowsInUUU/jinx-ads-rules](https://github.com/RiverFlowsInUUU/jinx-ads-rules) | 白名单守卫 + 广告拦截 |

---

## ⚠️ 注意事项

| 项目 | 说明 |
|:----:|:-----|
| 🔗 **节点必填** | `proxies` 是空 `[]`，不填则代理不通 |
| 🎯 **分流组必填** | 空的 `policies: []` 要填节点名，否则 `Final → Proxy` 是断的 |
| 🧩 **`v0` 尤其注意** | 它只留 4 个组，`Proxy` 为空时**所有走代理的流量都不通** |
| 🧪 **自查方式** | 本仓库**刻意不挂 CI**（理由见 [`skill/README.md`](skill/README.md)）。改完 profile 请本地跑 `bash skill/tests/run.sh` + 4 个审计脚本 |
| 🔀 **命名歧义** | 文件名 `v0` / `v1` / `v2` / `v2.1` ≠ `docs/06` 的迭代谱系 `v1~v10` |

---

## 📖 更多文档

| 文档 | 内容 |
|:----:|:-----|
| [`DetailsReadme/`](DetailsReadme/) | 逐段详解 · 原理推导 · v1–v10 谱系 · 18 项审计清单 · 规则集开销实测 · 已知取舍 · FAQ |
| [`docs/`](docs/) | 6 篇专题：DNS 怎么工作 / 为什么泄露 / 加固清单 / 逐段讲解 / no_resolve 成对交付 / 实测谱系 |
| [`skill/`](skill/) | 审计脚本、回归测试与方法论 |

---

## 📝 更新日志

> 按时间倒序。⚠️ **这里一共有三个不同的「版本」维度，别混**：
> ① **文件版本** `v0` / `v1` / `v2` / `v2.1` —— 见上方 [📦 四个版本](#-四个版本)；
> ② **配置自身的迭代谱系** v1~v10 —— 见 [`docs/06`](docs/06-实测数据与版本谱系.md)；
> ③ **本节的日期** —— 仓库每次改动的记录。

### 2026-09-21

- 🆕 **新增 `v2.1`（推荐版）** —— `v2` 的精简后继：删掉 **52 行「值恰好等于官方默认值」**的冗余行
  （`ipv6: false` / `compat_route: false` / `include_all_networks: false` / `include_apns: false`、
  各组 `flatten: false` · `hidden: false`、各规则 `disabled: false`）。写与不写对 Egern 是**同一份配置**，
  已用 4 个审计脚本验证**逐项等价**。`v2` 原样保留以备对照。
- ✂️ **`v0` −17 行 / `v1` −52 行** —— 同一判据（值等于官方默认值）精简。
- 🔧 **`v0` 两处调整**（**不同步到其他版本**）—— `Final` 组加 `hidden: true`（它只有一个子策略 `Proxy`，
  没有手动切换的意义）；`AD` 组去掉 `DIRECT`、只留 `REJECT`。
- ➕ **`rules` 段各加 2 条**（`v0` / `v1` / `v2`；`v2.1` 由其派生故同样包含）—— 白名单守卫
  `surge-white-guard.list → DIRECT`（必须抢在广告规则之前放行）、`surge-ads.list → AD`。
  规则总数 **22 → 24**（`v0` 为 **7 → 9**）。
- 📄 **文档同步** —— README 改版并新增「分流组结构」「规则优先级」两节；
  全部文档对齐 `v2.1` 与 `v0` 的新状态（README / [`docs/04`](docs/04-模板逐段讲解.md) /
  [`DetailsReadme`](DetailsReadme/) / [`skill/SKILL.md`](skill/SKILL.md)）。
- 🗑️ **撤掉 GitHub Actions** —— 删除 `.github/workflows/audit-regression.yml`，全部验证改为本地手动跑
  （`bash skill/tests/run.sh` + 4 个审计脚本），**功能上无损失**。

### 2026-09-20

- 🆕 **新增 `v2`** —— `dns` 段从 40 行压到 22 行：删掉没有任何引用点的 `hosts:` 段、
  与 catch-all 语义完全重叠的第二条兜底规则，并把 6 个端点收敛为「2 机构 × 2 协议」的 4 个。
  原模板保留为 **`v1`**，两份并存。
- 🆕 **新增 `v0`** —— 懒人极简版：只留 `Proxy` / `AI` / `AD` / `Final` 四组 + 9 条规则。
- 🔗 **`forward` 塌缩为 2 条兜底** —— 与订阅 / 节点域名**彻底解耦**：换订阅、换机场、换节点域名，
  `dns` 段一个字都不用改（当晚由 `v2` 进一步收敛为 1 条）。
- 🧹 **模板清理** —— 删掉 15 条 DNS 端点固定路由规则（`upstreams` 端点全是 IP 字面量，这些规则没有
  作用面，写错反而可能把国内 DoH 绕到境外）+ 10 条 `disabled: true` 的遗留规则。
- 🎯 **规则集调整** —— AI 分区接 ACL4SSR 远程 `AI.list`（固定 commit，避免上游漂移）；
  国内域名直连换用 Loyalsoldier `direct.txt`（111,160 条**纯域名**、零 IP 条目）；
  `Proxy` 规则默认 `disabled: true`，由 `Final` 兜底。
- 🔒 **脱敏发布** —— 剥离全部虚拟节点 / 机场订阅 URL / 证书；26 个分流组图标整合进本仓库 `icons/`
  （**不跨项目引用任何图标地址**）；`Foreign-DNS` 整组**注释保留不删**；加 MIT LICENSE。
- 🛠️ **三轮外部核查整改** —— 修 4 个脚本缺陷：`group_reach` 判据失效（曾把自有模板误判成 3 high、
  退出码 1）、`audit_dns_forward.py` 不带 `--drill` 直接崩（`UnboundLocalError`）、IPv6 端点被截断成
  `'[2400:3200:'`、`hostpart` 剥 scheme 的大小写回归（端点写 `HTTPS://…` 时读数从 0 high 翻成 9 high）。
  helper 收编进共享模块 [`_egern_common.py`](skill/scripts/_egern_common.py)，从结构上消灭
  「同一判据两份拷贝」。
- 🧪 **新增防退化守卫** —— [`skill/tests/run.sh`](skill/tests/run.sh)（5 fixture × 2 脚本 = 10 断言）。
- 📄 **新增 [`DetailsReadme/`](DetailsReadme/)** —— 集中 README 省略的全部技术细节；
  并修正 v7 / v10 后已作废的「节点域名 forward 修法」。
- 🔧 **行尾规范化** —— profile 由 CRLF 转 LF，内容逐字不变。

### 2026-09-19

- 🎉 **仓库初始化** —— Egern 防 DNS 泄露配置模板与审计工具。

---

## 🎨 图标与许可

- 分流组图标整合自 [RiverFlowsInUUU/Rule](https://github.com/RiverFlowsInUUU/Rule)、[jnlaoshu/MySelf](https://github.com/jnlaoshu/MySelf)、[Koolson/Qure](https://github.com/Koolson/Qure)，已统一存入本仓库 `icons/`，**不跨项目引用任何图标地址**。
- 本项目采用 **MIT** 许可证，见 [LICENSE](LICENSE)。
- 第三方规则集（blackmatrix7 / ACL4SSR / AWAvenue / jinx-ads-rules / Qure 等）版权归其原作者。

---

<p align="center">
  <sub>让 DNS 无处可漏 🐈</sub>
</p>
