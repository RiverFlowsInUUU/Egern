---
name: egern-profile-dns-hardening
description: 审计并加固 Egern 配置（Profile.yaml）的 DNS 泄露面与分流覆盖。触发词：Egern 配置、Egern 防 DNS 泄露、Egern dns 段、proxy_nameservers、hijack_dns、bootstrap 泄露、Egern dnsleak、节点域名明文解析、Egern 的 DNS 泄露到运营商（电信/联通/移动）、leak test 显示 china telecom、upstream 显示 bootstrap、日志里规则判定正常但 upstream 是 bootstrap、延迟测试域名泄露、cp.cloudflare.com 泄露、系统 DNS 回退泄露、Egern YAML 配置优化、egern no_resolve 路由、规则集 IP 条目缺 no-resolve、Apple_All.list 强制解析、blackmatrix7 No_Resolve 变体、rule_set 触发 DNS 解析、国内域名走代理、国内网站不是直连、chinamax 只有 ip 走直连、国内域名全落 final、加了 no_resolve 之后分流坏了、ChinaMax.list 没有域名规则、ChinaMax_All_No_Resolve、分流覆盖审计。
agent_created: true
---

# Egern 配置防 DNS 泄露

## 适用

用户给一份 Egern `Profile.yaml`（或含 `dns:` 段的 YAML），要求「防 DNS 泄露 / 别让 DNS 裸奔 / 检查 DNS 配置」，或反馈「实测有 DNS 泄露」。也可用于交付前自检。

## Egern 的 DNS 模型（不理解这个就会改错地方）

官方 `docs/configuration/dns` 定义**两条互不相通的解析路径**：

| 路径 | 用途 | 连接上游时 | 未命中时 |
|---|---|---|---|
| **默认 DNS** | 解析**用户要访问**的域名 | **遵循代理规则**（可走代理） | 回退 Bootstrap |
| **代理 DNS** | 官方措辞是"供代理服务解析目标域名"；但从"**强制直连**"这个约束反推，它实际承担的是**节点 `server` 的域名** —— 那个名字必须在隧道建立前解析出来 | **强制直连**（避免 DNS→代理→DNS 循环） | 未配 `proxy_nameservers` 时回退 Bootstrap |

⭐ **「强制直连」这条约束是理解一切的关键**：在国内，直连去问境外解析器（8.8.8.8:443 之类）基本不通。所以**代理侧的任何解析，只有两条出路：国内解析器，或者明文 bootstrap（223.5.5.5 → 也可能回落 `system` = 运营商）**。这条路径**无法加密**，只能靠"让它不需要解析"（节点写成 IP）或"给它一个确定的可达解析器"来收口。

⭐ **被忽略的最重要前提：`proxies[].server` 是域名还是 IP。** 本类事故里，**域名形式的节点必然产生一次「本机 + 直连 + 明文」解析**，这是整份配置里唯一**必定发生**的国内解析（不取决于用户访问什么网站，只取决于要连哪个节点）。**动手前先统计节点形式**：
```bash
python -c "import yaml;d=yaml.safe_load(open('Profile.yaml',encoding='utf-8'));print([(list(p.values())[0].get('name'),list(p.values())[0].get('server')) for p in d['proxies']])"
```


**社区事实标准配置（Repcz，被 Toperlock 等多仓库引用）有一句比官方文档更实用的话：**

> 「Egern 的解析规则接近 Surge，即**已经匹配到走节点的规则交由节点 dns 查询，dns 设置仅对需要本地解析的域名进行查询**」

→ **进代理的域名由节点远端解析；本地 `dns:` 段只服务「直连域名」和「代理节点自己的域名」。** 这决定了改哪里才有意义。

**Bootstrap 与回退链（这是"泄露到运营商"的唯一来源）**，官方原文：

> `bootstrap` …… 仅支持传统 UDP 协议（端口 53），且不遵循代理规则——**流量直连**。用途：① 解析 `upstreams` 中加密 DNS 服务器的主机名；② 作为最终的 DNS 回退。
> `bootstrap` …… **未配置或解析失败时，自动使用系统 DNS 服务器。**

**完整回退链：选中的上游解析失败 → bootstrap（明文 UDP:53、直连）→ 若 bootstrap 也失败 → system DNS（= 运营商 DHCP 下发的那台）。**

> 🚨 **国内运营商普遍对第三方明文 :53 做 DNS 重定向/调度。** 所以只要有任何查询落到 bootstrap 或 system 这两条明文路上，最终应答的解析器就可能变成**运营商自己的服务器** —— 用户就会看到「DNS 泄露到中国 ISP」。**这条路无法加密，唯一办法是让它永不触发。**

**推论：泄露只可能出在这几个位置** ——
1. `upstreams` / `proxy_nameservers` 里用了**域名**形式的加密 DNS（必被 bootstrap 明文解析一次）
2. ⭐ **节点 `server` 是域名，且 `forward` 里没有为它写显式规则**（→ 落境外组 → 直连通不了 → 回退明文 bootstrap / `system`）。**这是 CN 环境下最常见、也最容易被漏掉的一条。**
3. **回退被触发**（上游写错、端点失效、或端点路由被绕坏）→ 落到明文 bootstrap / system
4. **IP 类规则没 `no_resolve`**（为判定规则而触发解析）
5. **国内解析器被用在境外域名上**（见下）
6. ⭐ **profile 自身运行所必需的解析**（`proxy_latency_test_url` / `direct_latency_test_url` 的域名、策略组 `icon` 的域名）没有被靠前的 forward 规则接住。这些名字**普遍不在 ChinaDomain.list 里** —— 实测 `cp.cloudflare.com`、`connectivitycheck.platform.hicloud.com`、`jsdelivr.net`、`raw.githubusercontent.com` 全部 **0 命中**（表里唯一两条 cloudflare 还是注释掉的），于是整类落到兜底 = 境外组。而这类解析**每轮节点测速都要做一次**（策略组 `interval` 到点就全量测一遍），所以它的泄露是**持续型**的、与你访问什么网站无关。**这是继节点域名之后第二个必须显式接住的名字类别**（v3 漏的就是它）。

## ⚠️ 实测铁律：国内解析器不能用来解析境外域名

实测（本机出口直连，取 `www.google.com` 的 A 记录）：

| 端点 | RFC8484 线格式 | JSON API | `www.google.com` 返回 |
|---|---|---|---|
| `doh.18bit.cn` | 200 ✓ | 400 | `216.239.38.120` |
| `dns.alidns.com` | 200 ✓ | 400 | **`31.13.92.37`（Facebook 段，典型 GFW 污染签名）** |
| `doh.pub` | 200 ✓ | 200 | `174.132.167.252` |
| `dns.google` / `1.1.1.1` / `8.8.8.8` | 200 ✓ | 400/200 | `142.251.x.x` ✓ 真实地址 |

**结论：让国内解析器解境外域名，不是"泄露"这么轻 —— 是直接解析错（拿到污染 IP）。** 所有分岔设计都要围绕这条。

### ⚠️ 铁律修正：这条只约束"本地解析"，别把它套到兜底组上（2026-09-19 二次修正）

上面这条铁律有两个边界，不划清就会把配置改坏：

1. **它只约束"本地解析"这条路径。** 官方 DNS 文档 + 社区共识：**已经匹配到走节点的域名由节点远程解析**，本地 `dns:` 段只为"需要本地解析"的名字服务（DIRECT 域名、节点域名、profile 自身依赖）。所以**兜底指国内组，不会让"要访问的境外网站"拿到污染答案** —— 它只影响那些本来就走直连的域名。
2. **"泄露到运营商"和"答案被污染"是两个不同的问题，致命的是前者。** 一份把兜底挂在境外组、却在代理未就绪时回退明文的配置，比一份兜底用国内加密组的配置**危险得多**：前者泄露给运营商（不可撤销），后者最坏只是本地解析的 DIRECT 域名拿到国内答案（可接受，且对国内/Apple 域名反而更快更准）。

⇒ **兜底组的唯一判据是「直连可达」，不是「指向境外」。** 这条判据的代价是：我上一版审计里"兜底指国内 = HIGH"是**错判**，已撤回（见坑 13）。

## 审计清单

| # | 检查 | 判据 | 严重度 |
|---|---|---|---|
| 1 | `upstreams` / `proxy_nameservers` 的加密 DNS 是否 IP 字面量或已钉 hosts | 域名端点 → 必被 bootstrap 明文解析 | **境外域名=高**；国内域名=低 |
| 2 | ⭐ **`proxies[].server` 是域名的节点，它的解析走哪条路** | 节点域名走的是**代理 DNS**。v7 起 `proxy_nameservers` 已被显式设置 ⇒ 代理 DNS **跳过 `forward`**，只用那组 IP 字面量端点 ⇒ **不需要、也不应该**在 `forward` 里为节点域名写规则（那是死代码，见坑 18 / 清单 18）。判据从"forward 有没有接住"改成「**`proxy_nameservers` 是否显式设置、端点是否全为 IP 字面量**」 | **高** |
| 2b | `proxy_nameservers` 是否存在 | **v7 起必须显式写。** 它是**硬覆盖**：一设就绕过 `forward`、强制直连。**"不写"才是问题** —— 官方语义「未配置时，代理 DNS 与默认 DNS 共用 Forward 规则，**未命中回退 Bootstrap**」，等于留下一条通往明文 UDP:53 的兜底分支。只能用**国内**端点（代理 DNS 强制直连，境外解析器在电信线路上不可达） | **高（缺失时）** |
| 3 | ⭐ **DNS 端点是否有显式路由** | `geoip` 加了 `no_resolve` 就**不再匹配域名**；主机名形式的端点会落到 `default` → 国内端点被绕到境外出口 / 境外端点直连被阻断。**国内端点必须显式 → DIRECT，境外端点必须显式 → Proxy** | **高** |
| 4 | ⭐ **`forward` 里是否存在「捕获一切」的兜底，且该兜底组「直连可达」** | 兜底存在的意义只有一个：让"未命中的域名"不回退 bootstrap 明文。**判据是"这组在代理没起来时能不能工作"，不是"它指国内还是境外"** —— 组内端点必须全是 IP 字面量，**且至少一个端点在 `rules` 里被判给 `DIRECT`**。只判给 Proxy 的组 = 依赖代理 = 启动期（规则集/DB 下载、首轮测速）会掉进 bootstrap 明文。**兜底指国内组才是对的**（见"铁律修正"）。**写法要认全**：`domain_wildcard: '*'` **和** `domain_regex: '.'`（官方 PCRE2 find 式，命中任意子串）都算兜底 —— 别只认前一种（审计器 v2 就误判过）。推荐**两条都写**（互不依赖的双保险），并让 `domain_wildcard` 放最后便于人/工具识别 | **高** |
| 5 | `geoip` / `ip_cidr` / `ip_cidr6` / `asn` 是否带 `no_resolve` | 官方：`no_resolve` **仅适用这四类**；不加则规则会触发解析 | 高 |
| 6 | ⭐ **规则引用的策略能否解析** | `policy` 是嵌在类型字典里的（`{domain: {match, policy}}`），要读 `r[type]['policy']`。抓 `负载均衡` 这类笔误 | 高 |
| 7 | 硬编码 DoH IP（8.8.8.8 / 1.1.1.1 / 9.9.9.9 / OpenDNS…）是否有启用规则 → 代理 | `hijack_dns` 只覆盖 **:53**，App 用 DoH on **:443** 会绕过 | 中 |
| 8 | ⭐ **`rule_set.match` 是否为 URL 或文件路径** | 写成 `AI` / `抓取` / `Apple push` 这种名字 → 无法加载，等同死规则 | 中 |
| 9 | `block_ips` | 未设 → `0.0.0.0` 这类空路由式污染应答照单全收 | 低 |
| 10 | `real_ip_domains` | 为空 → 走不到隧道的流量（APNs / 内网）也拿 Fake IP，推送/内网会异常 | 低 |
| 11 | `ipv6` | `true` → AAAA 可绕过 IPv4 侧封堵 | 中 |
| 12 | `hijack_dns` 是否覆盖全部 | 官方 example 示例值即 `['*']`（= 接管 :53 并返回 Fake IP） | 高（缺失时） |
| 13 | `public_ip_lookup_url` | **不配置**才不发 ECS（不把公网 IP 交给 DNS 服务器） | 配了才是问题 |
| 14 | `skip_tls_verify` | 应为未设置 / `false` | 低 |
| 15 | ⭐ **profile 自身必需解析的名字**（两个 latency test URL 的域名 + 策略组 `icon` 的域名）是否被"兜底之前"的 forward 规则接住 | 没接住 → 落兜底=境外组 → 一旦这次解析发生在直连侧（代理 DNS 强制直连 / 无代理可用），境外组不可达 → 回退 bootstrap 明文 → 再落 `system` = 运营商。**延迟测试端点 = 高**（每轮测速都触发，持续泄露）；**图标 = 低**（失败只是图标不显示；硬钉到国内解析器反而可能拿到污染/`0.0.0.0` 应答，收益<风险，可故意不动） | **高**（前提：兜底组不安全；v6 起兜底已换成直连可达的国内组 ⇒ 落到兜底不再构成泄露，实际降级为 LOW，且 v10 起**连"单列规则"都不再需要** —— 见清单 18） |
| 16 | ⭐⭐ **远程规则集里有没有"不带 `no-resolve` 的 IP 类条目"** | 这是**最隐蔽的一类**：缺陷不在 profile 里，而在别人仓库的 `.list` 文件里。官方 rules 文档：`no_resolve` 为 true 才"不触发 DNS 解析" ⇒ **不带就触发**。一条启用的 `rule_set` 规则里只要有**一条**这种条目，**每个走到该规则的域名都会被强制本地解析一次**。实测 `blackmatrix7/Surge/Apple/Apple_All.list` 有 13 条（139.178.128.0/18 等 Apple CDN 段）—— 这就是"规则判定 `default → Final → Proxy`、upstream 却是 `bootstrap`"的成因（坑 16）。**必须逐个下载 + 数**，用 `scripts/audit_ruleset_noresolve.py` | **高** |
| 17 | ⭐⭐ **国内域名有没有"域名类"规则兜底**（不是"有没有一条叫 China 的规则"） | 给 IP 规则补 `no_resolve` 会**同时**关掉"靠解析判 IP 归属"这条直连路径。此时若没有一个**真正的域名规则集**接住国内域名，它们会整片落到 `default → Final → 代理`。判据：把规则集**下载下来数域名条目**（`DIRECT` 规则集域名条目 ≈ 0 就是这个坑），再用 `scripts/audit_routing_coverage.py` 拿真实域名走一遍。实测 `ChinaMax.list` 只有 64 条域名 / 12472 条 IP（仓库 README：它与 `ChinaMax_Domain.list` 需"共同使用"） | **高** |
| 18 | ⭐ **`dns.forward` 的 `value` 是不是单值？有没有把节点域名写死？** | 若所有规则的 `value` 相同 ⇒ **顺序与域名清单都不影响结果** ⇒ 本节对"换订阅/换机场"天然免疫；反之新域名会落到兜底组，必须先确认兜底组安全。另：节点域名的解析走**代理 DNS**，配了 `proxy_nameservers` 后官方明确"**跳过 Forward**" ⇒ **写在 `forward` 里的节点域名规则是死代码**（坑 18）。用 `scripts/audit_dns_forward.py` 跑，含"换订阅演练"（合成未来节点域名） | **中**（可维护性/耦合面） |

**关于 `no_resolve` 的三个层级，别混**：
1. **规则级**（`rules:` 里 `- geoip: {match: CN, policy: DIRECT, no_resolve: true}`）—— 官方明说**只适用 `geoip`/`ip_cidr`/`ip_cidr6`/`asn` 四类**，写在 `rule_set` 规则上**不生效**。
2. **规则集文件内的顶层字段**（Egern 原生 YAML 格式才有的 `no_resolve: true`）—— "影响所有 IP 相关规则"。
3. **规则集条目级**（Surge `.list` 里的 `IP-CIDR,x/y,no-resolve`）—— **第三方 `.list` 走的就是这一层**，也是坑 16 的战场。profile 写得再干净也管不到它。

**键名以 DNS 专页为准**：`domain` / `domain_suffix` / `domain_keyword` / `domain_wildcard` / `domain_regex` / `proxy_rule_set`。
`configuration/example` 页里出现的是 `wildcard` / `regex` 这类短名（且与同页的 `domain_suffix` 混用）—— 那是**陈旧/不一致**的写法，别照抄。`real_ip_domains`、`vif_only`、`include_all_networks`、`include_apns`、`compat_route`、`block_quic` 等顶层字段确实存在（以 example 页为准，没有 `general` 页）。

## 加固模板

```yaml
dns:
  bootstrap:                      # 只能明文 UDP:53 —— 本文件唯一无法加密、无法走代理的出口。
  - 223.5.5.5                     # 列 2 个以上国内公共 DNS：官方「解析失败时自动使用系统 DNS」，
  - 223.6.6.6                     # 而 system 在蜂窝下就是运营商。多列几个只为压低这一最坏分支。
  - 119.29.29.29                  # ⚠️ 绝不写 system —— 那是主动把运营商解析器接进回退链。
  upstreams:
    Domestic-DNS:                 # 国内域名 → 国内加密 DNS。★ 全部写 IP 字面量：
    - https://223.5.5.5/dns-query  #   端点上每写一个主机名，官方就会用明文 bootstrap 解析它一次
    - https://223.6.6.6/dns-query  #   （bootstrap 用途①）。写 IP 则一次都不产生，且零依赖。
    - https://1.12.12.12/dns-query #   下面 6 个已实测通过（含证书覆盖 IP），两家机构 × 两种协议。
    - https://120.53.53.53/dns-query
    - tls://223.5.5.5
    - tls://1.12.12.12
    Foreign-DNS:                  # ★ 一律 IP 字面量，杜绝 bootstrap 解析
    - https://8.8.8.8/dns-query    # 需在 rules 里把这些 IP 显式判给 Proxy，链路才是
    - https://8.8.4.4/dns-query    # 「设备 → 代理 → 8.8.8.8」，从国内蜂窝也能建起来。
    - https://1.1.1.1/dns-query    # 多列端点：官方「组内并发竞速、最快者胜」，
    - https://1.0.0.1/dns-query    # 触发回退的唯一条件是「本组全失败」，端点越多越不可能。
    - tls://8.8.8.8
    - tls://9.9.9.9                # ⚠️ Quad9 只能走 DoT：其 9.9.9.9 的 DoH 实测
                                  #    返回 HTTP Version Not Supported（只提供 HTTP/3）
                                  #    写 https://9.9.9.9/dns-query 会静默失效。
    # ⚠️⚠️ 本组**不要**用作 forward 的兜底 —— 它必须经代理才可达，把兜底挂在它身上等于
    #      「先有代理，才敢解析」，代理未就绪时那次解析会掉进 bootstrap 明文（见坑 13）。
  forward:                        # ★★ v10 起只留兜底 —— **不要在这里写任何具体域名**（坑 18）
  - domain_regex:                 # ★★ 双保险之一：官方 PCRE2 find 式，'.' 必然命中任何域名
      match: '.'
      value: Domestic-DNS         # ★★ 兜底指向「直连可达」的国内加密组 —— 不是境外组。
  - domain_wildcard:              #    境外组必须经代理，代理没就绪时兜底就会掉进 bootstrap
      match: '*'                  #    明文（见坑 13）。按官方语义走代理的域名由节点远程解析，
      value: Domestic-DNS         #    本地 dns 段只服务 DIRECT 域名，所以国内组没有副作用。
  # ★ 为什么不需要 `.cn` / 国内域名表 / 节点域名 / 延迟测试域名 / 图标域名这些规则：
  #   ① 它们的 value 与兜底**完全相同** ⇒ 单值集合里"命中顺序"不产生任何影响，删掉也不变（清单 18）。
  #      官方那句"第一条命中的决定上游"只在 value 有差异时才有意义。
  #   ② 节点域名的解析走**代理 DNS**，配了 proxy_nameservers 后官方明确"**跳过 Forward**"
  #      ⇒ 写在 forward 里的节点域名规则是**死代码**（v7 之前它有用，v7 之后退役）。
  #   ③ 延迟测试域名与图标域名同理：v4 加它们是因为当时兜底是境外组（不安全）；
  #      v6 把兜底换成国内组之后，它们就已被兜底覆盖。
  #   ⚠️ 千万别为了"看起来严谨"再往这里堆域名 —— 每堆一条就把"换订阅"变成一次复查配置的义务。
  # ★★ v7 起必须显式写 proxy_nameservers —— 不写就等于留下一条通往明文 UDP:53 的兜底分支：
  #   官方原文：「未配置时，代理 DNS 与默认 DNS 共用 Forward 规则，**未命中回退到 Bootstrap**」；
  #   配置后语义：「所有代理 DNS 查询强制走该列表，**Forward 规则会被跳过**」。
  #   只能用国内端点 —— 代理 DNS **强制直连**，境外解析器在电信线路上不可达。
  proxy_nameservers:
  - https://223.5.5.5/dns-query
  - https://223.6.6.6/dns-query
  - https://1.12.12.12/dns-query
  - https://120.53.53.53/dns-query
  - tls://223.5.5.5
  - tls://1.12.12.12
  # ⚠️ 如果你发现"节点连不上"，第一件事是注释掉这 6 行（等价于回到 v6 的行为）。
  hosts:                          # ★ 把上面 DoH 域名钉到 IP（仅当 IP 固定）
    dns.alidns.com: [223.5.5.5, 223.6.6.6]
    doh.pub: [1.12.12.12, 120.53.53.53]
    dot.pub: [1.12.12.12, 120.53.53.53]
  block_ips:                      # 丢弃空路由式污染应答；别放私网段免得误伤内网
  - 0.0.0.0
  - 127.0.0.1

rules:
# ★★ DNS 端点固定路由必须放在 rules 最前 —— geoip 带 no_resolve 后不再匹配域名，
#    主机名形式的端点会落到 default。国内端点不钉住就会被绕到境外出口。
- domain_suffix:
    match: alidns.com
    policy: DIRECT
- domain:
    match: doh.pub
    policy: DIRECT
- ip_cidr:
    match: 223.5.5.5/32
    policy: DIRECT
    no_resolve: true
# ... 223.6.6.6 / 1.12.12.12 / 120.53.53.53 同样处理
- domain:
    match: dns.google
    policy: Proxy
- domain_suffix:
    match: cloudflare-dns.com
    policy: Proxy
- ip_cidr:                        # ★ 兜住「App 硬编码 DoH IP + :443 绕过 hijack」
    match: 8.8.8.8/32
    policy: Proxy
    no_resolve: true
# ... 8.8.4.4 / 1.1.1.1 / 1.0.0.1 / 9.9.9.9 / 208.67.222.222 / 208.67.220.220
# ---- 以下是原有规则 ----
# ... 最后（顺序很关键：国内域名兜底必须在 default 之前）：
- rule_set:                      # ★★ 国内域名直连兜底（坑 17）—— 必须用域名条目足够多的那份：
    match: https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/ChinaMax/ChinaMax_All_No_Resolve.list
    policy: DIRECT               #   111332 条域名 + 12473 条 IP（IP 全带 no-resolve）
                                 #   ❌ 别用 ChinaMax.list：它只是 IP 规则集，域名只有 64 条
- domain_suffix:                  # ★ 补 .cn 直连兜底：不依赖上面那份规则集是否加载成功
    match: cn
    policy: DIRECT
- geoip:                          # ★ 不加 no_resolve 会为每次判定触发解析
    match: CN
    policy: DIRECT
    no_resolve: true
- default:
    policy: <代理组>
```

顶层另加：`ipv6: false`、`hijack_dns: ['*']`、`real_ip_domains: ['*.lan','*.local','*.push.apple.com']`。

⭐ **v10 起不要做这一步（它的反面才是对的）**：早期版本（v3）要求"把域名形式的节点逐个写成 `domain_suffix → Domestic-DNS`"，因为那时代理 DNS 会共用 `forward`。**v7 显式写出 `proxy_nameservers` 之后，代理 DNS 会跳过 `forward`** ⇒ 那些规则再也没被查询过（死代码，坑 18）。现在只需保证两件事：

1. `proxy_nameservers` **显式设置**，端点全部是**国内可达的 IP 字面量** —— 它是节点域名解析的唯一出口；
2. `forward` **只留兜底**，且兜底组「直连可达」。

⚠️ 顺序仍不能反：**先把解析路径收口（这两条），再去调 `upstreams` 里的解析器**。理由没变 —— 这些名字在隧道建立前必须被解析，而代理侧强制直连，国内根本问不到境外解析器。**但收口的手段是"把代理 DNS 钉死"，不是"在 forward 里列举域名"。**

⭐ **同理，profile 自身运行必需的域名**（`proxy_latency_test_url` / `direct_latency_test_url` / 策略组 `icon`）**也不需要单列规则**：v6 起兜底已是国内加密组，它们天然被覆盖。它们只在**兜底是境外组的配置里**才会造成持续泄露 —— 那正是 v4 加它们的场景。用 `audit_dns_forward.py --drill` 可验证任何域名（含这两类）都落到安全的兜底。

## 判断 hosts 能不能钉

**先实测解析**，IP 固定才钉；CDN 池不能钉（钉了反而破坏轮换）：

```bash
python -c "
import socket
for h in ['dns.alidns.com','doh.pub','doh.18bit.cn']:
    print(h, sorted({a[4][0] for a in socket.getaddrinfo(h,443)}))"
```

实测参考：`dns.alidns.com`→223.5.5.5/223.6.6.6（固定 ✅）、`doh.pub`→1.12.12.12/120.53.53.53（固定 ✅）、`doh.18bit.cn`→**11 个 IP 的 CDN 池（不可钉 ❌）**，且它落在 **42.51.x.x（中国联通）** 上的自建服务 —— 能用作国内上游，但别让它承担"所有国内域名"。

## ⚠️ 已踩过的坑（别再犯）

**坑 1：用 JSON API 判 DoH 端点死活 → 误判。**
`?name=x&type=A` + `accept: application/dns-json` 是 Google 风格的**可选** JSON API。RFC 8484 只强制**线格式**（`?dns=<base64url>` + `accept: application/dns-message`）。`dns.google`、`8.8.8.8`、`dns.alidns.com` 用 JSON 都会回 400 —— 它们没坏。**判断端点是否可用，只能用 `scripts/probe_doh.py` 的线格式请求。**

**坑 2：给 `geoip` 加 `no_resolve` 会悄悄改掉 DNS 端点的路由。**
`no_resolve: true` 之后 geoip **不再匹配域名**（官方："仅匹配已解析的 IP 地址"）。于是以主机名出现的加密 DNS 端点失去「CN → DIRECT」，只能靠某个 rule_set 里的 `DOMAIN-SUFFIX,cn` 兜住 —— 而那个规则集一旦加载失败（例如含 Egern 未文档化的类型），国内 DNS 查询就落到 `default → 代理`，被绕到境外出口再回国内，超时后**回退明文 bootstrap → 运营商 DNS**。**这就是"DNS 泄露到运营商"的完整机制链。修法：给每个 DNS 端点写显式路由（见模板），别依赖规则集内容。**

**坑 3：自己的审计脚本只能验证自己编码进去的假设。** 脚本报 `0 high` 不等于真的没泄露。用户实测出泄露时，必须回到**机制层**重新推导（回退链 / 端点路由 / 分组兜底），而不是重跑同一个脚本。

**坑 4：别假定 `.list` 是域名表。** 实测 `ChinaMax.list`：12614 条里 **12472 条是 IP-CIDR/IP-CIDR6**，域名只有 64 条，还含 65 条 `USER-AGENT` 和 **12 条 `PROCESS-NAME`（Egern 未文档化）**。用之前**下载 + 统计类型分布**（见 `scripts/profile_ruleset.py`）。这类巨型 IP 集合没有 `no_resolve`，是个持续触发本地解析的开销源。
　→ ⚠️ **这条不只是"别误判"，它还有直接的后果**：把它当"国内域名走直连"的兜底规则用，等于没有兜底。真正能兜住的是 `ChinaMax_All_No_Resolve.list`（111k 域名 + 同份 IP，IP 条目全带 `no-resolve`）。详见**坑 17**。

**坑 5：`policy` 嵌在类型字典里。** `- domain: {match: x, policy: Proxy}` —— 读 `r.get('policy')` 永远得到 `None`（审计器 v1 就是这么废掉的）。要读 `r[type]['policy']`。

**坑 6：`proxy_nameservers` 不是"多加一层保险"，是"砍掉整条 forward"。**
官方：一旦设置，**所有代理 DNS 查询强制走它、完全绕过 `forward` 规则、且强制直连**。所以"顺手加一行指向阿里/腾讯"这件事，实际效果是**把代理侧解析无条件钉死在国内解析器上**（哪怕 `forward` 里已经把节点域名引到了正确的组）。**默认不要设它**；要设必须能说清为什么，并在报告里写明"成为唯一出口"的代价。**实测教训：v1 加了它 → 用户实测仍泄露，且比原配置更确定。**

**坑 7：审计器的"兜底判定"不要只认一种写法。** v2 里把 `has_catchall` 写成「最后一条必须是 `domain_wildcard: '*'`」，于是配置里写 `domain_regex: '.'` 这条等效兜底时被误报 HIGH、而 `domain_wildcard` 前面的同义兜底又被算成"靠前规则指向境外组"报了假 LOW。**判定要按语义（是否覆盖一切域名）而不是按字面键名+位置**；同时必须显式排除兜底规则本身，避免它污染"靠前规则"检查。修好后同一份 v3 从 `1 high/3 low` 变成 `0 high/1 low`。

**坑 8：`forward` 里的 `proxy_rule_set` 若含 IP 类条目且不带 `no-resolve`，会为了判定而强制一次预解析。** 实测 `ChinaDomain.list` 里那 9 条 `IP-CIDR(6)` 都带 `no-resolve`，所以安全；但用户自选的规则集不保证。审这类文件时**一定要数类型分布**（`scripts/profile_ruleset.py`）。

**坑 9：审计器"看不见"的那一类名字，就是最终泄露的那一类。**
v3 的审计结果是 `0 high / 1 low`，但用户实测**持续泄露到中国电信**。原因是脚本只检查了「用户会访问的域名」和「节点域名」，**从没把 profile 自己运行必需的域名（延迟测试 URL、策略组图标）拉进来做覆盖判定**。补上这项检查后：原始配置 `4 high`、**v3 `2 high`**（两个 latency test 域名）、v4 `0 high` —— **v3 的"0 high"是审计盲区造成的假安心**。
同时修掉一个 helper bug：`hostpart()` 里 `SCHEME` 白名单只有 `udp|tls|https|quic|h3`，遇到 `http://…`（延迟测试 URL 正是这种）不剥离协议头，再按 `:` 切就得到假主机名 **`'http'`**，导致检查结果牛头不对马嘴。**修法：先按 `'://'` 通用剥离，不依赖协议白名单。**（检查一个 URL 类字段的解析结果时，务必先打印几个样例看看解析出来的是什么。）

**坑 10：官方文档说"未配置或解析失败时自动使用系统 DNS"—— 这句是"运营商泄露"的入口，别只当兜底描述读。** 它意味着**任何一次上游失败都可能把查询交给你家路由器的 DNS**。所以在 CN 环境下，判断标准不是"我配的解析器够不够好"，而是"**有没有任何一条路径会失败**"。
配套的另一半在同一页：bootstrap 的**用途①是「解析 `upstreams` 中加密 DNS 服务器的主机名」**。所以**端点上每写一个主机名，就多欠一次明文查询**；写 IP 字面量则一次都不产生。这也解释了官方示例为什么写成 `https://8.8.8.8/dns-query` 而不是 `https://dns.google/dns-query`。
顺带：`bootstrap` 里的特殊值 `system` = 「合并系统 DNS（Wi-Fi/**蜂窝网络下发**的 DNS）」→ **在配置里写 `system` 等于主动把运营商解析器接进回退链**，审计器现在把这条判 HIGH。

**坑 11（流程坑，代价最大）：先确认"用户是在什么设备、什么链路上测的"，再谈机制。**
本次真实事故：用户报"新规则会泄露中国的 ISP"，我**默认他在和之前同一台 Windows + 同一张旁路由网络上测**，于是花了一整轮做本机网络侧实测（`:53` 被旁路由劫持成 `198.18.x`、`whoami.akamai.net → 219.128.79.150`），并据此产出一份"根因报告"。下一句用户说"**leak test 肯定是 iPhone 上跑的，用流量**" —— **旁路由根本不在链路上，那整套证据与结论全部作废**。
**规矩：动手前先问清三件事 —— ① 哪台设备（有没有可能根本没装这个客户端）；② 哪条链路（Wi-Fi / 蜂窝 / 有线）；③ 谁提供的 DNS（家庭路由器 / 运营商 / 系统级加密 DNS）。** 不同链路下"明文 :53 的下场"完全不同：
- 家庭网 + 旁路由：:53 被透明重定向到旁路由的 Fake IP（**看起来像"解析成功但返回假 IP"**）；
- 运营商蜂窝：:53 被运营商透明重定向到它自己的递归解析器，或直接不通后掉到系统 DNS（**看起来就是"leak test 显示运营商"**）。
两种都是同一条"明文回退"链，但**要拿的实测数据完全不同**。先问，再测。

**坑 12：端点写成 IP 字面量之前，必须逐个实测它真的能用。**
"IP 字面量 + 证书覆盖该 IP"不是想当然的。实测：`https://223.5.5.5/dns-query`、`https://1.12.12.12/dns-query`、`tls://1.12.12.12` 都正常；但 **`https://9.9.9.9/dns-query` 直接失败 —— `HTTP Version Not Supported`**（Quad9 在 `9.9.9.9` 上只提供 HTTP/3，不响应 RFC8484 的 HTTP/1.1 线格式；`149.112.112.112` 同样），而 **`tls://9.9.9.9` 正常**（证书 `CN=dns.quad9.net`）。**写错形式 = 白占一个端点，而且它是"静默失效"**，不会在配置校验时报错。
测法见 `scripts/probe_dns_endpoints.py` —— **直接吃 profile 文件**，把 `upstreams` / `proxy_nameservers` / `bootstrap` 里每个端点逐个跑一遍（DoH 走 RFC8484 线格式、DoT 走 853 握手并校验证书、裸 IP 走 UDP:53），最后输出「失效端点 N / M」。**加固后报告里附上这张表，别只写"端点已改 IP"。**（v5 实测：15 个端点 0 失效。对候选端点应**连测 3 轮**再下"稳定/不稳"的结论 —— 本次就吃过一次单轮抖动误判。）

**坑 13：兜底组挂在"必须经代理才可达"的组上 —— 审计器判 OK，用户实测却是 `upstream: bootstrap`。**
本次事故：v5 把兜底指向 `Foreign-DNS`（端点全为 IP 字面量、且都在 `rules` 里判给 Proxy），审计判 `0 high`。用户复测报 **`upstream: bootstrap`**。复盘出两个漏洞：
1. 官方只写了「未命中 Forward 回退 Bootstrap」，**"命中组的端点全失败"会怎样并没有写** —— 未定义行为。一旦它同样回退 bootstrap，兜底挂在境外组就是一条明文通道。
2. 兜底组经代理 ⇒ 引入隐式依赖「**先有代理，才敢解析**」。**启动阶段**（规则集与 `geoip_db_url` / `asn_db_url` 的下载、策略组首轮测速）代理尚未就绪，这一刻的本地解析会掉进 bootstrap 明文。本次配置里 `raw.githubusercontent.com` 正是这类**启动依赖**（规则集 + 两个 DB + 用户自己的策略组图标都托管在它上面），在 v5 里它落到兜底 → 境外组 → 启动期必然失败。
⇒ **判据收紧为「端点全为 IP 字面量 + 至少一个在 `rules` 里判给 `DIRECT`」**（即"直连可达"，而非"路由确定"）。修好后 v5 `1 high`、v6 `0 high`。**教训：对"审计器给了 OK"保持不信任 —— 脚本只能验证你编码进去的假设，而"这组在代理没起来时还能用吗"从来不在假设里。**

⚠️ **该判据在 v10（2026-09-20）后被双向化 —— 别再用上面那半句当完整判据。** v10 删掉了全部 15 条 DNS 端点路由规则（`upstreams`/`proxy_nameservers`/`bootstrap` 全是 IP 字面量 ⇒ 解析器直接以 IP 访问，不需要在 `rules` 里钉域名/IP），于是「至少一个在 `rules` 里判给 `DIRECT`」这半句**永远不成立** ⇒ 脚本把自有模板误判 `3 high`、退出码 1（外部审查报告抓到的就是这个）。
现在的完整判据是**两条二选一**：
- **(a) 旧判据**：端点全为 IP 字面量，**且至少一个在 `rules` 里判给 `DIRECT`**（适用于把 DNS 端点显式路由的配置）；**或**
- **(b) 新判据**：端点全为 IP 字面量，**且至少一个是已知的国内解析器 IP**（`check_egern_dns.py` 里的 `DOMESTIC_RESOLVER_IPS` 白名单：223.5.5.5 / 223.6.6.6 / 119.29.29.29 / 1.12.12.12 / 120.53.53.53 / 114.114.114.114 / 180.76.76.76 …）—— 国内到这些 IP 的可达性是**公共事实**，不需要在 profile 里用路由来"证明"。

❗ **绝不要采纳「端点全为 IP 即充分」这种更宽的写法** —— 一个全为境外 IP 的组（如纯 `8.8.8.8`）虽是 IP 字面量，却必须经代理才可达，那会**直接回退到坑 13 的 v5 事故形态**。放宽必须保留收紧面。
回归守卫：`tests/` 目录下有五份合成 profile —— **改 `group_reach` 判据后必须五份都跑**
（或直接 `bash tests/run.sh`，它把五份同时喂给两个脚本、共 10 个断言）：

| profile | 构造 | 期望 | 命令 |
|---|---|---|---|
| `tests/bad_foreign.yaml` | 兜底组端点全为**境外** IP（`8.8.8.8` / `1.1.1.1`） | **HIGH + 退出码 1** | `check_egern_dns.py tests/bad_foreign.yaml` |
| `tests/bad_hostname.yaml` | 兜底组端点含**主机名**（`dns.alidns.com`） | **HIGH + 退出码 1** | `check_egern_dns.py tests/bad_hostname.yaml` |
| `tests/ok_route.yaml` | 兜底组端点全为国内 IP **且有显式 `ip_cidr → DIRECT`**（走判据 A） | **通过 + 退出码 0** | `check_egern_dns.py tests/ok_route.yaml` |
| `tests/ipv6_only.yaml` | 端点仅 IPv6 国内解析器（`[2400:3200::1]`） | **通过 + 退出码 0，且两脚本结论必须一致** | `bash tests/run.sh` |
| `tests/scheme_case.yaml` | 端点 scheme 写成大写（`HTTPS://` / `TLS://`），其余与 `ok_route.yaml` **逐字相同** | **通过 + 退出码 0，结论必须与 `ok_route.yaml` 完全相同** | `bash tests/run.sh` |

前两个是**收紧面**（证明判据没被放宽成"全 IP 即安全"）；后三个是**放行面**（分别证明判据 A 路径、
IPv6 端点解析、scheme 任意拼法都仍有效）。后两份的期望值都必须在**修 bug 之前先验证它会失败** ——
否则只是个恒绿的摆设。

⭐ **同一判据只要在第二处有实现，就必须在注释里互指。** `audit_dns_forward.py` 的 `endpoint_route`/`direct_ips` 与 `check_egern_dns.py` 的 `group_reach` 是**同一判据的副本** —— 只改一个，两个脚本就会给出相反结论（比没有脚本更糟）。改判据时**两处一起改**，并跑 `check_egern_dns.py` + `audit_dns_forward.py --drill` 双确认。

**坑 14：看到客户端词汇表里的名字（`bootstrap` / `system`），一步就能锁定"明文回退面"。**
`bootstrap` 不是网络上的实体，是 **Egern 内部给启动 DNS 组起的名字** —— 官方把它和 `system` 并列为可直接引用的 upstream 值（`bootstrap` 展开为全部 Bootstrap 服务器，`system` 展开为系统 DNS），而这个字符串**第三方泄露测试站不可能打印**（它们只给 IP / ASN / 国家）。所以一旦用户报出它，就说明**有一次查询确实走了明文 UDP:53**，范围立刻锁死到"谁把它推上去的"：
- **用途①** 解析 `upstreams` 里的主机名端点 → 查端点是不是域名；
- **用途②** 未命中 Forward 的最终回退 → 查兜底在不在、兜底组可不可直连。
反过来也成立：**报"泄露到某运营商"时，先索要这一栏的名字**（是 IP？还是 `bootstrap` 这类客户端标签？），比让他描述"访问哪个网站"有用得多。

**坑 15：漏写 `no_resolve` 的 `geoip`，会给每一个走到它的域名强制一次本地预解析 —— leak test 的随机子域正是靠这条路进场的。**
官方 rules 文档：`no_resolve` **只适用 `geoip` / `ip_cidr` / `ip_cidr6` / `asn` 四类**，语义是"不触发 DNS 解析"。**不写 = 为了判定归属必须先解析一次**。本次事故的完整链（每一步都在配置里有坐标）：
```
aaaa.dnsleaktest.com（随机子域）
  → 不在任何规则集里（实测 bm7-Proxy / Apple_All / ChinaMax / Lan / ChinaDomain 全部 0 命中）
  → 落到 rules 里那条 geoip:CN（原配置没有 no_resolve）⇒ 强制本地解析一次
  → 默认 DNS → forward 兜底 → Foreign-DNS（端点是主机名 dns.google / cloudflare-dns.com）
  → Bootstrap 用途①：明文 UDP:53 解析 dns.google ⇒ 蜂窝上被运营商接管 ⇒ 解析器归属 = 运营商
```
**两个必要条件缺一不可**（漏 `no_resolve` + 主机名端点），这也是为什么泄露表现为"每测一次漏一次"。**审别人的配置时，`geoip`/`ip_cidr` 的 `no_resolve` 要当成 P0 项看。**

**坑 16（v7 的真正解法，也是最反直觉的一条）：强制解析不写在 profile 里，藏在别人仓库的 `.list` 里。**
本次的真实链路（用户报了 `default → Final → Proxy` + `upstream: bootstrap` 同时出现）：
```
aaaa.dnsleaktest.com
  → rules 0..40 全不命中（实测这些规则集里确实没有 dnsleaktest）
  → 命中 rules[41]  rule_set: Apple_All.list → DIRECT，**enabled**
       而该文件里有 13 条 `IP-CIDR,x/y` **没带 ,no-resolve**
       ⇒ 官方语义：不带 = 会触发解析 ⇒ **为了判定这条 IP 规则，先强制本地解析一次**
  → 这次解析走了明文（日志里的 `upstream: bootstrap`）
  → 之后继续往下匹配，42/44/45/46 都不中 → rules[47] `default → Final → Proxy`
  ⇒ 于是日志里"判定"与"解析"看起来矛盾：「default → Final → Proxy」但 upstream 是 bootstrap
```
**诊断要点：`upstream: <明文标签>` 与"判定结果看起来没问题"同时出现 ⇒ 去找"为了判定某个规则而被迫发生的解析"。**
排查顺序：把 profile 里**所有** `rule_set` / `proxy_rule_set` 的 URL 抓下来，逐个统计"IP 类条目里有多少条不带 `no-resolve`"，并确认该规则 `disabled` 与否。实测 22 个规则集的结论（含 2026-09-21 新增的 `white-guard` / `ads`，两条均为纯域名、无 IP 条目）：**只有 `Apple_All.list` 有问题（13/13 全裸）**，其余（含 12614 条的 `ChinaMax.list`，12473 条 IP 全带）都干净 —— 所以这类问题不是"普遍存在"，而是**个别文件埋的雷，必须逐个核对**。

**修法优先级**：
1. ⭐ **换用同源等价文件**。blackmatrix7 的命名约定：`XXX.list`（标准）/ **`XXX_No_Resolve.list`（IP 条目全带 no-resolve，首选）** / `XXX_Resolve.list`（全不带）/ `XXX_Domain.list`（纯域名）。Apple 实测 `Apple_All_No_Resolve.list` 与 `Apple_All.list` 在**去掉 `,no-resolve` 后 1616 条逐条相同** ⇒ 换 URL 就完事，覆盖范围零损失，**对 IP 形式的连接判定也完全不受影响**（IP 本就不需要解析）。
   换用前**必须**跑一次归一化比对（去掉 `,no-resolve` 后是否逐条相同），否则可能悄悄换了覆盖范围。
2. 上游没有 No_Resolve 变体 → 自建镜像，把那几条 IP 条目补上 `,no-resolve` 再托管。
3. 下策：整条规则 `disabled: true`（会丢掉该规则集的路由能力）。
❌ **不要**试图在 `rule_set` 规则上写 `no_resolve: true` —— 官方明说只适用 IP 类规则，写了也不生效（写了还可能被当成未知字段）。

顺带记一条实测修正：`ChinaDomain.list` 用 `curl` 直接抓会拿到 0 条（`github.com/.../raw/...` 是 301，**必须加 `-L`**）。用 `-L` 后是 635 条、9 条 IP 全带 no-resolve。审规则集时 curl 漏了 `-L` 会得出"这文件是空的"的错误结论。

**坑 17（v8 的教训，也是全项目最值得记的一条）：治好 DNS 泄露的那一手，会顺手把国内域名的分流一起干掉 —— 它们是同一个机制。**

用户 v7 复测："没有 dns 泄露了，可是国内外的分流好像出了问题，国内网站都不是直连反而走了代理，chinamax 基本都是一些 ip 走了直连，而国内域名基本都走了 final。"

这不是"新引入的 bug"，而是**同一次改动的另一面**：

```
原始配置：国内域名 → 命中 geoip:CN（**没有** no_resolve）
             → 为判定归属**强制本地解析一次**（← 这就是当年的 DNS 泄露）
             → 判出 CN IP → DIRECT ✅（← 这就是当年的国内直连）
v7 改动：geoip:CN 补上 no_resolve: true（官方：不再触发解析）
             → 泄露没了 ✅
             → 但 geoip **不再匹配域名**，那条"解析判归属"的直连路径也一起没了 ❌
             → 本该补位的 ChinaMax 规则**不含域名规则**，于是国内域名整片落 default → Final
```

⚠️ **认知陷阱：`no_resolve` 不是"纯安全加固"，它是"用解析换分流"的开关。** 补它之前必须先确认"国内域名的直连已由域名类规则承担"。

⚠️ **第二个陷阱：规则集的名字骗人。** `ChinaMax.list` 看起来最像"中国域名表"，实际 **98.6% 是 IP**（实测 12,627 行：8251 `IP-CIDR` + 4221 `IP-CIDR6` + 65 `USER-AGENT` + 12 `PROCESS-NAME` + 1 `IP-ASN`，域名只有 **51 `DOMAIN-SUFFIX` + 13 `DOMAIN-KEYWORD`**）。该仓库自己的 `ChinaMax/README.md` 明写：

> `ChinaMax.list`，请使用 RULE-SET。
> **`ChinaMax.list`、`ChinaMax_Domain.list` 共同使用。**
> `ChinaMax_All.list` / `ChinaMax_All_No_Resolve.list` **单独使用**。

所以"用了 ChinaMax 却不生效"非常正常 —— **必须下载 + 数域名条目**，别按名字推断（同坑 4）。判据只有一条：**`policy=DIRECT` 的规则集里域名条目数是多少**。≈0 就等于没有直连兜底。

**修法（v8 实测最简单）**：把 URL 换成同目录的 `ChinaMax_All_No_Resolve.list`（3.42 MB）：

| 判据 | 实测结果 |
|---|---|
| 域名覆盖 | 111,332 条（111051 后缀 + 268 精确 + 13 关键词） |
| 旧覆盖是否丢失 | 旧文件那 64 条**全被包含**，差集 = 0 |
| IP 覆盖是否变化 | 12,472 条 IP **去掉 `,no-resolve` 后逐条相同**（diff 为空） |
| 会不会重新触发解析 | 12,473 条 IP **全部带 `,no-resolve`** ⇒ 不会（别用标准版 `ChinaMax_All.list`，它的 IP 条目**不带**） |
| 效果 | 15/15 国内探针 `DIRECT`；境外探针仍命中各自的 Google/GitHub/ChatGPT 组，无过宽误判 |

⇒ **凡是要"用 IP 规则判归属"的配置，都必须有一份域名类国内规则集兜底。这一步和补 `no_resolve` 是同一次改动，不能分两次做。**

**配套新增脚本 `scripts/audit_routing_coverage.py`（清单 17）**：吃 profile，先统计每个启用的 `rule_set` 的域名/IP 构成，再拿一批探针域名按 rules 顺序走一遍，输出"命中规则 + 策略"。内置 15 个**不以 `.cn` 结尾**的国内探针（专门暴露"`.cn` 兜底掩盖了国内域名无覆盖"这种假象）+ 7 个境外探针（查是否被误判直连）。**动过 `no_resolve` 或换过规则集，必须复跑。** v7 实测 `7/15 落 Final`（完整复现用户现象），v8 `15/15 DIRECT`。

**坑 18（v10 的教训）：不要把节点域名写进 DNS 分流规则 —— 它既没用，又让配置"看起来需要随订阅维护"。**

用户的原话很准：「还要把节点的域名写在配置里配置对应的 dns 设置，过于复杂了 —— 这意味着我换了订阅，防 DNS 泄露就失效了」。核查后要说得更严厉一点：**那几条规则自 v7 起就是死代码。** 两条结构性事实（官方 dns 文档逐字支持）：

1. **代理 DNS 不走 `forward`。** 官方：「配置了 `proxy_nameservers` 后，代理 DNS 会**跳过 Forward 阶段**，直接走该列表」。节点域名的解析走的正是代理 DNS ⇒ 写在 `forward` 里的节点域名规则**从未被查询过**。（v3 写它们时还没有 `proxy_nameservers`，当时确实需要；v7 补上之后它们就退役了，只是没人回头清理。）
2. **当所有 forward 规则的 `value` 相同时，顺序与域名清单都不影响结果。** 官方说"第一条命中的决定上游"，但**单值集合里不存在"命中错"这回事** —— 加一条、删一条、写错一条，结果都一样。

⇒ 正确做法不是"想办法动态生成节点域名规则"，而是**删掉它们**：`forward` 只留兜底，防泄露由**兜底组的安全性**（端点全为 IP 字面量 + 满足判据 A 或判据 B，见坑 13）承担，而不是由"记得去列举域名"承担。实测 v10：`forward` 10 条 → 2 条，`dns` 段与节点域名的耦合 4 → 0，四项审计逐项不变。

⚠️ **更要提防它带来的错觉**：这些规则让配置**看起来**很严谨（"我专门照顾了节点域名"），实际既无功能，又把"换订阅"变成了一件需要复查配置的事。**判断一条规则该不该存在，只问两个问题：删掉它结果会变吗？它是否引入了维护耦合？**

**配套新增脚本 `scripts/audit_dns_forward.py`（清单 18）**：打印 `forward` 的 value 集合与结构性冗余条数、统计"订阅耦合度"（从 `proxies[].server` 提取节点域名，查有几条 forward 规则把它们写死）、并支持 `--drill` 用**合成的"未来订阅"域名**做演练（默认 6 个故意不在任何规则集里的域名，验证"未命中的域名到底落到哪个上游"）。退出码 0/1，可直接接 CI。

## 定位"泄露到运营商"必须在网络侧实测，不能只看配置

用户说"leak test 显示 china telecom / 联通"时，**第一个动作不是改配置，是把"运营商解析器"这条路径实测出来**。配置层能证明的只有"我声明的上游不会产生这个应答"，剩下的必须落到网络层。

**⓪ 先确认链路（不做这步，后面全是白做——见坑 11）。** 问清「哪台设备 / Wi-Fi 还是蜂窝 / 谁是 DNS」。两条链路的实测对象不同：

| 链路 | 明文 :53 的下场 | 怎么测 |
|---|---|---|
| 家庭网 + 旁路由（OpenClash/mihomo） | 被透明重定向到旁路由，返回 **Fake IP `198.18.x`** | 逐个问外部解析器同一域名（见 ③） |
| **运营商蜂窝** | 被运营商重定向到**它自己的递归解析器**；或直接不通 → 掉到系统 DNS | 见 ④ 的「蜂窝变体」 |

**① 先算 IP 归属**（`curl -s https://ipinfo.io/<ip>/json`）。`org` 里带哪个运营商，就直接排除掉所有非该运营商的上游。**这一步常常一下就把范围锁到"没走到 profile 声明的上游"。**

**② 看设备自己网络的 DNS/网关**（Windows：`netsh interface ipv4 show dnsservers` / `show config`）。

**③ 测这张网有没有把 :53 全量劫持**（旁路由/OpenClash 的 DNS 重定向很常见）。逐个问外部解析器同一个域名：
```bash
for s in 223.5.5.5 119.29.29.29 1.1.1.1 8.8.8.8 <可疑IP> 192.168.2.1; do nslookup www.qq.com "$s"; done
```
若**所有**外部解析器都返回同一个 `198.18.x.x`（mihomo/Clash 默认 Fake IP 段），说明明文 :53 被旁路由吃掉了。
**关键副作用：Egern 的 bootstrap 也就此失效**（拿回的是一张 Fake IP，不是可用应答），而官方规定 bootstrap 失败就**自动使用系统 DNS** → 运营商。

**④ 用 `whoami.akamai.net` 直接问出某条路径的真实递归方**（Akamai 会回显"它看到的解析器出口 IP"）：
```bash
nslookup -type=A whoami.akamai.net 192.168.2.1      # 真实出口：如 219.128.79.150（中国电信广州）
nslookup -type=A whoami.akamai.net 192.168.2.168    # 若返回 198.18.x 说明被 fake-ip 吃掉，看不到真实出口
```
把回显 IP 和用户报的 IP 对比（同运营商/同段 = 同一条路径），**结论就从"怀疑"变成"实锤"**。

**④-蜂窝变体（本次真正用上的，比 ③④ 更通用）**：手机在运营商蜂窝上时，你没法从电脑去探测它那条链路，所以**只能"改一行、复测"**。最有效的一个实验是**把 `bootstrap` 换成一个可辨识的国内公共 DNS**（如 `180.76.76.76` 百度），复测 leak test：

| 结果 | 结论 |
|---|---|
| 归属变成 **Baidu/百度** | bootstrap 在应答且可用 ⇒ 原来的"运营商"来自 **bootstrap 全失败 → 系统 DNS** |
| **仍是 China Telecom** | 明文 :53 被运营商**透明重定向**（或那次解析根本没走 bootstrap）⇒ 去查系统级加密 DNS（`hijack_dns` 只劫持 UDP:53，拦不住配置描述文件里的 DoH/DoT） |

**④-蜂窝变体-2**：让用户核对 **设置 → 通用 → VPN与设备管理 → 配置描述文件** 里有没有 DNS/DoH/DoT 描述文件（运营商推的、公司 MDM 推的、1.1.1.1 App 装的）。**存在即绕过 UDP:53**，此时 Egern 无辜。这是"改了半天配置却发现不是配置问题"的高频原因。

**⑤ 交叉验证测试环境**：Egern 只跑在 Apple 设备上。若 leak test 是在 Windows/安卓上跑的，结果必然是局域网 DNS 的，与 profile 无关 —— 这种情况先问清楚，别改配置。同理，让用户提供 **Egern 自己的 DNS 日志**（它详细记录 DNS 流量）：哪条规则、哪个上游应答的，是唯一能直接证伪/证实的一条证据。

**⑥ 能治本的路由器侧动作**：把主路由 WAN/LAN 的 DNS 从"自动获取（= 运营商）"改成 `223.5.5.5`/`119.29.29.29`。这样即使将来任何客户端回退到 `system`，落点也不再是运营商。

⚠️ **`vif_only` 语义官方只有一句"仅虚拟网接口模式，默认 false"，无法确认细节。** 用户配置里若出现**非默认值**（`true`），只能当作 A/B 候选单独排除，**不要凭猜测替用户改**（常见于把机场模板当基线改的场景）。

## 规则集到底有多重？（2026-09-19 实测，配 `scripts/weigh_ruleset.py`）

用户问「3.42 MB 的规则集是不是负担太重 / 别的软件扛得住吗」时，**先纠正两个前提再谈数字**：

1. **rule-set 不是 profile 的一部分**。profile 本体 ~34 KB，规则表是远程文件，只在启动/更新时下载一次并缓存，**不参与每次连接**。"配置太大"这个说法本身不成立。
2. **大表不是用来治 DNS 泄露的**。治泄露是 `no_resolve` + 换掉带裸 IP 的规则集（坑 15/16）；大表（`ChinaMax_All_No_Resolve`）解决的是**分流**（坑 17）。两者不是一笔交易，别把成本记在泄露头上。

### 实测（原生内核 mihomo v1.19.31 / Go，windows-amd64，稳态 RSS 中位数，3 次）

| 加载内容 | 条目 | 文件 | 稳态 RSS | 增量 |
|---|---|---|---|---|
| 空配置基线 | — | — | 29.2 MB | — |
| `ChinaMax_All_No_Resolve` | 111,332 域名 + 12,472 IP | 3.42 MB | 51.8 MB | **+22.6 MB** |
| 同上、删掉 IP 条目 | 111,409 域名 | 2.97 MB | 47.7 MB | +18.5 MB |
| `adrules_surge_domainset`（Cats-Team 广告表） | 199,781 | 4.36 MB | 53.8 MB | +24.7 MB |

- ⭐ **可复用判据：原生实现每个域名条目 ≈ 130–175 B ⇒ 内存 ≈ `条目数 × 0.15 KB`。**（Python dict 实现实测 ~290 B/条，约为原生 2 倍。）
- ⚠️ **别用"感觉"估**：本次先估"原生大概几 MB"，实测 +22.6 MB —— **差 5 倍**。要真数字就得起一个内核量（Windows 上可直接下载官方 release，用 `rule-providers: {type: file, behavior: classical, format: text}` 指向本地 `.list`，读进程 RSS）。
- **加载时间无差别**：空配置就绪 356 ms vs 加载 3.42 MB 就绪 355 ms。
- ⭐ **匹配成本与表规模基本无关**：单次查询 0.36–0.69 µs；表从 1,000 条涨到 111,332 条（111 倍），查询只从 0.36 µs → 0.69 µs（不到 2 倍，O(域名标签数)）。**所以大表不会拖慢任何连接，唯一代价是常驻内存。**

### 大表几乎不能瘦身（别再花时间找"精简版"）

| 检查 | 实测 |
|---|---|
| 去重 | 111,319 → 111,319，**零重复** |
| 被更短父后缀覆盖的冗余 | **只有 4–5 条（0.004%）** |
| 标签深度分布 | 两级 110,754 条、三级 396、四级以上 119 ⇒ **99.5% 已是最小可用粒度**，没有归并空间 |
| 表内 IP 段 vs `geoip:CN` | 12,472 条中 7,622 条（61.1%）两端都在 CN；IPv4 面积 93.4% 落在 CN 内 ⇒ **那 12,472 条 IP 对本配置冗余**，但只值 4.1 MB / 13%，删了要自建托管，不划算 |

### 换小表要按「覆盖率」判，绝不能按体积判

| 判据 | `ChinaMax_All_No_Resolve`（111k） | `ChinaDomain.list`（ACL4SSR，586 条 / 17 KB） |
|---|---|---|
| 从大表随机抽 5,000 条长尾域名 | 100% | **0.4%** |
| 26 个高频国内站点 | 25/26 | 21/26（漏 `deepseek.com` / `kimi.com` / `volces.com` / `didi.com`） |

⇒ **覆盖是双峰的**：主流站点几百条就够，其余 99.5% 是长尾国内站。用小表 = 你随机撞到的国内小站（尤其视频/CDN 边缘）会被塞进境外代理。

```bash
"<venv>/Scripts/python.exe" scripts/weigh_ruleset.py <大表> --sub <小表> --probe www.jd.com --probe api.deepseek.com
```

**结论模板**：内存代价 20 MB 级（iPhone 上 0.5%，无感；RAM < 256 MB 的路由器要留意，叠加广告表后是 +45 MB 量级）；换来的是国内域名直连。**不值得为省这 20 MB 牺牲分流**；真正的大头往往是广告表（本项目里那份 199,781 条 / +24.7 MB 比 ChinaMax 还大，且更可控）。

## 改配置的安全姿势

Egern profile 常含**超长单行**（`mitm.ca_p12` 的 base64 CA 证书，可达数千字符）。**不要用 YAML dump 重写整个文件**（会丢注释、改格式）。正确做法：

1. 按行读入（`raw.split('\n')`）
2. 用「内容定位 + 断言唯一性」的方式插行/替换行
3. 额外写回，逐字节对比关键字段（如 `ca_p12` 完全一致）
4. 用 `yaml.safe_load` 验证新旧两份都能解析

⭐ **替换锚点必须换行锚定**：`src.index('dns:\n')` 会命中 `hijack_dns:\n` 里的子串，静默吃掉中间十几行（实测踩过）。用 `src.index('\ndns:\n') + 1`，并且改完**逐字段比对未触碰的部分**（本项目用它抓到了那次误删）。

定位改动点的核心是 `find_one(pred, what)` —— 对每处改动断言「全文恰好命中 1 行」，命中 0 或 >1 行就中止。

### 删除顶层键（实测：v9 删 `mitm` 段）

用户说「HTTPS 解密暂时不用了 / 把 mitm 删掉」时，**先查依赖再删**：

1. ⭐ **有没有规则依赖解密？** 只有 **`url_regex` / `header` / `user_agent` / `process_name`** 这四类需要 MITM 解密才能匹配；`domain*` / `ip_cidr` / `rule_set` / `geoip` 在 TLS 握手前就能判定。查法：
   `sed -n '<rules 起始行>,$p' profile.yaml | grep -c 'url_regex\|header\|user_agent\|process_name'`
   —— 零命中才可安全删（本项目实测零命中，零能力损失）。
2. **删除范围不能按行数猜**：先定位 `^mitm:$`，再断言紧随的缩进行**恰好**是 `  ca_p12:` + `  ca_passphrase:` 两行，再断言第 4 行不是缩进（否则段内还有别的子键，按行数删会吃错）。`ca_p12` 是**单行 3674 字符**的超长行，只有一行，别当成多行 base64。
3. **断言清单（七项）**：被删字段名与 base64 主体零残留 → 其余行逐条未变 → 顶层键数 = 原数 −1 且**差集恰好是 `{mitm}`** → 其余顶层键的值逐个相同 → `dns` / `rules` / `proxies` / `policy_groups` 解析后逐项相等 → YAML 可解析 → UTF-8 无 BOM / LF。
4. **原位留一行中性注释**（**不含** `mitm` / `ca_p12` 等字样，如「此处原为 HTTPS 解密（个人证书）配置段，2026-09-19 按需删除；需要时从 vN 取回」）—— 便于日后恢复，又不会干扰敏感串扫描。
5. **告知用户**：设备上已装的 CA 证书**不必删**（配置里不再解密，它不会被使用；真要清理去「设置 → 通用 → VPN与设备管理 → 配置描述文件」，但这与 DNS 泄露/分流无关）；**回滚 = 用上一版覆盖**，所以上一版必须保留。
6. 删 `mitm` 后三项审计应**与上一版逐字相同**（DNS 面 / 规则集 / 分流）—— 不同就是误删，回去查第 2 步的断言。

## 核对器

```bash
"<venv>/Scripts/python.exe" scripts/check_egern_dns.py profile.yaml [more.yaml ...]
"<venv>/Scripts/python.exe" scripts/probe_dns_endpoints.py profile.yaml   # ★ 端点逐个实测（含证书覆盖 IP）
"<venv>/Scripts/python.exe" scripts/audit_ruleset_noresolve.py profile.yaml  # ★★ 规则集 IP 条目 no-resolve 审计（清单 16）
"<venv>/Scripts/python.exe" scripts/audit_ruleset_noresolve.py --url <ruleset-url>
"<venv>/Scripts/python.exe" scripts/audit_routing_coverage.py profile.yaml   # ★★ 分流覆盖审计（清单 17，域名→命中规则→策略）
"<venv>/Scripts/python.exe" scripts/audit_dns_forward.py profile.yaml         # ★ forward 单值性/订阅耦合审计（清单 18）
"<venv>/Scripts/python.exe" scripts/audit_dns_forward.py profile.yaml --drill # ↑ --drill 可选：加合成"未来订阅"域名多演练一遍
"<venv>/Scripts/python.exe" scripts/probe_doh.py                    # 只测 DoH 线格式
"<venv>/Scripts/python.exe" scripts/profile_ruleset.py some.list    # 规则集类型分布
"<venv>/Scripts/python.exe" scripts/weigh_ruleset.py some.list [--sub small.list] [--probe d]  # ★ 规则集"重量"：构成/冗余/深度/加载与匹配耗时/覆盖对比

bash scripts/../tests/run.sh                                       # ★★ 回归测试：5 fixture × 2 脚本 = 10 断言，退出码非 0 即失败
```

⚠️ **运行目录要求**：`check_egern_dns.py` 与 `audit_dns_forward.py` 会 import 同目录的
`_egern_common.py`（共享工具）。**这三个文件必须在一起**，否则报 `ModuleNotFoundError`。
`_egern_common.py` 收编了 `DOMESTIC_RESOLVER_IPS` / `hostpart` / `ip_literal` —— 从结构上消灭了
"同一判据两份拷贝、改一处漏另一处"的隐患（详见"审计演进"节 v10.2）。

⚠️ **`hostpart()` 剥 scheme 必须用大小写不敏感的通用正则，不能用白名单。**
白名单（`("https://", "tls://", ...)`）会让 scheme 的**拼法**参与审计结论：端点写成
`HTTPS://223.5.5.5/dns-query` 时白名单失配，`HTTPS` 被当成主机名，端点从「IP 字面量」
误判成「待解析域名」，同一份配置读数从 0 high 翻成 9 high。`tests/scheme_case.yaml` 是这条的守卫。

`check_egern_dns.py` 输出 `OK / LOW / HIGH` 三类，有 `HIGH` 时退出码 1，覆盖上面清单 1–15 项。
清单 16 由 `audit_ruleset_noresolve.py` 单独覆盖（要下载**全部被引用的**规则集，几十秒，不塞进同一个脚本；有 `.ruleset-cache/` 本地缓存，加 `--offline` 可只读缓存）。实测判别力：**原始配置 → HIGH（`Apple_All.list` 13 条），v7 → OK（20 个全过）**。⚠️ 数量会随配置变化：v10 是 **19 个**（少的那 1 个 = `forward` 不再引用 `ChinaDomain.list`）；2026-09-21 新增 `white-guard` / `ads` 两条后为 **21 个** —— 报数变化时先确认是"少引用"而不是"漏扫"。

v3 起新增：① **节点域名覆盖检查**（从 `proxies[].server` 自动提取域名，逐个查 `forward` 是否有非兜底规则接住）；② **兜底语义识别**（`domain_wildcard:'*'` 与 `domain_regex:'.'` 都认，不再依赖"必须在最后一条"）。
⚠️ **①在 v7/v10 后已反转**：`proxy_nameservers` 一旦显式设置，代理 DNS 就跳过 `forward` ⇒ 该检查的判据改为"`proxy_nameservers` 是否显式设置且端点全为 IP 字面量"，而"forward 里有没有为节点域名单列规则"变成**要主动避免的事**（坑 18）。
v4 起新增：③ ⭐ **「profile 自身必需解析」覆盖检查** —— 把两个 latency test URL 与 `policy_groups[].icon` 的域名按 `domain`/`domain_suffix`/`domain_keyword`/`domain_wildcard`/`domain_regex` 语义去匹配 `forward`，看有没有"兜底之前"的规则接住。**兜底组不安全时**：延迟测试端点漏接 = HIGH（每轮测速都触发，持续泄露）；图标漏接 = LOW。
⚠️ **③在 v6 后降级**：兜底一旦换成直连可达的国内组，这些名字落到兜底就不再构成泄露（现为 LOW）—— 它们只在"兜底不安全"的配置里才是事故（坑 18）。
v5 起新增：④ **明文回退面检查** —— `bootstrap` 含 `system` → HIGH（主动接进运营商 DNS）；`bootstrap` 只有 1 个 → LOW；`forward` 的 `value` 出现 `system` → HIGH、出现 `bootstrap` → LOW。
v6 起（⭐ 本版最重要的收紧）：⑤ **兜底组「直连可达」判定（`group_reach()`）** —— 判据从"端点写 IP + 有显式路由"改为"**端点写 IP + 至少一个在 `rules` 里判给 `DIRECT`**"。只判给 Proxy 的组报 HIGH：**兜底组依赖代理**（坑 13）。这条判据是本次事故的直接产物 —— v5 在旧判据下 `0 high`，用户实测却出 `upstream: bootstrap`。同时**撤回 v2 的一条错判**："兜底指向国内组 = HIGH"是错的 —— 致命的是**明文**，"答案可能被污染"是另一个量级的问题；现在兜底 = 直连可达的国内组判 **OK + 一条 LOW 说明**。

v7 起（本条不是脚本新增检查，而是**判据层面的补完**）：⑥ **清单 16 的规则集审计独立成脚本** —— 因为"强制解析"这类缺陷**完全不在 profile 文本里**，`check_egern_dns.py` 再怎么写也看不见。**这是本项目第二次栽在"审计器只能验证自己编码进去的假设"（坑 3、坑 9）上**：v6 在 `check_egern_dns.py` 下已是 `0 high`，用户实测仍有泄露。结论固化下来：**任何一次"审计通过但用户仍报泄露"，都必须假设"存在审计器看不见的维度"，并把该维度补成一个可复跑的脚本。**

v8 起：⑦ **分流覆盖审计独立成脚本（清单 17）** —— 第三次栽在同一个道理上：v7 在 `check_egern_dns.py` / `audit_ruleset_noresolve.py` 下**双双通过**（`0 high` + `OK 20/20`），用户实测却是"国内域名全落 final"。原因是两个脚本一个只看 DNS 面、一个只看"会不会强制解析"，**都看不见路由本身对不对**。⇒ 新增 `audit_routing_coverage.py`。**结论再收紧一层：DNS 审计全绿 ≠ 配置可用；只要动过 `no_resolve` 或换过任何规则集，分流必须单独复测（可用域名走一遍规则）。**

v10 起：⑧ **forward 单值性 / 订阅耦合审计独立成脚本（清单 18）** —— 这一次不是"泄露或分流坏了"，而是**可维护性**：用户指出"节点域名写在配置里，换订阅就失效"。核查发现那几条规则**自 v7 起已是死代码**（`proxy_nameservers` 让代理 DNS 跳过 forward；且全部 forward 规则 value 相同 ⇒ 顺序与域名清单都不影响结果）。⇒ `forward` 塌缩为 2 条兜底，新增 `audit_dns_forward.py`。**教训：审计器要同时盯"安全"和"耦合面" —— 一条没功能、却让人以为"配置依赖订阅"的规则，本身就是缺陷。**

v10.2 起（2026-09-20，二次核查报告触发）：⑩ **「靠注释提醒同步两份拷贝」被证明不可靠 —— 改成共享模块 + fixture 回归。**
背景：上一条 v10.1 我在两个脚本里各写了一份同样的判据，并加了注释"改一处要同步另一处"。**注释没能阻止我漏改**：
- 判据**本体**同步了，但**喂给判据的 helper 没同步** —— `audit_dns_forward.py` 自己的 `ep_ip()`
  用 `rsplit(":", 1)[0]` 切端口，把 IPv6 的 `[2400:3200::1]` 截成 `'[2400:3200:'`；
  而 `check_egern_dns.py` 的 `hostpart()` 有方括号专处理、返回正确值。
  ⇒ **同一份 IPv6 profile，两个脚本给出相反结论**（0 high/exit 0 vs 需确认/exit 1）——
  比"没有脚本"更糟，因为用户不知道信谁。
- 同一时期还暴露：`audit_dns_forward.py` **不带 `--drill` 直接崩**（`UnboundLocalError: fails`）——
  `fails = []` 只写在 `if probes:` 块里，而 README / docs / skill 里给的命令**正是不带参数的形态**。
  这个崩溃**旧版就有**，但因为它只被手工喂给 `check_egern_dns.py`，一直没被发现。

⇒ 固化四条：
1. ⭐⭐ **共用逻辑必须收编成一个模块，不靠注释同步。** 现为 `scripts/_egern_common.py`，
   收 `DOMESTIC_RESOLVER_IPS` / `hostpart` / `ip_literal`；两个脚本都 import 它。
   **判据可以有两处调用点，但实现只能有一处。**
2. ⭐⭐ **fixture 必须喂给"所有"脚本，而不是常跑的那一个。** 新增 `scripts/../tests/run.sh`
   （5 fixture × 2 脚本 = 10 断言）+ CI `.github/workflows/audit-regression.yml`。
   经验：**"只差一点就能抓到"的 bug，恰恰是因为守卫只覆盖了一半**。加守卫时要问："这条断言有没有在
   **每一个**消费方上跑过？"
3. ⭐ **文档里给的命令必须逐条照着执行一遍。** 这次崩溃的命令就印在 README / docs/04 / skill/README 里。
   文档里的命令是**接口契约**，改脚本后要回填验证（`--drill` 这类可选参数尤其要显式标注"可选"）。
4. ⭐ **`_egern_common.py` 必须与调用它的脚本同目录。** 用户如果只拷走单个脚本会报 `ModuleNotFoundError`；
   分发/打包时三个文件（`_egern_common.py` + 两个审计脚本）要一起走。

v10.3 起（2026-09-20，三次核查报告触发）：⑪ **"收编共用逻辑"这个动作本身会引入回归 —— 收编时把实现悄悄换掉，比两份拷贝更难发现。**
本次事故：把 `hostpart` 收进 `_egern_common.py` 时，剥 scheme 从「通用剥离 `if "://" in s: split("://",1)[1]`」
退化成「大小写敏感白名单 `("https://", "tls://", ...)`」。于是端点写成 `HTTPS://223.5.5.5/dns-query`
时白名单失配，`HTTPS` 被当成主机名 ⇒ 端点从 IP 字面量误判成待解析域名 ⇒ 同一份配置读数从
**0 high 翻成 9 high**。发布模板端点全是小写所以没暴露；换任何一个大写 scheme 的配置就翻。
⇒ 固化三条：
1. ⭐⭐ **重构"等价改写"必须逐输入对拍，不能只看测试是否还绿。** 测试绿只说明**已覆盖的输入**没变，
   说明不了"改写等价"。写一个把新旧实现按同一批输入逐一对比的脚本（这次是 16 个输入），
   差异为 0 才叫等价。
2. ⭐⭐ **解析器里出现"枚举白名单"就是气味。** `scheme` / 大小写 / 编码这类**输入的表层拼法**，
   不该有能力改变判定结果。凡是要枚举，先问"漏一个会怎样"——这里漏一个就从 0 high 变 9 high。
3. ⭐ **"读到的数字"和"声称的结论"要分开核。** 本轮还发现 README/commit 声称"已加 CI"而
   `.github/workflows/` 从未上传：PAT 缺 `workflow` scope 时 GitHub 对含 workflow 的 tree 创建
   返回 **404**，发布脚本据此静默摘掉 CI 文件继续推。**发布后要用 `git ls-files` 核对交付物，
   而不是相信发布脚本的 commit message。**

v10.1 起（2026-09-20，外部审查报告触发）：⑨ **判据本身会随配置演进失效 —— 改配置后必须重跑判据，且改判据要用"双向回归"守住收紧面。**
本次事故：v10 删掉了 15 条 DNS 端点路由规则（依据是 `upstreams` 全是 IP 字面量 ⇒ 不需要路由），**我验证了配置侧、没验证脚本侧** —— 而 `group_reach` 的判据有一半是「至少一个端点判给 `DIRECT`」。删掉那些规则 ⇒ 这半句永远不成立 ⇒ 插件把**自有模板**误判 `3 high`、退出码 1。报告结论准确。
⇒ 固化三条：
1. ⭐ **凡是"判据依赖的对象会被别的改动删掉"的检查，改动后必须重跑。** 判据是**双向**的（A 且 B），只验证其中一端（A）不等于判据成立 —— 这跟坑 3/9/坑 16/17/18 是同一个母题的第 N 次复发：**审计器只能验证你编码进去的假设，而假设会腐烂。**
2. ⭐ **放宽判据必须同时保留收紧面。** 正解是**二选一**（旧判据「≥1 端点 DIRECT」**或**新判据「≥1 端点是国内知名解析器 IP」），**不是**「端点全为 IP 即充分」（那会回退到坑 13 的 v5 事故：全境外 IP 组被误判安全）。改完用三份合成 profile 做**双向回归**：全境外 IP → 必须 HIGH；主机名端点 → 必须 HIGH；显式 `ip_cidr→DIRECT` → 必须通过。
3. ⭐ **同一判据有第二份实现时，注释里必须互指。** `audit_dns_forward.py` 的 `endpoint_route`/`direct_ips` 与 `check_egern_dns.py` 的 `group_reach` 是同一判据的两个副本 —— 只改一处就会让两个脚本给出**相反**结论（比没有脚本更糟）。改判据 = 两处一起改 + 两个脚本一起复跑。

**配套的发布脚本卫生**：dry-run 一定要**逐条看文件清单** —— 本轮 dry-run 才发现会把 `__pycache__/*.pyc` 推上去（`os.walk` 型发布脚本的常客），必须靠剪枝 + 后缀过滤拦掉；远端历史残留（改名前的旧文件、误提交的字节码）要用 `sha: None` 的 tree 条目删除。另：`probe_doh.py` 与 `probe_dns_endpoints.py` 的**证书校验开关必须一致**（单个脚本偷偷关校验 ⇒ 测不出"证书不覆盖该 IP"这类真问题；需要关时必须显式 `--no-verify` 且打印警示）。

实测基准（同一份机场模板；v1→v7 三天内迭代。数字均为**当前判据**下、同一天复跑所得）：

| 版本 | `check_egern_dns.py` | `audit_ruleset_noresolve.py` | 关键问题 |
|---|---|---|---|
| 原始配置 | **5 high** / 13 low / 3 ok | **HIGH**（`Apple_All.list` 13 条） | `Foreign-DNS` 两个主机名端点；兜底组不安全；两个 latency 域名落兜底；规则集强制解析 |
| v1（我第一版） | 3 high / 8 low / 12 ok | HIGH | 同上；另私自加了 `proxy_nameservers`，把泄露从"偶发"变成"确定" |
| v3 | 3 high / 3 low / 16 ok | HIGH | 兜底组依赖代理 + 两个 latency 域名仍落兜底 |
| v4 | 2 high / 2 low / 19 ok | HIGH | 兜底组依赖代理 |
| v5 | **1 high** / 2 low / 35 ok | HIGH | **兜底组依赖代理** |
| v6 | 0 high / 2 low / 37 ok | **HIGH** ← 假安心 | 兜底已修，但 **`Apple_All.list` 的强制解析还在**；用户实测仍报 `upstream: bootstrap` |
| **v7** | **0 high** / 3 low / 43 ok | **OK（20/20）** | — 但 **分流坏了**：国内域名 7/15 落 Final（该维度当时还没有脚本，见 v8） |
| **v8** | **0 high** / 3 low / 43 ok | **OK（20/20）** | — （`ChinaMax.list` → `ChinaMax_All_No_Resolve.list`；分流 15/15 DIRECT、境外无误判） |
| **v9** | **0 high** / 3 low / 43 ok | **OK（20/20）** | — （删顶层 `mitm` 段；与 v8 **三项审计逐字相同**，纯删除不动 DNS/分流） |
| **v10** | **0 high** / 3 low / 43 ok | **OK（19/19）** | — （`forward` 10 条 → 2 条兜底，删掉 8 条结构性冗余；`dns` 与节点域名耦合 4 → 0。规则集数 20 → 19 是因为不再引用 `ChinaDomain.list`。四项审计中前三项与 v9 完全一致，`audit_dns_forward.py` 新增通过） |

⚠️ v1/v2/v3/v5 的 `0 high` **全是假安心**：v1/v2 靠加 `proxy_nameservers` 把 HIGH 压下去（代价是把泄露从偶发变成确定）；v3 是审计盲区（脚本没看 latency 域名）；**v5 是判据不足（"路由确定"被当成了"不依赖代理"）**；**v6 是审计维度缺失（只看 profile、不看它引用的规则集）**。**审计通过 ≠ 没有泄露 —— 必须回到机制层推导 + 按链路做实测（见"定位泄露到运营商"一节）。**

### 加固结束的验收标准（七条同时满足才算完）

1. `upstreams` 与 `proxy_nameservers` 里**没有任何主机名端点**（全部 IP 字面量，或已钉 `hosts`）—— 消灭 bootstrap 用途①。
2. `forward` 有兜底，**且兜底组直连可达**（端点全为 IP 字面量 + **至少一个在 `rules` 里判给 `DIRECT`，或至少一个是已知国内解析器 IP** —— 两条二选一，见坑 13 末尾）—— 消灭 bootstrap 用途②，且不依赖"代理已就绪"。
3. 所有 IP 类规则（`geoip` / `ip_cidr` / `ip_cidr6` / `asn`）**都带 `no_resolve`** —— 否则每个走到它的域名都会被强制本地预解析一次（坑 15）。
4. ⭐ **所有被启用的 `rule_set` / `proxy_rule_set`，其规则集文件里的 IP 类条目都带 `no-resolve`** —— 用 `audit_ruleset_noresolve.py` 跑，必须 OK（坑 16）。
5. `bootstrap` 显式列 2 个以上国内公共 DNS 的 IP，**且不含 `system`** —— 把"全失败 → 系统 DNS"压到最低。
   ⚠️ 前 4 条是"让它不被用到"；第 5 条只是把最坏分支的概率压小。**bootstrap 是明文 UDP:53，在运营商线路上无论指向哪个 IP 都可能被接管 —— 它唯一安全的形态是"永远不被触发"。**
6. ⭐⭐ **分流仍然正确：国内域名仍判给 DIRECT。** 用 `audit_routing_coverage.py` 跑，15 个国内探针必须全 `DIRECT`。
   **这一条是第 3 条的代价，必须成对交付** —— 给 IP 规则补 `no_resolve` 会同时关掉"靠解析判 IP 归属"那条直连路径（坑 17）。所以补 `no_resolve` 的同一时刻，必须确认 `default` 之前有一份**含大量域名条目**的国内规则集（如 `ChinaMax_All_No_Resolve.list`）。**"DNS 审计全绿"不等于"配置可用"**：v7 时两个审计脚本双双通过，分流却整片是坏的。
7. ⭐ **`dns.forward` 与订阅零耦合：`value` 单值，且没有任何一条规则把节点域名写死。** 用 `audit_dns_forward.py profile.yaml --drill` 跑，必须「零耦合 + 通过」。
   **防泄露必须由"兜底组的安全性"承担，而不是由"记得去列举域名"承担** —— 后者会让换订阅变成一件需要复查配置的事，而它连功能都没有（坑 18）。

## 公开模板仓库（本项目的对外交付物）

自用配置已脱敏发布为公开模板 + 文档 + 本 skill：

**https://github.com/RiverFlowsInUUU/egern-anti-dns-leak**

```
README.md                                   # 三条铁律 + 一图看懂回退链
profiles/v2.1.yaml                          # 脱敏模板 · 推荐版（无节点、无订阅、无证书）
profiles/v2.1.min.yaml                      # 同上，纯配置版（去注释）
profiles/v2.yaml / v2.min.yaml              # 保留原样（比 v2.1 多 52 行「值等于默认值」的冗余行）
profiles/v1.yaml / v1.min.yaml              # 旧版，保留不删（dns 段较冗长，功能等价）
profiles/v0.yaml / v0.min.yaml              # 极简裁剪版（4 组 / 9 条规则，Final 隐藏、AD 只留 REJECT）
docs/01-DNS是怎么工作的.md                   # 递归解析 / 加密 DNS / Fake IP / Egern 双轨模型
docs/02-DNS为什么会泄露.md                   # 5 个真实案例（每个：现象→机制→修法）
docs/03-加固清单-18项.md                     # 清单 + no_resolve 三层级 + 验收 6 条
docs/04-模板逐段讲解.md                      # 逐段讲模板，含"必须替换的 4 处"
docs/05-分流与no_resolve必须成对交付.md       # v7→v8 事故复盘
docs/06-实测数据与版本谱系.md                 # 端点实测表 / 污染实测表 / v1→v8 谱系
skill/                                       # 本 skill（含全部脚本）
```

**要更新模板时**：不要手改仓库里的 yaml。本地有 `outputs/_build_public_template.py`，
它从 v8 自用版做**带断言的行级替换**并跑 38 个敏感串的零残留自检 —— 这是唯一正确的入口。
发布用 `outputs/_publish_to_github.py`（Git Data API 单次提交；空仓库需先落初始化提交，
否则 `POST /git/blobs` 报 `409 Git Repository is empty`）。方法论见 skill `github-publish-sanitized-repo`。

⚠️ **发布 CI 文件需要 PAT 具备 `workflow` scope。** 只有 `public_repo` 时，GitHub 对
「包含 `.github/workflows/` 的 tree 创建」返回 **404**（不是 403 —— 它故意不暴露存在性）。
`_publish_to_github.py` 会把 workflow 文件摘掉、照常推送其余文件 —— 于是 README 写着
「CI 见 …」而仓库里根本没有 CI（三次核查报告 P1 的真实成因）。
**发布后必须核对交付物，而不是相信脚本的 commit message**：
`git ls-files | grep '^\.github/'` 应至少列出 1 个文件。

**脱敏清单（这五类必须洗）**：节点 server/凭据/sni/reality 公钥 → 占位；
机场订阅 URL（含 token）→ 占位；`mitm.ca_p12` + `ca_passphrase`（个人 CA 私钥）→ **注释掉**；
机场组名/节点名 → `Airport-A` / `Node-1`；`dns.forward` 里的**节点域名** → `example-node.com`。

## 官方文档入口

- DNS 机制：`https://egernapp.com/docs/configuration/dns`（**核心页**，两条路径 + bootstrap + proxy_nameservers + block_ips + hosts 全在此）
- 规则字段：`https://egernapp.com/docs/configuration/rules`（`no_resolve` 适用范围、逻辑规则 `and`/`or`/`not`、rule_set 内部字段）
- 顶层字段全表：`https://egernapp.com/docs/configuration/example`（**注意键名与 DNS 页不一致**）
- 社区参考实现（中国网络环境的最佳实践，DNS 段写法值得对照）：`https://repcz.github.io/egern`
- sitemap（找页面用）：`https://doc.egernapp.com/sitemap.xml`

⚠️ `https://egernapp.com/zh-CN/docs` 和 `/docs/configuration/general` 是 **404**；顶层字段只能从 `configuration/example` 页获取。DNS 页有中文版 `/zh-CN/docs/configuration/dns`。
