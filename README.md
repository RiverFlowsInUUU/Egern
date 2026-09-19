# Egern 防 DNS 泄露配置模板

一份**面向中国网络环境**的 [Egern](https://egernapp.com) 配置模板，以及配套的审计脚本与原理文档。

目标只有两个，而且必须**同时**成立：

1. **不泄露** —— 任何一次解析都不会落到「明文 UDP:53 → 运营商 DNS」这条路上。
2. **分流正确** —— 国内域名直连、境外域名走代理，不被"防泄露"的手段误伤。

> ⚠️ 这两个目标会互相拉扯。**治好泄露的那一手，往往正是搞坏分流的同一手** —— 本仓库最大的价值就是把这层耦合讲清楚（见 [docs/05](docs/05-分流与no_resolve必须成对交付.md)）。

---

## 30 秒速览：三条铁律

| # | 铁律 | 依据 |
|---|---|---|
| **1** | **加密 DNS 端点只写 IP 字面量，绝不写主机名。** | 官方文档：`bootstrap` 的用途之一就是"解析 `upstreams` 中加密 DNS 服务器的主机名"。端点上每写一个主机名，就必然产生一次**明文**查询。 |
| **2** | **所有 IP 类规则（`geoip`/`ip_cidr`/`ip_cidr6`/`asn`）必须带 `no_resolve`；同时必须有一份"域名条目足够多"的国内 DIRECT 规则集。** | `no_resolve` 是**用解析换分流**的开关。关了强制解析，也关掉了"靠解析判 IP 归属"的直连路径。两条必须成对交付。 |
| **3** | **`bootstrap` 唯一安全的形态是"永远不被触发"。** | 它是明文 UDP:53、直连。在中国运营商线路上，无论指向哪个 DNS 服务器 IP，都可能被透明重定向接管；失败后还会回落 `system`（= DHCP 下发的运营商 DNS）。**换个"更好的 bootstrap IP"没有意义 —— 实测换过，泄露的 ISP 没变。** |

---

## 泄露是怎么发生的（一图）

```
                     ┌──────────────────── 用户发起一次请求 ────────────────────┐
                     │                                                          │
                命中 DIRECT 规则？                                    命中 Proxy 规则？
                     │                                                          │
                     ▼                                                          ▼
        ┌────────────────────────┐                              ┌────────────────────────┐
        │      默认 DNS 解析      │                              │   交给节点远端解析      │
        │  (本机发起，需要答案)    │                              │  (不经过本地 dns 段)    │
        └───────────┬────────────┘                              └────────────────────────┘
                    │
                    ▼
        ┌────────────────────────┐
        │ forward 规则匹配上游组   │
        └───────────┬────────────┘
                    │
            ┌───────┴────────┐
            ▼                ▼
     命中 → 上游组        未命中 → 兜底组
            │                │
            └───────┬────────┘
                    ▼
        ┌────────────────────────┐        组内端点全失败？
        │  上游组：加密 DNS       │──────────────┐
        │  DoH :443 / DoT :853   │              │
        └────────────────────────┘              ▼
                                    ┌────────────────────────┐
                                    │  bootstrap（明文 :53） │  ← ★ 泄露点
                                    │  不遵循代理规则，直连   │
                                    └───────────┬────────────┘
                                                │ 仍然失败？
                                                ▼
                                    ┌────────────────────────┐
                                    │     system DNS         │  ← ★★ 泄露点
                                    │  = 运营商 DHCP 下发的   │
                                    └────────────────────────┘
```

**关键认知：泄露不一定来自"你选的 DNS 服务器"，而来自"你没意识到的解析"。**
上面那条 `bootstrap → system` 的明文回退分支，只要被触发一次，应答的解析器就可能变成运营商自己的服务器 —— 于是 leak test 上就出现"DNS 泄露到中国电信"。

因此本模板的全部工作，就是**让这条分支在结构上无事可做**：把它的两个用途（① 解析 `upstreams` 主机名；② 作为未命中时的回退）分别消灭掉。

---

## 快速开始

```bash
# 1. 拿到模板
git clone https://github.com/RiverFlowsInUUU/egern-anti-dns-leak.git
# 或直接下载 profiles/egern-anti-dns-leak.template.yaml

# 2. 替换占位内容（共 4 处，见 docs/04 的"必须替换的清单"）
#    - proxies 段：6 个占位节点 -> 你自己的节点
#    - policy_groups 段：Airport-A/B/C/Free 的订阅 URL -> 你自己的订阅
#    - dns.forward 段：example-node.com / example-node.net / example-cdn.com -> 你的节点域名
#    - 删除或本地填写 mitm 段（模板默认注释掉）

# 3. 导入 Egern，跑一次审计（把 profile 路径换成你的）
python skill/scripts/check_egern_dns.py            Profile.yaml
python skill/scripts/audit_ruleset_noresolve.py    Profile.yaml
python skill/scripts/audit_routing_coverage.py     Profile.yaml

# 4. 真机验证：在**蜂窝流量**上跑一次 leak test，确认不再出现国内 ISP 的 IP
```

第 3 步三个脚本都必须给出如下结果才算过关：

| 脚本 | 期望输出 |
|---|---|
| `check_egern_dns.py` | `0 high`（`low` 是"有意为之"的说明项，可接受） |
| `audit_ruleset_noresolve.py` | `OK`（所有启用规则集的 IP 条目都带 `no-resolve`） |
| `audit_routing_coverage.py` | `OK —— 15 个国内探针全部命中 DIRECT` |

---

## 仓库结构

```
├── README.md                                  # 你在这里
├── profiles/
│   └── egern-anti-dns-leak.template.yaml      # ★ 配置模板（已脱敏，无节点无订阅）
├── docs/
│   ├── 01-DNS是怎么工作的.md                   # 原理：递归、加密 DNS、Fake IP、Egern 双轨模型
│   ├── 02-DNS为什么会泄露.md                   # 5 个真实泄露案例 + 每个的机制与修法
│   ├── 03-加固清单-17项.md                     # 可逐条勾选的检查清单 + 验收 6 条
│   ├── 04-模板逐段讲解.md                      # 逐段讲这份模板为什么这么写
│   ├── 05-分流与no_resolve必须成对交付.md       # ★ 本项目最贵的一条教训
│   └── 06-实测数据与版本谱系.md                 # 端点实测表、污染实测表、v1→v8 谱系
└── skill/
    ├── SKILL.md                               # 给 AI Agent 用的审计方法论（含 17 坑）
    └── scripts/
        ├── check_egern_dns.py                 # ① profile 层审计（15 项）
        ├── audit_ruleset_noresolve.py         # ② 规则集层审计（下载并数条目）
        ├── audit_routing_coverage.py          # ③ 分流覆盖审计（域名 → 命中规则 → 策略）
        ├── profile_ruleset.py                 # 规则集类型分布（识破"名字骗人"）
        ├── probe_dns_endpoints.py             # 端点逐个实测（DoH 线格式 / DoT 握手）
        └── probe_doh.py                       # 只测 DoH 线格式
```

> `skill/` 目录可以直接拷到 `~/.workbuddy/skills/`（或其它支持 Agent Skills 的目录）供 AI 复用。

---

## 这份模板做了什么（相对一份"常规"配置）

| 项 | 常规写法 | 本模板 | 为什么 |
|---|---|---|---|
| 加密 DNS 端点 | `https://dns.alidns.com/dns-query` | `https://223.5.5.5/dns-query` | 消灭 bootstrap 用途①（主机名端点必被明文解析一次） |
| 未命中的兜底 | 指向境外组 | 指向**国内加密组**，并**双写** `domain_regex: '.'` + `domain_wildcard: '*'` | 兜底组的唯一判据是「**直连可达**」——境外组要经代理，启动期代理没就绪就会掉进明文 |
| `proxy_nameservers` | 不写（默认） | 显式写 6 个 IP 端点 | 官方语义：不写时"代理 DNS 未命中也会回退 bootstrap"——**不写这件事本身就留着一条明文分支** |
| IP 类规则 | 不带 `no_resolve` | 全部带 `no_resolve` | 不带 ⇒ 每个走到它的域名都被**强制预解析一次** |
| 国内直连 | 靠 `geoip: CN` 解析后判归属 | 靠 `ChinaMax_All_No_Resolve.list`（111,332 条域名） | 见铁律 2：`no_resolve` 一加，`geoip` 就不再匹配域名 |
| 节点域名解析 | 无显式规则 | `forward` 里显式指国内加密组 | 这是唯一**必定发生**的解析，且只能在直连侧做 |
| 延迟测试域名 | 无显式规则 | `cp.cloudflare.com` / `connectivitycheck.platform.hicloud.com` / `jsdelivr.net` 显式接住 | 这些名字**每轮节点测速都要解析一次**，是持续型泄露面 |
| 规则集来源 | `Apple_All.list` / `ChinaMax.list` | `Apple_All_No_Resolve.list` / `ChinaMax_All_No_Resolve.list` | 前者含**裸 IP 条目**（强制解析）；后者根本兜不住域名 |

---

## 已知代价与取舍

- **规则集体积**：`ChinaMax_All_No_Resolve.list` 约 3.4 MB（旧版 `ChinaMax.list` 约 454 KB）。首次加载/更新会多一点时间和内存，之后走缓存。若感知明显，可考虑改用 `ChinaMax_Domain.list`（纯域名）+ 保留 `geoip` 的方案，但**必须先跑分流覆盖审计确认不会漏**。
- **兜底用国内 DNS**：需要本地解析的**境外**域名会拿到国内答案（可能被污染）。按官方语义，走代理的域名由节点远程解析、不经过本地 `dns` 段，所以实际影响面仅限 DIRECT 域名 —— 对国内与 Apple 域名反而更快更准。
- **`proxy_nameservers` 是硬覆盖**：一设就绕过 `forward`。若你发现"节点连不上"，第一件事就是注释掉它。
- **模板不含 MITM**：原配置的 `ca_p12` 是个人 CA 私钥，**绝不能公开**（见 [docs/04](docs/04-模板逐段讲解.md)）。本模板的防泄露设计**完全不需要 MITM**。

---

## 免责

- 本项目提供的是**配置模板与审计工具**，不含任何节点、订阅或机场信息。
- 模板中的节点、订阅地址、域名均为占位符，请自行替换为你有权使用的资源。
- DNS 行为与运营商策略强相关，**审计通过 ≠ 你的线路上一定不泄露** —— 请按 [docs/06](docs/06-实测数据与版本谱系.md) 的方法在自己的链路（尤其是蜂窝流量）上实测。

## 许可

文档与配置模板可自由使用与修改。引用的第三方规则集版权归其原作者（[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)、[ACL4SSR](https://github.com/ACL4SSR/ACL4SSR)、[TG-Twilight/AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)、[Koolson/Qure](https://github.com/Koolson/Qure) 等）。
