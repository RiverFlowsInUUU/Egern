# DetailsReadme · Egern 防 DNS 泄露配置模板 · 完整技术文档

> **这份文档的定位**：`README.md` 只保留了「配置框架 + 防泄露原理」的精华，有意省略了大量推导、数据、谱系与工程方法。
> 本文档是 README 的**详版 / 补集**——把那些被省略的信息全部展开、讲清楚。
>
> **隐私声明**：本文档**不包含任何私人信息**。本仓库的模板本身是脱敏模板（节点段为空、图标已整合进本仓库、无订阅地址 / 证书 / token）。
> 下文凡涉及「真实配置」之处，一律用抽象表述，不出现任何具体节点域名、订阅链接、证书串或个人凭据。
> 文中提到的图标来源（公开 GitHub 仓库）仅作**署名归属**，它们已被下载整合进本仓库的 `icons/`，模板不再跨项目引用。

---

## 0. 目录

1. [配置框架逐段详解](#1-配置框架逐段详解)
2. [防泄露原理：从机制到推导](#2-防泄露原理从机制到推导)
3. [版本谱系 v1–v10（完整）](#3-版本谱系-v1v10完整)
4. [审计清单（18 项）](#4-审计清单18-项)
5. [规则集开销实测](#5-规则集开销实测)
6. [已知代价与取舍](#6-已知代价与取舍)
7. [隐私与脱敏](#7-隐私与脱敏)
8. [提炼的 Skill / 方法论](#8-提炼的-skill--方法论)
9. [如何自行审计](#9-如何自行审计)
10. [常见问题（扩展版）](#10-常见问题扩展版)

---

## 1. 配置框架逐段详解

### 1.1 顶层结构总览

模板由 12 个顶层段组成，按职责分三类：

**A. 全局开关 / 辅助项**
- `vif_only` —— 是否仅走虚拟接口。
- `hijack_dns` —— DNS 劫持开关，**接管本地 `:53` 并返回 Fake IP**，是防泄露的第一道闸门（缺失时 App 自带 DoH 仍能绕过）。
- `geoip_db_url` / `asn_db_url` —— `geoip` / `asn` 规则依赖的地理库（远程 `.mmdb`，非图标，保留原引用）。
- `proxy_latency_test_url` / `direct_latency_test_url` —— 延迟测试的 HTTP 端点（决定测速走代理还是直连）。
- `real_ip_domains` —— 不做 Fake IP 映射的域名白名单（APNs / 内网发现走的是「隧道外」链路，用 Fake IP 会异常）。

**B. 核心三段**
- `proxies` —— 节点定义（**模板为空 `[]`**，由你填写）。
- `policy_groups` —— 分流组（见 1.3）。
- `rules` —— 匹配表（见 1.4）。

**C. DNS 与默认出口**
- `dns` —— 双 DNS 模型核心（见 1.5）。
- `default_proxy_group` —— 默认出口组（本模板为 `Proxy`）。

### 1.2 `proxies` —— 空模板，由你填写

模板此处为 `proxies: []`。Egern 的 `proxies` 只描述节点本身（`server` 可为 IP 或域名、`type` 决定协议、`password` / `sni` / `reality-...` 等凭据）。

> 模板**不附带任何示例 / 虚拟节点**。原因：占位节点既无真实出口，又会在 `policy_groups` 里留下悬空引用，属于「过度设计」。你填入真实节点后，再把对应分流组的 `policies` 填上节点名（或订阅组名）即可。

### 1.3 `policy_groups` —— 四种类型、组间引用、图标

Egern 的分流组**按类型做键**，而不是平铺的 `name` 字段。一个组的典型形态是 `{select: {name: X, policies: [...], icon: ...}}`。四种类型：

| 类型 | 作用 | 模板里的例子 |
|---|---|---|
| `select` | 手动选路 | `Proxy` / `Final` / 各类 App 组 |
| `smart` | 智能选优：组内多轮测速，按延迟 / 抖动 / 可靠性综合打分自动选最稳节点 | `Hong Kong` / `USA` / `Japan`（这些地区组另配 `filter` 正则从订阅里筛节点 —— 归类是 `filter` 的职责，不是 `smart` 的） |
| `fallback` | 故障转移：按 `policies` 顺序依次尝试，选第一个可用的节点 | `ChatGPT` / `Gemini` |
| `external` | 从订阅 URL 拉取节点 | 模板里是 `sub.example.com?token=REPLACE_WITH_YOUR_TOKEN` 占位 |

要点：
- **组与组之间可以互相引用**（例如 `Final` 的成员是 `Proxy`，App 组的成员里混入地区组）。这种引用关系保留，是模板的正常结构。
- **`v2.3` 起已无空组**：`ChatGPT` / `Gemini` 曾是 `policies: []` 的空组，而规则直接指向它们
  ⇒ **导入即静默断流**；现已填成 `[Proxy]` + `flatten: true`（`flatten` 在这里起什么作用，
  见下方「组清单与要点」；逐段讲解见 `docs/04-模板逐段讲解.md` §4）。
- **图标**：模板用到的 26 个分流组图标（整合自 RiverFlowsInUUU/Rule、jnlaoshu/MySelf、Koolson/Qure 三个公开仓库）已统一下载进本仓库 `icons/`，全部以 `https://raw.githubusercontent.com/RiverFlowsInUUU/egern-anti-dns-leak/main/icons/<file>` 形式引用，**不再跨项目引用任何图标地址**。

#### 组清单与要点（`v2.4`）

**节点来源**（2 个订阅槽位）：`Airport-A` / `Airport-B`（后者另带一条 `urls_disabled` 示例）。
`v2.1` 及更早为 4 个槽位（多出 `Airport-C` / `Airport-Free`）—— `v2.2` 精简掉，选路能力不变。

**`flatten: true`** —— 把子策略组**展开成全部具体节点**，而不是当成一个「组」单位。
以 `Smart` 为例：不加时候选是「`Airport-A` 组」「`Airport-B` 组」两个单位（两级选优），
加上后才是订阅里的**全部具体节点**（一级选优）。官方「通用字段」明确它在
`select` / `auto_test` / `smart` / `fallback` / `load_balance` 五种基础类型上通用。
本模板的 `Smart` / `MAX` / `ChatGPT` / `Gemini` 与全部地区组都用了它。

**`ChatGPT` / `Gemini` 为什么必须配 `flatten`** —— 它们是 `fallback`，语义是**按顺序取第一个可用**。
不加 `flatten` 时候选只有「`Proxy`」**一个**，等于没有故障转移能力，且 `Proxy` 一挂整组就断；
加上后 `Proxy` 展开成全部具体节点，`fallback` 在节点级依次尝试
⇒ 效果是给 `Proxy` 补一层**节点级故障转移**。

**`MAX`** —— 「带节点筛选的 `Smart`」：上游同 `Smart`，额外用
`filter: (?<![\d.])0\.\d*[1-9]` 只留**倍率 < 1** 的节点。

**地区组** —— 「按正则把节点归类」是 **`filter`** 干的，不是 `smart` 本身；
`smart` 只负责在筛出来的节点里选最优。`Other Regions` 的负向断言把其余 6 个地区组的
关键词**逐字抄了一遍** —— 改任何一组的关键词都要同步改它，
用 [`skill/scripts/audit_region_filters.py`](../skill/scripts/audit_region_filters.py) 校验（漏改会被它拦下）。

**服务组**（默认策略与承接的规则集）见 [`README.md`「分流组结构」](../README.md#-分流组结构)。

**`v0` 的两处专属调整**（只属于它，不同步其他版本）：`AD` 组**只有 `REJECT`**（没有 `DIRECT` 兜底）、
`Final` 组**被隐藏**（只有一个子策略，没有手动切换的意义）。

### 1.4 `rules` —— 匹配表与直连规则集

`rules` 是「什么流量走哪里」的总指挥。支持的规则类型：

- `domain_suffix` / `domain` / `domain_keyword` —— 域名类（会触发解析，除非被后面的 `no_resolve` 逻辑约束）。
- `ip_cidr` / `ip_cidr6` / `asn` —— IP 类（**必须带 `no_resolve`**，见 2.3）。
- `rule_set` —— 引用远程 / 本地规则集文件（其内部的 IP 条目也必须带 `no-resolve`）。
- `geoip` —— 按 IP 地理归属（`no_resolve: true` 时只对「已经是 IP」的连接生效）。
- `default` —— 兜底策略。

**直连三件套**（决定国内流量不走代理）：
1. `Lan.list` —— 局域网。
2. `Apple_All_No_Resolve.list` —— Apple 域名 + 带 `no-resolve` 的 IP，既做直连判定又不重新触发解析。
3. **国内域名规则集（Loyalsoldier `direct.txt`）** —— 约 **11.1 万条纯域名**（`DOMAIN-SUFFIX` 约 11.06 万 + `DOMAIN` 553，**零 IP 条目**；上游每次更新都会变动，故这里用约数），是「国内域名直连」的主力。纯域名规则只做字符串匹配、不触发解析，因此无需 `no_resolve`；「已经是 IP 的连接」由下方 `geoip: CN` 兜住。
> 另有一条 `domain_suffix: cn` —— 把整个 `.cn` TLD 再钉一次，**不依赖规则集是否加载成功**
> （`direct.txt` 已覆盖绝大多数国内域名）。它与上面 3 条规则集合起来，构成 `rules` 的全部直连来源。

**默认出口链**：未命中任何规则集的域名 → `default` 规则（`policy: Final`）→ `Final` 组唯一成员是 `Proxy` → 走代理。这类流量由**节点远程解析**，不经过本地 `dns:` 段，日志里表现为 `default → Final → Proxy`。

> ⚠️ 关键绑定：`geoip: CN`（`no_resolve: true`）**只对已经是 IP 的连接生效**，国内域名的直连**完全依赖那个纯域名国内规则集（`direct.txt`）**。两者绑定，动一条必须看另一条（详见 2.3 / 清单 17）。

### 1.5 `dns` —— 双 DNS 模型核心

`dns` 段是本模板防泄露的中枢，由四个子段组成：

| 子段 | 作用 | 本模板取值 |
|---|---|---|
| `upstreams` | 默认 DNS 的解析器组 | 仅 `Domestic-DNS`（**4 个**国内加密端点 = 2 机构 × 2 协议，全为 IP 字面量） |
| `bootstrap` | 默认 DNS 的回退（明文 `:53`） | **2 个**国内公共 DNS 的 IP（阿里 + 腾讯），**不含 `system`** |
| `proxy_nameservers` | 代理 DNS（解析节点 `server` 里的域名），**硬覆盖** | **4 个**国内加密端点，与 `upstreams` 一致 |
| `forward` | 默认 DNS 按域名选上游 | **1 条 catch-all 兜底**（见 2.4） |

另有 `hijack_dns`（接管 `:53` 返回 Fake IP）。

> 关于 `Foreign-DNS` 组：迭代 v10 起它就无任何引用（forward 兜底改国内组后不再需要境外组）；`v1` 里它被**整组注释**保留作 A/B 备用，**`v2` 起整段删除**。想恢复境外解析答案，需自行在 `upstreams` 里加回该组、并把 `forward` 兜底的 `value` 改过去 —— 但要注意「先有代理才敢解析」的启动期明文风险。详见第 6 节。

### 1.6 `rule_sets` 与 `no_resolve` 要求

模板通过 `rules` 里的 `rule_set` 引用远程规则集（blackmatrix7 / ACL4SSR / Qure 等公开仓库）。**致命点**：缺陷常藏在别人仓库的 `.list` 文件里——若其中存在「不带 `no-resolve` 的 IP 类条目」，profile 写得再干净也看不见（见清单 16）。因此所有被启用的规则集文件，其 IP 条目必须带 `no-resolve`，并用 `audit_ruleset_noresolve.py` 逐个下载核对。

---

## 2. 防泄露原理：从机制到推导

### 2.1 双 DNS 模型

理解整份配置只需记住一个事实：**Egern 有两套 DNS**。

1. **默认 DNS** —— 处理业务流量的域名解析。按 `dns.forward` 匹配上游，未命中则回退到 `dns.bootstrap`。
2. **代理 DNS**（`dns.proxy_nameservers`）—— 只负责解析「节点 `server` 里的域名」，且强制在**直连侧**完成（代理还没通，不可能让代理去解析自己的地址）。它一旦设置，就**绕过 `forward`**。

**泄露只会发生在一条路径上：明文 `UDP:53` 的 `bootstrap`。** 一切加固都围绕「让 bootstrap 无事可做」展开。

### 2.2 `bootstrap` 的两条用途与如何消灭

`bootstrap`（明文 `:53`）会被触发当且仅当：
- **用途①**：某个加密 DNS 端点本身是用**主机名**写的（如 `https://dns.google/dns-query`），Egern 得先用系统 DNS 把它解析成 IP ⇒ 暴露。
- **用途②**：`forward` 没有接住某个域名，默认 DNS 回退到 `bootstrap` ⇒ 暴露，且一旦本地递归失败还会掉到「系统 DNS」（运营商）。

消灭方式：
- 用途① → 所有端点写 **IP 字面量**（2.3 原则①）。
- 用途② → `forward` 必须有一条「直连可达」的兜底（2.3 原则③ / 清单 4）。

> ⚠️ **`bootstrap` 唯一安全的形态是「永远不被触发」。** 它本质是明文 UDP:53，在运营商线路上无论指向哪个 IP 都可能被接管或失败。所以「换一个更好的 bootstrap IP」是错误思路——本模板的做法是把前两条做到位，让它根本不被用到（清单 5）。

### 2.3 三条原则详述

**① 端点全部写成 IP 字面量**
`dns.upstreams` 与 `dns.proxy_nameservers` 里**不出现任何主机名**。没有需要解析的目标 ⇒ 用途①被直接消灭（清单 1）。

**② `no_resolve` 成对出现（这是「用解析换分流」的开关）**
所有 IP 类规则（`geoip` / `ip_cidr` / `ip_cidr6` / `asn`）都带 `no_resolve`，它们只匹配「已经是 IP」的连接，不再触发任何域名解析。需要靠域名判定归属的国内直连，由**纯域名的国内规则集**（Loyalsoldier `direct.txt`，11 万条）承接——域名规则只做字符串匹配、不触发解析，故无需 `no_resolve`。两者绑定，缺一不可（清单 5 / 17）。

> `no_resolve` 有三个层级，别混：
> - **规则级**：写在 `rules:` 里的 `geoip/ip_cidr/...`，官方明说只适用这四类；写在 `rule_set` 规则上**不生效**。
> - **规则集文件顶层**：Egern 原生 YAML 规则集里的 `no_resolve: true`，影响整文件。
> - **规则集条目级**：Surge `.list` 里的 `IP-CIDR,x/y,no-resolve`——第三方 `.list` 走这一层，也是缺陷最常藏身之处（清单 16）。

**③ `forward` 塌缩为一条 catch-all 兜底**
```yaml
forward:
  - domain_wildcard: '*'     value: Domestic-DNS
```
> `v1` 里是两条（`domain_regex: '.'` + `domain_wildcard: '*'`）；`v2.1` 删掉了 `domain_regex` ——
> 它与 `domain_wildcard` 语义完全重叠（任何域名两条都命中、`value` 又相同），
> 按官方「第一条命中即决定上游」，第二条永远不会被求值。详见 2.4。

### 2.4 `forward` 塌缩的设计判据（两个反直觉事实）

决定「不必在 forward 里列举任何节点 / 订阅域名」的两层原因：
- 配了 `proxy_nameservers` 后，**代理 DNS 会跳过 forward** —— 节点域名根本不走这里（清单 2b）。
- 兜底 `value` 为**单值**时，**规则顺序与域名清单都不影响结果**（官方：「规则按声明顺序求值，第一条命中决定上游」；但所有兜底都指向同一个组，顺序无意义）。

⇒ 于是 forward 与订阅**彻底解耦**：你换十个订阅，这里一行都不用改。

### 2.5 兜底组安全性 vs 列举域名（核心设计原则）

> **防泄露由「兜底组本身是否直连可达」承担，不由「在 forward 里罗列域名」承担。**

判据：删掉一条 forward 规则，结果会变吗？会引入维护耦合吗？两个反直觉事实（2.4）说明：在 `value` 单值 + 代理 DNS 跳过 forward 的前提下，列举节点域名 / 延迟测试域名 / 图标域名 / `.cn` / 国内域名表都是**死代码或冗余**。因此模板只留兜底，把节点域名、订阅耦合全部剥离。这一手同时消灭了「换订阅导致 forward 配置失效」的风险（清单 18）。

---

## 3. 版本谱系 v1–v10（完整）

> 以下每版描述均为**机制层面**的演进，不涉及任何具体节点域名或私人配置。验收数据来自实际真机测试。

| 版本 | 改动 | 结果 |
|---|---|---|
| **v1** | 第一版加固 | ❌ 私自加了 `proxy_nameservers`，把代理侧解析钉死在国内 → 泄露从「偶发」变「确定」 |
| **v2** | 端点改 IP 字面量 + DNS 端点显式路由 + 加 `block_ips` | ❌ `proxy_nameservers` 仍在，问题未解 |
| **v3** | 删 `proxy_nameservers`；显式覆盖节点域名；forward 双兜底 | ✅ 修掉节点域名明文解析 ⚠️ 漏了 latency 测试域名 |
| **v4** | 补 profile 自身必需解析（两个延迟测试域名 + jsdelivr）→ 国内组 | ✅ 修掉「每轮测速触发一次」的持续泄露 |
| **v5** | `upstreams` 全部改 IP 字面量 + `bootstrap` 扩到 3 个国内 IP | ✅ 消灭 bootstrap 用途① |
| **v6** | forward 两条兜底的 value：境外组 → 国内组 | ✅ 消灭 bootstrap 用途②（兜底不再依赖代理） |
| **v7** | ① `Apple_All.list` → `Apple_All_No_Resolve.list`；② 显式写 `proxy_nameservers`；③ 给 `geoip: CN` 补 `no_resolve` | ✅ 泄露治好（第③条是真正答案）<br>❌ **但同一手把国内域名的直连路径一起关掉了** |
| **v8** | **只改一条**：`ChinaMax.list` → `ChinaMax_All_No_Resolve.list`（补齐国内域名直连） | ✅ **泄露与分流同时成立 —— 真机验收通过** |
| **v9** | 删除整个顶层 `mitm` 段（`ca_p12` + `ca_passphrase`） | ✅ 用户主动要求「暂时不用 HTTPS 解密」；纯删除，不触碰 DNS / 分流任何一行；证书串零残留 |
| **v10** | `dns.forward` 由 10 条塌缩为 2 条兜底（删 8 条结构性冗余 + 2 处死引用） | ✅ 与订阅 / 节点域名解耦；审计通过，订阅耦合 4 → 0 |

### 每一版的验证结果

> ⚠️ **读数说明（很重要）**：下表的所有数字都是**作者的「自用配置」**跑出来的 ——
> 它带真实节点、且 v1–v8 时期 `rules` 里还有 DNS 端点路由规则。
> **本仓库发布的是一份脱敏模板**（`proxies: []`、无节点、v10 已删段 A 路由），
> 它的审计读数**与下表不同**，且**从未声称全绿**。两者的差异见本节末尾「发布模板的审计读数」。

| 版本 | `check_egern_dns.py` | `audit_ruleset_noresolve.py` | `audit_routing_coverage.py` |
|---|---|---|---|
| v6 | 0 high / 3 low / 43 ok | ❌ **HIGH** | 未覆盖 |
| v7 | 0 high / 3 low / 43 ok | ✅ OK (20/20) | ❌ **7/15 国内探针落 Final** |
| **v8** | **0 high / 3 low / 43 ok** | ✅ **OK (20/20)** | ✅ **15/15 DIRECT** |

> v7 那一行是本项目最重要的一张表：**两个脚本双双全绿，配置却不可用。**

### 发布模板的审计读数（与上表不同）

发布模板**不是**自用配置，读数独立：

| 脚本 | 发布模板读数 | 说明 |
|---|---|---|
| `check_egern_dns.py` | ✅ **0 high / 2 low / 24 ok（退出码 0）** | 见下方「v3.1 判据修正」；24 这个数对应 `v2` 起的全部版本（`v1` 是 30 ok，多出的 6 项来自它比 `v2` 多的一批 DNS 端点路由规则） |
| `audit_routing_coverage.py` | ✅ 15/15 国内探针 `DIRECT` | 分流正确性不受脱敏影响 |
| `audit_dns_forward.py --drill` | ✅ 通过（退出码 0） | `forward` value 单值、订阅耦合 0 |
| `audit_region_filters.py` | ✅ 6 个地区组关键词全部同步（退出码 0） | 负向断言与地区组 filter 逐字一致 |

**v3.1 判据修正（2026-09-20）** —— 曾有一段时间发布模板**过不了** `check_egern_dns.py`：

- **现象**：3 high / 8 low / 20 ok，退出码 1。
- **根因**：v10 删掉段 A（DNS 端点固定路由）后，脚本 `group_reach` 的判据是
  「端点全为 IP **且至少一个在 `rules` 里判给 `DIRECT`**」，后半句在无段 A 的模板里**永远不成立** ⇒
  兜底组 `Domestic-DNS` 被恒定判为「依赖代理」，连锁触发 3 条 HIGH（兜底组 + 两个延迟测试域名）。
  **这是判据的载体选错，不是配置的问题。**
- **修法**：补**第二判据** —— 端点全为 IP 且**至少一个是国内知名解析器 IP**（内置白名单：
  阿里 `223.5.5.5`/`223.6.6.6`、腾讯 `119.29.29.29`、`1.12.12.12`、`120.53.53.53` …）时同样判「直连可达」。
  此判据在 profile 文本内可验证、且语义等价于「不经代理即可到达」。
- **没有放松防护**：v5 踩过的坑仍被拦住 —— **一个全由境外 IP 组成的组依然判 HIGH**
  （境外解析器必须经代理才可达）；含主机名端点的组依然判 HIGH。已用反例做过回归验证。
- **四处同步**：`check_egern_dns.py` 的 `group_reach` + 其国内端点路由检查、
  `audit_dns_forward.py` 的 `direct_ips` 收集 + 结论判定。
- ⭐ **（二次核查后）已消除「两份拷贝」隐患**：上述同步最初靠注释互相提醒，**被证明不可靠** ——
  判据本体同步了、但喂给它的 helper（`ep_ip`）没同步，导致
  `audit_dns_forward.py` 把 `[2400:3200::1]` 截断成 `'[2400:3200:'`，
  **同一份 IPv6 profile 两个脚本给出相反结论**（0/1）。
  现已把 `DOMESTIC_RESOLVER_IPS` / `hostpart` / `ip_literal` 收编到共享模块
  `skill/scripts/_egern_common.py`，两个脚本都从它 import —— 从结构上消灭拷贝。
  并新增 `skill/tests/run.sh`（阶段 1：5 fixture × 2 脚本）作为**防退化守卫**。
- ⚠️ **（三次核查后）"收编"这个动作本身又引入了一次回归**：`hostpart` 剥 scheme 从
  「通用剥离」退化成「大小写敏感白名单」，端点写 `HTTPS://223.5.5.5/dns-query` 时
  `HTTPS` 被当成主机名 ⇒ 同一份配置读数从 **0 high 翻成 9 high**。发布模板端点全小写所以没暴露。
  已改回大小写不敏感的通用正则，并新增 `skill/tests/scheme_case.yaml` 守卫。
  **教训：重构式的"等价改写"必须逐输入对拍，测试还绿只说明已覆盖的输入没变。**
- ⚠️ **（三次核查后）"声称已交付"与"实际交付"必须分开核**：当时 README 与 commit message
  都写着"已加上某物"，实际那个文件**从未上传** —— 发布脚本遇到失败会**摘掉该文件继续推**，
  于是"推成功了"和"东西真的在那儿"是两回事。
  **教训：发布后要用 `git ls-files` 核对交付物，而不是相信发布脚本的 commit message。**

> 📌 **诚实声明**：本项目最长的一条教训就是「审计通过 ≠ 配置可用」，反向同样成立 ——
> **审计不通过 ≠ 配置不可用**。上面那次 3 high 就是判据的问题，配置本身（IP 字面量端点 + 单值兜底）
> 一直是对的。这类 false positive 必须当 bug 修掉，否则脚本的退出码就不能当守门判据。

### 五次「审计通过但实测有问题」

| # | 表现 | 真实原因 | 补上的审计维度 |
|---|---|---|---|
| 1 | v1/v2 脚本报 0 high | 靠加配置压指标（`proxy_nameservers`）掩盖问题 | — |
| 2 | v3 脚本报 0 high | 审计器没看 latency 测试域名这一类 | 清单 15 |
| 3 | v5/v6 脚本报 0 high | 判据不足：`group_ready` 只要求端点全 IP + 至少一个被判路由，没要求那一条是 `DIRECT` | 收紧为 `group_reach` |
| 4 | v6 脚本报 0 high | 审计维度缺失：只看 profile 文本，没看它引用的规则集文件 | `audit_ruleset_noresolve.py`（清单 16） |
| 5 | v7 两个脚本都全绿 | 审计不覆盖分流——治泄露的副作用没人检查 | `audit_routing_coverage.py`（清单 17） |

### 反向教训：审计**不通过**但配置是对的（v10，2026-09-20）

上面 5 次都是「审计绿了但配置不可用」。第 6 次是**镜像问题**：

| # | 表现 | 真实原因 | 修法 |
|---|---|---|---|
| 6 | v10 删段 A 后，发布模板 `check_egern_dns.py` 报 **3 high**、退出码 1 | **判据的载体过时了** —— `group_reach` 依赖 `rules` 里的 `ip_cidr → DIRECT` 作为「不经代理可达」的证据；v10 把那批规则删掉后证据消失，但配置本身没问题 | 补第二判据「端点全为 IP + 至少一个是国内知名解析器」；**两份拷贝同步改**，并用反例（全境外 IP 组）回归验证防护未被放松 |

**这条要记的是**：判据和被测对象是**同一套假设的两端**。改了配置、必须回跑审计脚本 —— 否则
脚本会开始报 false positive，而**退出码这个守门判据就成了摆设**。改配置的人有责任验另一端。

**固化规则**：任何一次「审计与实测不一致」（**无论哪个方向**），都必须假设「判据本身可能过时」，
先分清是配置错还是判据错，再动手。false positive 与 false negative 一样是 bug。

---

## 4. 审计清单（18 项）

> 📌 本节是 [`docs/03-加固清单-18项.md`](../docs/03-加固清单-18项.md) 的摘要。**逐条判据与严重度的权威版本以 `docs/03` 为准** —— 要改清单请改那一份，本节跟着同步。

> 全部自动化：`check_egern_dns.py` 覆盖 1–15；`audit_ruleset_noresolve.py` 覆盖 16；`audit_routing_coverage.py` 覆盖 17；`audit_dns_forward.py` 覆盖 18。

| # | 检查 | 判据 | 严重度 |
|---|---|---|---|
| 1 | `upstreams` / `proxy_nameservers` 端点是否为 IP 字面量 | 出现主机名端点 → 必被 bootstrap 明文解析一次 | 高（境外）/ 低（国内） |
| 2 | 节点 `server` 是域名时，`forward` 是否接住 | 没接住 → 节点域名明文暴露 | 高 |
| 2b | `proxy_nameservers` 是否存在 | 它是**硬覆盖**：一设就跳过 `forward`、强制直连。**两种写法都成立，但必须二选一、不要叠加** —— ① **不设置**（代理 DNS 与默认 DNS 共用 `forward`，靠兜底接住节点域名）；② **设置**（把「未命中 → 回退 `bootstrap`」这条分支从结构上消掉，且强制直连 ⇒ 不依赖代理就绪）。**本模板采用 ②** | 中 |
| 3 | DNS 端点是否全为 IP 字面量（无需在 `rules` 钉路由） | 主机名端点才需在 `rules` 显式路由（否则落 `default` 错判出口）；**本模板全部 IP 字面量，故 `rules` 中已无 DNS 端点路由规则**，此条由清单 1 覆盖 | 高（仅在你自己改用主机名端点时适用） |
| 4 | `forward` 是否有「直连可达」兜底 | 兜底组端点全为 IP 字面量 + 满足**判据 A 或判据 B**：**A** 至少一个在 `rules` 里被判给 `DIRECT`；**B** 至少一个是**国内知名解析器 IP**（`223.5.5.5` / `223.6.6.6` / `119.29.29.29` / `1.12.12.12` / `120.53.53.53` …）—— **本模板走判据 B**。写法要认全：`domain_wildcard:'*'` **和** `domain_regex:'.'` 都算兜底 | 高 |
| 5 | `geoip`/`ip_cidr`/`ip_cidr6`/`asn` 是否带 `no_resolve` | 不加则触发解析 | 高 |
| 6 | 规则引用的策略名能否解析 | 笔误（如「负载均衡」）会成死规则 | 高 |
| 7 | 硬编码 DoH IP 是否有启用规则 → 代理 | `hijack_dns` 只覆盖 `:53`，App 自带 DoH on `:443` 会绕过 | 中 |
| 8 | `rule_set.match` 是否为 URL / 文件路径 | 写成名字 → 无法加载，等同死规则 | 中 |
| 9 | `block_ips` | 未设 → 污染应答照单全收 | 低 |
| 10 | `real_ip_domains` | 为空 → 走不到隧道的流量也拿 Fake IP | 低 |
| 11 | `ipv6` | `true` → AAAA 可绕过 IPv4 侧封堵 | 中 |
| 12 | `hijack_dns` 是否覆盖全部 | 官方示例值 `['*']` | 高（缺失时） |
| 13 | `public_ip_lookup_url` | 不配置才不发 ECS | 配了才是问题 |
| 14 | `skip_tls_verify` | 应为未设置 / `false` | 低 |
| 15 | profile 自身必需解析（两个 latency test URL + 策略组 icon 域名）是否被兜底之前接住 | 没接住 → 直连侧解析失败回退明文 = 运营商；延迟测试端点 = 高（持续泄露），图标 = 低（可不动） | 高 |
| 16 | ⭐⭐ 远程规则集里有无「不带 `no-resolve` 的 IP 类条目」 | 缺陷藏在别人仓库的 `.list` 里；一条启用规则集里有 1 条就触发；必须逐个下载 + 数 | 高 |
| 17 | ⭐⭐ 国内域名有没有「域名类」规则兜底（不是「有没有一条叫 China 的规则」） | 给 IP 规则补 `no_resolve` 会同时关掉直连路径；必须有一份含大量域名条目的国内规则集；判据是数域名条目 | 高 |
| 18 | ⭐ `forward` 是否单值 + 是否写死节点域名（订阅耦合）+ 兜底是否直连可达 | `value` 单值 ⇒ 顺序/清单无意义；写死节点域名 ⇒ 换订阅变死代码；兜底不可达 ⇒ 掉进明文 | 高 |

**验收六条（同时满足才算完）**
1. `upstreams` / `proxy_nameservers` 无任何主机名端点 → 消灭用途①。
2. `forward` 有兜底且兜底组直连可达 → 消灭用途②，不依赖代理就绪。
3. 所有 IP 类规则都带 `no_resolve`。
4. 所有被启用的 `rule_set` / `proxy_rule_set`，其文件内 IP 类条目都带 `no-resolve`。
5. `bootstrap` 显式列 2 个以上国内公共 DNS IP，且不含 `system`。
6. ⭐⭐ 分流仍正确：国内域名仍判 `DIRECT`（15 个国内探针全绿）。**这是第 3 条的代价，必须成对交付。**

**五个脚本的定位（为什么不合成一个）**
| 脚本 | 看哪一层 | 关键点 |
|---|---|---|
| `check_egern_dns.py` | **profile 文本** | 能验证的只有「你自己编码进去的假设」 |
| `audit_ruleset_noresolve.py` | **被引用的规则集文件** | 缺陷不在 profile 里 —— 不下载就永远看不见 |
| `audit_routing_coverage.py` | **域名 → 命中规则 → 策略** | 验证「防泄露」没把「分流」一起干掉 |
| `audit_dns_forward.py` | **`forward` 的结构**（单值性 / 订阅耦合 / 换订阅演练） | 验证「换订阅后还能不能防泄露」 |
| `audit_region_filters.py` | **地区组 filter 的「两份拷贝」** | 负向断言（「排除以上全部」）必须逐字重抄关键词，Egern 不支持 `filter` 引用 ⇒ 只能靠脚本守同步 |

---

## 5. 规则集开销实测

> 数据来自在真实内核里加载规则集后量出的常驻内存与查询耗时。

- **内存估算**：原生实现约 130–175 B / 域名条目 ⇒ 内存 ≈ `条目数 × 0.15 KB`。
  例：`ChinaMax_All_No_Resolve`（111,332 域名 + 12,473 IP / 3.42 MB）→ 稳态 RSS +22.6 MB；`adrules_surge_domainset`（199,781 条）→ +24.7 MB。
- **加载与匹配几乎无代价**：就绪时间无差别；单次域名匹配 0.36–0.69 µs，表规模涨 111 倍只让查询涨不到 2 倍（O(标签数)）。**大表不拖慢连接，只吃常驻内存。**
- **大表不能瘦身**：去重收益 0；父后缀冗余仅 4–5 条；99.5% 已是两级域名；表内 IP 段与 `geoip:CN` 大面积重合（61% 两端都在 CN / 面积 93.4%）。
- **换小表按覆盖率判，不按体积**：ACL4SSR `ChinaDomain.list`（586 条 / 17 KB）对大表长尾抽样只覆盖 0.4%（高频 26 站 21/26）⇒ 主流站几百条够用，长尾 99.5% 会掉进代理。
- **工具**：`skill/scripts/weigh_ruleset.py <大表> --sub <小表> --probe <域名>`。

---

## 6. 已知代价与取舍

- **`Foreign-DNS` 已删除**：迭代 v10 起它就无任何引用（forward 兜底改国内组后不再需要境外组）；`v1` 曾**整组注释**保留为 A/B 备用，**`v2` 起整段删除**。要恢复境外解析答案，需自行在 `upstreams` 里加回该组。风险提醒：若用它作兜底且代理未就绪，会掉进明文 `:53`。
- **两个版本 + 5 份旧版 × 双形态**：可选只有 `profiles/v2.4.yaml`（**推荐**，完整分流）与 `profiles/v0.yaml`（**极简懒人版**，4 组 / 9 条规则）；其余 `v2.3` / `v2.2` / `v2.1` / `v2` / `v1` 都是 `v2.4` 的历代旧版、保留以备对照（`v1`~`v2.1` 为 29 组 / 24 条，`v2.2`~`v2.4` 为 27 组 / 24 条）。**各版本逐项差异见 [`docs/07-文件版本沿革.md`](../docs/07-文件版本沿革.md)（权威版本）**。⚠️ 文件名 `v0`…`v2.4` 是**文件版本**，与 `docs/06` 的「配置迭代谱系 v1~v10」是两个维度。
- **图标整合进本仓库**：26 个图标源自已整合进 `icons/`，模板不再跨项目引用图标地址。来源归属与许可见 [`docs/10-图标与许可.md`](../docs/10-图标与许可.md)（公开仓库署名）。
- **删除虚拟节点（不保留引用）**：模板 `proxies` 为空，占位节点名引用已从 `policy_groups` 剥除（组间引用保留；`v2.3` 起**已无空组**）。不保留虚假结构，由你自行填写。
- **与订阅解耦**：forward 不写任何节点 / 订阅域名，换订阅无需改动 DNS 段（清单 18 验证订阅耦合 4 → 0）。
- **审计脚本报的 2 条 `LOW`（刻意为之，不是缺陷）**：`check_egern_dns.py` 对本模板的读数是 `0 high, 2 low`。两条都属「安全性 vs 可用性」的自觉取舍，不是配置错误：
  - **① 设置了 `proxy_nameservers`** —— 它成为代理侧解析的唯一出口（绕过 `forward`、强制直连）。这是必须的：节点域名要在代理起来之前解析，只能走直连侧。
  - **② `forward` 兜底指向国内组**（`Domestic-DNS`）—— 需要本地解析的境外域名会拿到国内答案（可能被污染）。按官方语义，走代理的域名由节点**远程解析**、不经过 `dns` 段，所以实际影响面**仅限 `DIRECT` 域名**。

---

## 7. 隐私与脱敏

本仓库是纯模板，**发布前经过系统化脱敏**。脱敏五类：
1. 节点 `server` / 凭据 / `sni` / `reality` 公钥；
2. 机场订阅 URL（含 token）；
3. `mitm.ca_p12` + `ca_passphrase`（个人 CA 私钥，注释掉并占位）；
4. 机场组名 / 节点名；
5. `dns.forward` 里的节点域名。

**自检机制**：构建脚本对 38–39 个敏感串做零残留断言，并对全仓库做字符串扫描。发布前复核结论：
- 模板 yaml 外部图标源引用 **0**；
- 真实节点域名 / 订阅 host **0** 命中；
- `token=` / `ca_p12` / `sub.` 经核对均为占位符（`REPLACE_WITH_YOUR_TOKEN` / 注释说明 / `sub.example.com`），无真实泄露。

---

## 8. 提炼的 Skill / 方法论

本项目的工程方法已沉淀为两个可复用的 WorkBuddy Skill，并配套了本仓库的脚本。

### 8.1 `egern-profile-dns-hardening`

- **定位**：审计并加固 Egern 配置（Profile.yaml）的 DNS 泄露面与分流覆盖。
- **触发词**：Egern 配置 / 防 DNS 泄露 / `proxy_nameservers` / `bootstrap` 泄露 / 节点域名明文解析 等。
- **脚本清单**（9 个，各自看不同层）：
  | 脚本 | 层级 | 覆盖清单 |
  |---|---|---|
  | `check_egern_dns.py` | profile 文本 | 1–15 |
  | `audit_ruleset_noresolve.py` | 被引用的规则集文件 | 16 |
  | `audit_routing_coverage.py` | 域名 → 命中规则 → 策略 | 17 |
  | `audit_dns_forward.py` | forward 单值 / 订阅耦合 / 兜底可达 | 18 |
  | `audit_region_filters.py` | 地区组 filter 与 `Other Regions` 负向断言的同步 | 辅助 |
  | `weigh_ruleset.py` | 规则集重量（构成/冗余/耗时/覆盖） | 辅助 |
  | `probe_dns_endpoints.py` | 端点逐个实测（DoH 线格式 / DoT 握手） | 辅助 |
  | `probe_doh.py` | 只测 DoH 线格式 | 辅助 |
  | `profile_ruleset.py` | 规则集类型分布 | 辅助 |
- **核心价值**：把「审计通过 ≠ 配置可用」的教训固化成 **18 项可复跑清单**，尤其强调**规则集层（清单 16）**与**分流覆盖层（清单 17）**这两个 profile 文本审计看不见的维度。

### 8.2 `github-publish-sanitized-repo`

- **定位**：把本地文件（配置 / 脚本 / 文档）**脱敏后**发布到 GitHub 仓库，或往已有仓库做增量单提交。
- **触发词**：上传到我的 github / 发布到仓库 / 脱敏后上传 / 增量提交 等。
- **方法论要点**：
  - **Git Data API 流程**：`blobs → tree → commit → ref` 单次增量提交；读 HEAD 作 parent + `base_tree` 保证幂等更新。
  - **空仓库 409 处理**：空仓库不能直接建 blob（`POST /git/blobs` → `409 Git Repository is empty`）；先用 **Contents API（PUT）** 落一个初始化提交，再取 HEAD 作 parent + `base_tree`。
  - **脱敏五类 + 全库自检**：同第 7 节，发布前对全仓库扫描，确保敏感串零残留。
  - **绑定 PAT**：GitHub REST API + PAT 操作（本机无 gh CLI / SSH）。发布后**应提醒撤销轮换所用 PAT**。

### 8.3 本仓库配套脚本（公开）

除 `skill/scripts/` 的 9 个审计 / 探针脚本外，早期发布链路还包含一组构建脚本（位于维护者本地 `outputs/`，**不进公开仓库**，避免暴露构建侧的私人源路径）：
- `_build_public_template.py` —— 从脱敏基线生成模板（dns 段取自加固版、结构取自基线）。
- `_transform_template.py` —— 在已脱敏产物上做改写（删占位节点、剥节点引用、图标改指本仓库）。
- `_make_min.py` —— 由带注释版生成纯配置版（去注释）。
- `_fetch_icons.py` —— 下载整合全部图标到 `icons/`。
- `_publish_to_github.py` —— 递归遍历 `public/` 走 Git Data API 增量提交。

> ⚠️ **这组脚本当前已不在维护者本机**（2026-09-21 核查确认，全盘搜索无结果）。
> 它们描述的"从自用配置生成模板"流程**已停用** —— `v2.1` / `v2.2` / `v2.3` / `v2.4`
> 都是在仓库里**直接改 `profiles/*.yaml`** 产出的（模板早已脱敏完毕，无需重新生成）。
> 此处保留是为了记录方法论；若要恢复该流程，见 §8.2 的 Git Data API 流程重建。

---

## 9. 如何自行审计

三个主审计脚本**退出码 0 = 通过**，可直接用于提交前检查。
**本仓库刻意不挂 CI**（理由见下），全部验证都在本地跑：

```bash
PY="<你的 python（含 pyyaml）>"
S="skill/scripts"

"$PY" "$S/check_egern_dns.py" Profile.yaml
"$PY" "$S/audit_ruleset_noresolve.py" Profile.yaml        # 会下载并缓存规则集
"$PY" "$S/audit_routing_coverage.py" Profile.yaml
"$PY" "$S/audit_dns_forward.py" Profile.yaml --drill       # 换订阅演练
"$PY" "$S/audit_region_filters.py" Profile.yaml            # 地区组 filter 同步（v0 无此结构，自动跳过）

# 辅助
"$PY" "$S/weigh_ruleset.py" ChinaMax_All_No_Resolve.list --sub ChinaDomain.list
"$PY" "$S/probe_dns_endpoints.py" Profile.yaml
```

规则集缓存写在系统临时目录（约 5 MB），可离线复用（`--offline`）。

> 📌 **全部验证都在本地完成 —— 本仓库刻意不挂 CI / 任何自动化**（2026-09-21 决定）。
> 这是个人模板仓库，不会有外部贡献者，"自动验 PR"没有服务对象，而本地跑一遍只要几十秒。
> 上表那批本地命令已覆盖自动化做过的全部断言，**功能上没有任何损失**。
> 详细说明见 [`skill/reference/public-repo.md`](../skill/reference/public-repo.md)。

---

## 10. 常见问题（扩展版）

**Q1：为什么 forward 只留一条 catch-all 兜底，不写节点域名？**
因为配了 `proxy_nameservers` 后代理 DNS 跳过 forward（节点域名根本不走这里），且兜底 `value` 为单值时顺序与域名清单都无意义。写节点域名只会随订阅变化变成死代码。详见 2.4 / 清单 18。

**Q2：兜底指向国内组，会不会让境外网站拿到污染答案？**
不会。走代理的域名由节点远程解析，根本不经过本地 `dns` 段；兜底组只服务 DIRECT 域名、节点域名、profile 自身依赖。而且「泄露到运营商」（不可撤销）比「答案被污染」（对国内/Apple 域名反而更快更准）致命得多。兜底组的唯一判据是「直连可达」，不是「指向境外」。

**Q3：为什么 `geoip: CN` 不能单独承担国内直连？**
`geoip: CN`（带 `no_resolve`）只对「已经是 IP」的连接生效。国内域名的直连完全依赖那份**纯域名的国内规则集**（`direct.txt`）。给 IP 规则补 `no_resolve` 会同时关掉「靠解析判 IP 归属」那条直连路径——所以补 `no_resolve` 的同一时刻，必须确认有一份含大量域名条目的国内规则集。这是清单 17 的核心。

**Q4：规则集里的 `no-resolve` 是必备的吗？**
不是「所有规则集都要」，而是**只有能匹配 IP 的规则才需要**：
- **纯域名规则集**（`direct.txt`、多数分区表）——只做域名串匹配，**任何情况下都不触发解析** ⇒ `no-resolve` 是空操作，写不写都一样，不是必需的。
- **含 IP-CIDR / IP-CIDR6 / IP-ASN 条目的规则集**（历史上 `Apple_All.list` 有 13 条裸 IP、`ChinaMax.list` 有 12,472 条 IP）——这些 IP 条目若不带 `no-resolve`，**每个走到该规则的域名都会被强制本地解析一次**（泄露来源 + 额外延迟）⇒ 这几条 IP 必须带 `no-resolve`。
- **profile 级 IP 规则**（`geoip` / `ip_cidr` / `asn`）——同理必须带 `no_resolve`。

一句话：**`no-resolve` 是「IP 规则的开关」，与域名规则无关。** 判据是「这条规则能不能匹配 IP」，而不是「别人的配置里写了没写」。代价见 Q3：给 IP 规则关掉解析判定后，必须用域名规则补回来。

> **实证（本模板）**：profile 里 `no_resolve` **只出现 1 次**（`geoip: CN`）。模板引用的 **21 个**远程规则集中，**11 个是纯域名**（`direct.txt` / Gemini / Claude / Anthropic / AI / GitHub / Microsoft / YouTubeMusic / AWAvenue-Ads / **jinx white-guard** / **jinx ads**，无需 `no-resolve`）、**10 个含 IP 条目**（Lan / ChatGPT / Spotify / YouTube / Google / Telegram / Twitter / WeChat / Apple、以及 disabled 的 Proxy），而这 10 个的 IP 条目**已在上游 `.list` 内全部自带 `,no-resolve`**（逐条核对：14/14、2/2、6+5、13/13、97/97 …）。所以「看起来到处是 `no-resolve`」是**上游规则集自带的**，不是 profile 在堆 —— profile 只需管好自己那一条 `geoip: CN`。

**Q5：`Foreign-DNS` 组去哪了？我还能用吗？**
`v2` 起已整段删除（迭代 v10 起它就无引用，`v1` 曾注释保留为 A/B 备用）。想用境外解析答案，需自行在 `upstreams` 里加回该组（6 个境外 DoH/DoT 端点），并把 forward 兜底 `value` 改过去。但注意：若它作兜底且代理未就绪，会掉进明文 `:53` —— 迭代 v10 默认用国内组兜底正是为了避免这条路径。

**Q6：模板为什么没有示例节点？**
避免占位节点在分流组里留下悬空引用（过度设计）。你填真实节点后，再把对应组的 `policies` 填上节点名 / 订阅组名。

**Q7：图标为什么都收进本仓库 `icons/`？**
为了避免模板跨项目引用图标地址（你的项目或别人的项目）。26 个图标已整合进 `icons/`，模板全部以本仓库原始地址引用，并保留来源署名。

**Q8：两个模板文件有什么区别？**
内容完全一致，仅注释差异。`profiles/v2.4.yaml` 带注释（每段附原理），`profiles/v2.4.min.yaml` 纯配置。按习惯取用其一（其余版本同理：`v0` / `v1` / `v2` / `v2.1` / `v2.2` / `v2.3` 各有这两份）。

**Q9：审计全绿就安全了吗？**
不。本项目连续 5 次「脚本 0 high、实测仍有问题」，根因是审计维度缺失（没看规则集文件、没看分流覆盖）。必须把每个新维度补成可复跑脚本，而不是重跑同一脚本。详见第 3 节 / 清单 16、17。

---

回到 [README](../README.md) ｜ 原理见 [docs/01](../docs/01-DNS是怎么工作的.md) ｜ 案例见 [docs/02](../docs/02-DNS为什么会泄露.md) ｜ 清单见 [docs/03](../docs/03-加固清单-18项.md)
