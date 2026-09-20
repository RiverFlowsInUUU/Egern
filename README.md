# Egern 防 DNS 泄露配置模板

> 一份面向**中国大陆网络环境**的 [Egern](https://egernapp.com) 配置模板：在**不把 DNS 泄露给运营商**的前提下，把国内外流量正确分流。

---

## 这是什么，解决什么问题

如果你在国内用代理工具，但 DNS 没配好，很容易出现 **DNS 泄露**：你的域名解析请求被中国电信 / 联通 / 移动的服务器看到，甚至被它直接回答。后果有两个，都很难受：

- **隐私泄露** —— 你访问了哪些域名，运营商一清二楚。
- **解析污染** —— 运营商还可能给你一个假的 IP 地址（这比"泄露"更糟，等于直接把你带到错误的地方）。

这个模板的目标只有两个，而且**必须同时成立**：

1. **不泄露** —— 任何一次解析，都不会落到「明文 UDP:53 → 运营商 DNS」这条路上。
2. **分流正确** —— 国内域名直连、境外域名走代理，不被"防泄露"的手段误伤。

> ⚠️ 这两个目标会互相拉扯。**治好泄露的那一手，往往正是搞坏分流的同一手** —— 本仓库最大的价值，就是把这层耦合讲清楚（见 [docs/05](docs/05-分流与no_resolve必须成对交付.md)）。

---

## 你拿到的是什么

- `profiles/egern-anti-dns-leak.template.yaml` —— **脱敏配置模板**，不含任何节点、订阅或证书，开箱即用为占位符。
- `docs/` —— 6 篇文档，从 DNS 原理讲到实战踩坑。
- `skill/` —— 一套审计脚本（可直接拷到 Agent Skills 目录），导入前后自动检查配置有没有漏洞。

**这不是一个能直接联网的成品**：节点和订阅必须你自己填。模板只负责"填进去之后不会泄露"。

---

## 5 分钟上手

```bash
# 1. 拿到模板
git clone https://github.com/RiverFlowsInUUU/egern-anti-dns-leak.git
# 或直接下载 profiles/egern-anti-dns-leak.template.yaml

# 2. 替换占位内容（只需 2 处，见下方「必须替换的清单」）
#    - proxies 段：6 个占位节点 -> 你自己的节点
#    - policy_groups 段：4 个机场订阅 URL -> 你自己的订阅

# 3. 导入 Egern

# 4. 导入前后跑审计（把 Profile.yaml 换成你的文件）
python skill/scripts/check_egern_dns.py         Profile.yaml
python skill/scripts/audit_ruleset_noresolve.py Profile.yaml
python skill/scripts/audit_routing_coverage.py  Profile.yaml

# 5. 在真实链路上验证：用蜂窝流量跑一次 leak test，确认结果里不再出现国内 ISP 的 IP
```

第 4 步三个脚本**都必须通过**才算过关：

| 脚本 | 期望输出 |
|---|---|
| `check_egern_dns.py` | `0 high`（`low` 是"有意为之"的说明项，可接受） |
| `audit_ruleset_noresolve.py` | `OK`（所有启用规则集的 IP 条目都带 `no-resolve`） |
| `audit_routing_coverage.py` | `OK —— 15 个国内探针全部命中 DIRECT` |

---

## 必须替换的清单（只需 2 处）

| # | 位置 | 占位内容 | 换成 |
|---|---|---|---|
| 1 | `proxies:` | 6 个占位节点（`203.0.113.10` / `example-node.com` / `example-node.net` / `example-cdn.com`） | 你自己的节点 |
| 2 | `policy_groups:` | `Airport-A` / `Airport-B` / `Airport-C` / `Airport-Free` 的 `urls`（`sub.example.com`） | 你自己的订阅地址 |

> **相比旧版，本模板不再需要在 `dns.forward` 里写任何节点域名 / 订阅耦合的规则。**
> `forward` 已塌缩为 2 条兜底 —— 换订阅、换机场、换节点域名**都不用改 DNS 配置**。这是 v10 的核心改动，
> 原理见 [docs/04 §2.3](docs/04-模板逐段讲解.md)。AI 相关策略组的图标 URL 是 `example-user/Rule` 占位，按需替换即可（图标缺失不影响功能）。

---

## 它是怎么防泄露的（一句话版）

泄露的根源是 Egern 的一条**明文 UDP:53 回退路径**（`bootstrap` → `system`）。只要它被触发一次，你的解析就可能被运营商看到。模板的全部工作，就是**让这条路径在结构上无事可做**：

- **加密 DNS 端点只写 IP 字面量**，不写主机名 ⇒ 不需要用它去解析任何东西（消灭 `bootstrap` 用途①）。
- **`proxy_nameservers` 显式设置**（国内 IP 端点）⇒ 代理侧解析绕过 `forward`，不回退明文（消灭隐式分支）。
- **`forward` 兜底指向"直连可达"的国内加密组**，而不是必须经代理的境外组 ⇒ 启动期代理没就绪时也不会掉进明文。
- **所有 IP 类规则带 `no_resolve`**，并配一份"域名条目足够多"的国内直连规则集（`ChinaMax_All_No_Resolve.list`）⇒ 治泄露的同时保住国内域名直连。

更完整的原理与 5 个真实泄露案例，见 [docs/01](docs/01-DNS是怎么工作的.md) 和 [docs/02](docs/02-DNS为什么会泄露.md)。

---

## 已知代价与取舍

- **规则集体积**：`ChinaMax_All_No_Resolve.list` 约 3.4 MB（11 万+ 域名）。首次加载 / 更新多一点时间和内存，之后走缓存。若你的设备内存紧张（< 256 MB 的路由器），可改用 `ChinaMax_Domain.list` + `geoip` 方案，但**必须先跑分流覆盖审计确认不会漏**（实测数据见 [docs/06](docs/06-实测数据与版本谱系.md)）。
- **兜底用国内 DNS**：走代理的域名由节点远程解析、不经过本地 `dns` 段，所以不受影响；本地解析只服务于国内与 Apple 域名，反而更快更准。
- **`proxy_nameservers` 是硬覆盖**：一设就绕过 `forward`。若发现"节点连不上"，第一件事是注释掉这 6 行。
- **模板不含 MITM**：原配置的 `ca_p12` 是个人 CA 私钥，**绝不能公开**。本模板的防泄露设计完全不需要 MITM。

---

## 隐私说明

本仓库是**纯模板**：节点地址、订阅链接、机场名、个人图标托管域名、CA 证书**全部已脱敏或占位**，不含有作者的任何私密信息。生成过程由 `_build_public_template.py` 自动校验（39 个敏感特征串零残留）。你可以放心 fork / 使用 / 二次发布。

---

## 常见问题

**Q：我是新手，这和我直接抄一份网上的配置有什么不同？**
A：网上的配置大多没考虑"审计通过 ≠ 不泄露"。本模板附带 3 个审计脚本，能在你把配置导入设备前就抓出 17 类常见漏洞（端点非 IP 字面量、兜底组不可达、规则集缺 `no-resolve`、分流被误伤等）。

**Q：一定要用 Egern 吗？**
A：模板是针对 Egern 的。但 `docs/` 里的原理和踩坑对所有代理工具（Surge / Clash / Quantumult X）通用 —— 尤其 Surge 那一版"一份加密 DNS + 全直连、不按域名分流 DNS"的思路，正是本模板 `forward` 塌缩的设计来源。

**Q：换节点 / 换机场后需要改 DNS 吗？**
A：不需要。把订阅 URL 换掉即可，`dns` 段保持原样。

**Q：审计全绿了，为什么还建议真机测？**
A：DNS 行为与运营商策略强相关；审计验证的是"配置本身没有漏洞"，不等于"你的某条链路上一定不泄露"。请按 [docs/06](docs/06-实测数据与版本谱系.md) 的方法，在**蜂窝流量**（而不是家庭 Wi-Fi，可能有旁路由）上实测。

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
│   └── 06-实测数据与版本谱系.md                 # 端点实测表、污染实测表、v1→v10 谱系
└── skill/
    ├── SKILL.md                               # 给 AI Agent 用的审计方法论（含 18 个已踩坑）
    └── scripts/
        ├── check_egern_dns.py                 # ① profile 层审计（15 项）
        ├── audit_ruleset_noresolve.py         # ② 规则集层审计（下载并数条目）
        ├── audit_routing_coverage.py          # ③ 分流覆盖审计（域名 → 命中规则 → 策略）
        ├── audit_dns_forward.py               # ④ forward 单值性 / 订阅耦合审计（v10 新增）
        ├── profile_ruleset.py                 # 规则集类型分布（识破"名字骗人"）
        ├── probe_dns_endpoints.py             # 端点逐个实测（DoH 线格式 / DoT 握手）
        └── probe_doh.py                       # 只测 DoH 线格式
```

> `skill/` 目录可以直接拷到 `~/.workbuddy/skills/`（或其它支持 Agent Skills 的目录）供 AI 复用。

---

## 许可

本项目以 **MIT 许可证**发布，详见仓库根目录的 [LICENSE](LICENSE) 文件。文档与配置模板可自由使用、修改与再分发。引用的第三方规则集版权归其原作者（[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)、[ACL4SSR](https://github.com/ACL4SSR/ACL4SSR)、[TG-Twilight/AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)、[Koolson/Qure](https://github.com/Koolson/Qure) 等），使用前请自行确认其许可条款。
