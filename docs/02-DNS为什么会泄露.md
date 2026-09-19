# 02 · DNS 为什么会泄露

## 核心命题

> **泄露不一定来自"你选的 DNS 服务器"，而来自"你没意识到的解析"。**

一份把上游写成 `https://dns.google/dns-query`、看起来"全程加密"的配置，仍然可能每一轮测速都往运营商那里送一次明文查询。原因不是配置写错了某一行，而是**配置里有若干条你没注意到的解析路径**，它们会按回退链走到明文。

下面 5 个案例全部来自真实事故，每个都给出：**现象 → 机制 → 怎么发现 → 修法**。
（版本号 v1–v8 见 [docs/06](06-实测数据与版本谱系.md)，那是这条排查线的时间顺序。）

---

## 案例 ①  `upstreams` 里写了主机名 → bootstrap 用途①

**现象**：每一次冷启动、每一次上游组重建，都会有一次明文查询。

**机制**：官方文档明确 `bootstrap` 的用途之一是**"解析 `upstreams` 中加密 DNS 服务器的主机名"**。
所以只要你写：

```yaml
upstreams:
  Domestic-DNS:
  - https://dns.alidns.com/dns-query      # ← 这是一个「主机名」
```

软件就必须先知道 `dns.alidns.com` 的 IP，才能去连它 —— **而这次解析只能用 `bootstrap`（明文 UDP:53、直连）**。
端点上每多写一个主机名，就多一次明文查询。

**怎么发现**：搜 `upstreams` / `proxy_nameservers` 下的所有端点，肉眼检查有没有非 IP 字面量。

**修法**：

```yaml
upstreams:
  Domestic-DNS:
  - https://223.5.5.5/dns-query     # ✅ IP 字面量 ⇒ 一次解析都不产生，且零依赖
  - https://223.6.6.6/dns-query
  - https://1.12.12.12/dns-query
  - https://120.53.53.53/dns-query
  - tls://223.5.5.5
  - tls://1.12.12.12
```

> ⚠️ 换成 IP 之前**必须逐个实测端点真的可用**（`probe_dns_endpoints.py`）。
> 实测踩过的坑：`https://9.9.9.9/dns-query` 直接失败（返回 `HTTP Version Not Supported`，Quad9 在该 IP 上只提供 HTTP/3）——
> 必须写成 `tls://9.9.9.9`。另外要确认证书覆盖 IP：`tls://223.5.5.5` 的证书是 `CN=*.alidns.com`，覆盖 IP；`tls://1.12.12.12` 是 `CN=120.53.53.53`。

---

## 案例 ②  节点 `server` 是域名 → 代理 DNS 强制直连 → 回退明文

**现象**：启动阶段（规则集下载、首轮测速）必现一次明文查询。

**机制**：这是**唯一必定发生**的一次国内解析 —— 不取决于你访问什么网站，只取决于你要连哪个节点。

- 节点连不上，代理就是废的；要连节点，就必须先解析它的域名；
- 这次解析**只能在直连侧做**（代理还没通，不可能让代理去解析它自己的地址）；
- 而直连侧去问境外解析器在国内基本不通 ⇒ 回退 `bootstrap` 明文。

**怎么发现**：先统计节点形态 ——

```bash
python -c "import yaml;d=yaml.safe_load(open('Profile.yaml',encoding='utf-8'));print([(p[list(p)[0]].get('name'),p[list(p)[0]].get('server')) for p in d['proxies']])"
```

只要 `server` 里有域名，就要在 `forward` 里找对应的显式规则。

**修法**（两个方向，按推荐顺序）：

```yaml
# 方向 A（根治）：把节点 server 写成 IP 字面量 ⇒ 一次解析都不产生
proxies:
- vless:
    name: 🇺🇸 Node-1
    server: 203.0.113.10        # IP 形式，零解析

# 方向 B（收口）：在 forward 里为节点域名显式指定国内加密组
dns:
  forward:
  - domain_suffix:
      match: example-node.com   # ← 你的节点域名后缀
      value: Domestic-DNS
```

> **方向 B 的价值在于"把这次注定要发生的国内解析，变成确定的、快的、不经明文的"。**
> 它并不隐藏"你在解析节点域名"这件事 —— 真要连节点域名都不暴露，只有方向 A。

---

## 案例 ③  规则集里的裸 IP 条目 → 每个域名都被强制解析一次

**现象（最反直觉的一例）**：DNS 日志里**规则判定完全正常**（`default → Final → Proxy`），但同一时刻 `upstream` 显示 `bootstrap`。

**机制**：缺陷**不在 profile 里，而在 profile 引用的第三方 `.list` 文件里**。

- 官方规则：`no_resolve` 为 `true` 才"不触发 DNS 解析" ⇒ **不带就触发**；
- 一条启用的 `rule_set` 规则里只要有**一条**不带 `no-resolve` 的 IP 条目，**每个走到该规则的域名都会被强制本地解析一次**；
- 该次解析走的就是默认 DNS 的链 —— 一旦落到 `bootstrap`，就是明文。

**实测证据**：`blackmatrix7/ios_rule_script` 的 `Surge/Apple/Apple_All.list` 有 **13 条 `IP-CIDR` 没带 `no-resolve`**（`139.178.128.0/18` 等 Apple CDN 段）。
而这条规则**排在 `default` 之前、`policy: DIRECT`、且未禁用** ⇒ 每个没被前 40 条规则命中的域名，经过它都会被强制解析一次。

**怎么发现**：必须**把规则集下载下来数条目** ——

```bash
python skill/scripts/audit_ruleset_noresolve.py Profile.yaml
python skill/scripts/profile_ruleset.py https://.../Apple_All.list
```

**修法**：换用同源的 `No_Resolve` 变体，并**核对覆盖面无变化**（去掉 `,no-resolve` 后两份文件应逐条相同）：

```yaml
- rule_set:
    match: https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/Apple/Apple_All_No_Resolve.list
    policy: DIRECT
```

> 实测：`Apple_All.list` 与 `Apple_All_No_Resolve.list` 均为 **1616 条**，去掉 `,no-resolve` 后**逐条相同**，只有那 13 条补上了后缀 ⇒ 覆盖面零损失，对 IP 形式连接的判定也完全不受影响（IP 本就无需解析）。
> **全部 20 个远程规则集逐个下载核对后：只有 `Apple_All.list` 存在这个缺陷。** 但这恰恰说明**必须逐个查，不能抽查**。

---

## 案例 ④  `geoip` 不带 `no_resolve` → leak test 的随机子域正是这样进场的

**现象**：leak test 一跑就泄露，且**每次泄露的域名都不同**（因为测试站用的是随机子域）。

**机制**：dnsleaktest 之类的工具会构造一个**随机子域名**（例如 `abc123xyz.dnsleaktest.com`）让你去访问。
这个子域**不在任何规则集里**，于是它一路走到 `geoip: CN` 这条规则 —— 而这条规则**没带 `no_resolve`**，为了判断"这个连接是不是 CN"，软件**必须先把它解析出来**。

⇒ **测试工具"故意访问一个没人见过的域名"，正好命中了"为判定 IP 规则而强制解析"这条路径。**
这就是为什么 leak test 特别容易暴露这类问题。

**修法**：

```yaml
- geoip:
    match: CN
    policy: DIRECT
    no_resolve: true        # ✅ 不再触发解析
```

> 🚨 **但这一手有代价，而且代价很大**（见案例 ⑤ 之后的小节，以及 [docs/05](05-分流与no_resolve必须成对交付.md)）：
> `no_resolve: true` 之后，`geoip` **不再匹配域名**。如果国内域名的直连**本来**就靠这条 `geoip` 撑着，那它会**整片落到 `default` → 走代理**。

---

## 案例 ⑤  profile 自身必需解析的名字 → 持续型泄露

**现象**：什么都没访问，日志里也周期性出现解析。

**机制**：有一类名字**不是"用户要访问的网站"，而是 profile 自己运行所必需的**：

| 名字 | 谁在解析它 | 频率 |
|---|---|---|
| `cp.cloudflare.com` | `proxy_latency_test_url` 的域名 | **每轮节点测速一次**（多个策略组带 `interval`，每 10 分钟一轮） |
| `connectivitycheck.platform.hicloud.com` | `direct_latency_test_url` 的域名 | 同上 |
| `fastly.jsdelivr.net` / `raw.githubusercontent.com` | 策略组 `icon` 的域名 | 界面刷新时 |

**关键事实**：实测这几个名字在 `ChinaDomain.list` 里 **0 命中**（表里唯一两条 cloudflare 还是注释掉的）⇒ 整类落到**兜底组**。

⇒ 如果兜底组是"必须经代理才可达"的境外组，而这次解析发生在直连侧（代理 DNS 强制直连 / 无代理可用），就必然失败 → 回退 `bootstrap` 明文 → 再落 `system` = 运营商。
**而这类解析每 10 分钟就来一轮，与你访问什么网站无关 —— 所以它是持续型的。**

**修法**：在兜底规则**之前**，把这些名字显式接住：

```yaml
dns:
  forward:
  - domain:
      match: cp.cloudflare.com
      value: Domestic-DNS
  - domain:
      match: connectivitycheck.platform.hicloud.com
      value: Domestic-DNS
  - domain_suffix:
      match: jsdelivr.net
      value: Domestic-DNS
```

> **原则：必须在直连侧解析的名字，上游就得是「国内可达的加密 DNS」。**

---

## 附：兜底组挂在境外组 —— 一个"审计通过、实测泄露"的经典

上面几个案例之外，还有一个**结构性**的坑：

**兜底组的唯一判据是「直连可达」，不是「指向境外」。**

- 兜底存在的意义只有一个：让"未命中的域名"不回退 `bootstrap` 明文；
- 如果兜底挂在境外组上，就引入了一个隐式依赖 ——**"先有代理，才敢解析"**；
- 启动阶段（规则集与 geoip/asn DB 的下载、策略组首轮测速）代理尚未就绪，此时任何一次本地解析都会掉进 `bootstrap` 明文。

**正确写法（双保险，两条互不依赖）：**

```yaml
  - domain_regex:            # 官方 PCRE2 find 式，'.' 必然命中任何域名
      match: '.'
      value: Domestic-DNS
  - domain_wildcard:         # 官方示例与社区配置的主用法
      match: '*'
      value: Domestic-DNS
```

> **兜底指国内组不会让"要访问的境外网站"拿到污染答案** —— 按官方语义，走代理的域名由节点远程解析、不经过本地 `dns` 段；本地段只服务 DIRECT 域名与节点域名，而这些名字用国内加密 DNS 本来就更快更准。
> 反过来，一份"兜底挂境外组、代理没就绪时回退明文"的配置，**危险得多** —— 前者最坏是本地解析的 DIRECT 域名拿到国内答案（可接受），后者是**不可撤销地泄露给运营商**。

---

## 为什么"换个更好的 bootstrap IP"没有意义

实测记录：把 `bootstrap` 从 `223.5.5.5` / `119.29.29.29` 换成 `180.76.76.76`，**泄露的 ISP 仍然是 China Telecom**，出现的仍是 `219.128.13x.x` / `59.37.178.x` 这类电信地址段。

两个原因，任一条都足以解释：

1. **透明重定向**：发往任意外部 `:53` 的明文查询，在运营商线路上被改写目的地、交给运营商自己的解析器 —— 换 IP 不改变这件事；
2. **失败后回落 `system`**：官方文档"未配置或解析失败时，自动使用系统 DNS 服务器" —— 而蜂窝下的 `system` DNS 就是运营商下发的。

⇒ **结论：`bootstrap` 唯一安全的形态是"永远不被触发"。**
对抗它的正确做法不是"挑一个更干净的服务器"，而是把它的两个用途分别消灭掉：

| bootstrap 的用途 | 消灭方式 |
|---|---|
| ① 解析 `upstreams` 中加密 DNS 服务器的主机名 | 端点全部写成 IP 字面量（案例 ①） |
| ② 作为最终的 DNS 回退 | 让 `forward` 有一条"直连可达"的兜底（附节）；并显式写 `proxy_nameservers`，堵掉代理侧那条隐式回退分支 |

---

## 怎么从日志确认你踩的是哪一条

| 日志里看到 | 指向的案例 |
|---|---|
| `upstream: bootstrap` | 上面的某条路径被触发，具体看**同时出现的域名** |
| `default → Final → Proxy` **与** `upstream: bootstrap` 同时出现 | 案例 ③（规则集里的裸 IP 条目）或案例 ④（`geoip` 无 `no_resolve`）—— 规则判定是对的，那次解析是"为判定而额外发生的" |
| 启动阶段就出现 | 案例 ②（节点域名）或兜底挂在境外组 |
| 周期性出现、与访问无关 | 案例 ⑤（延迟测试域名） |
| 出现了没见过的随机子域 | 案例 ④ —— 那就是 leak test 的探针域名 |

⚠️ **`bootstrap` / `system` 是客户端自己的内部名称，第三方测试网站不可能"显示"它们。**
如果某个测试结果里出现了这两个词，说明它读到的是**客户端日志**而不是第三方页面 —— 这是最有价值的一类证据。

---

下一步：[docs/03 加固清单（17 项）](03-加固清单-17项.md) —— 把上面的机制变成可以逐条勾选的清单。
