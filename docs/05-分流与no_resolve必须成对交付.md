# 05 · 分流与 `no_resolve` 必须成对交付

> **这是本项目最贵的一条教训。**
> 「DNS 不泄露」和「分流正确」不是两个独立目标 —— 它们是**同一个机制的正面和反面**。
> 一份配置可以做到 DNS 审计全绿，同时国内网站全部走代理。

> **模板现状更新**：本文记录的是 v8 时期用 `ChinaMax_All_No_Resolve.list` 完成这次修复的实测与推导。
> 当前模板已把该规则集的 URL 换成 Loyalsoldier **`direct.txt`**（111,160 条**纯域名**，零 IP 条目）；
> 原理完全一致 —— 「IP 规则带 `no_resolve`」必须与「一份域名条目足够多的国内直连规则集」成对交付。
> 换用纯域名规则集后，它自身不触发解析，`no-resolve` 那一半由 `geoip: CN` 承担。

---

## 1. 机制：`no_resolve` 是"用解析换分流"的开关

官方 `rules` 文档原文：

> `no_resolve (bool)`，可选 —— 仅适用于 IP 类规则（`geoip`、`ip_cidr`、`ip_cidr6`、`asn`）。
> **设为 `true` 时仅匹配已解析的 IP 地址，不会触发 DNS 解析。**

反过来说：**不带 `no_resolve` 的 IP 类规则会触发一次解析** —— 这正是泄露源（见 [docs/02 案例 ④](02-DNS为什么会泄露.md)）。

但很多人没注意到的是这条的**另一半**：

> **`no_resolve: true` 之后，`geoip` 不再匹配域名。**

于是产生了一个隐蔽的连锁反应：

```
原始配置的国内直连机制：
    收到域名 → 强制本地解析一次 → 判出 CN IP → DIRECT
                    ▲
                    └── 这次解析就是泄露源

加上 no_resolve: true 之后：
    ✅ 不再有强制解析  → 泄露治好
    ❌ geoip 不再匹配域名 → 这条直连路径**一起消失**
                            → 国内域名整片落到 default → 走代理
```

⇒ **补 `no_resolve` 的同一时刻，必须确认 `default` 之前有一份"域名条目足够多"的国内 DIRECT 规则集。**
这就是"成对交付"的含义。

---

## 2. 事故复盘：治好泄露的那一手，把分流搞坏了

| 阶段 | 改动 | DNS 审计 | 分流 | 说明 |
|---|---|---|---|---|
| **v7** | 给 `geoip: CN` 补 `no_resolve`；换用 `Apple_All_No_Resolve.list`；显式写 `proxy_nameservers` | ✅ `check_egern_dns.py` → `0 high / 3 low / 43 ok`<br>✅ `audit_ruleset_noresolve.py` → `OK (20/20)` | ❌ **国内域名整片落 `default → Final → Proxy`** | **两个脚本双双全绿，配置却不可用** |
| **v8** | 只改一条：`ChinaMax.list` → `ChinaMax_All_No_Resolve.list` | ✅ 同上（无退化） | ✅ **15/15 国内探针命中 `DIRECT`** | 补回国内域名直连 |

**用户的原始反馈是这样的：**

> 「没有 dns 泄露了，可是国内外的分流好像出了问题……国内的网站怎么都不是直连 反而走了代理，chinamax 基本都是一些 ip 走了直连，而国内域名基本都走了 final」

这句话里其实**已经把根因说出来了**：`ChinaMax` 里"基本都是一些 IP"，所以只有 IP 形式的连接走了直连。
问题不在 DNS，而在**被引用规则集的构成**。

---

## 3. 根因：规则集的名字会骗人

`ChinaMax.list` —— 这个名字听起来**最像**一份"中国域名表"。实测数据（GitHub API / `raw` / jsDelivr 三处交叉核对，均为 453,982 字节）：

| 类型 | 条数 |
|---|---|
| `IP-CIDR` | 8,251 |
| `IP-CIDR6` | 4,221 |
| `USER-AGENT` | 65 |
| **`DOMAIN-SUFFIX`** | **51** |
| **`DOMAIN-KEYWORD`** | **13** |
| `PROCESS-NAME`（Egern 未文档化） | 12 |
| `IP-ASN` | 1 |
| **合计** | **12,614** |

⇒ **IP 类 12,473 条 / 域名类只有 64 条（0.5%）。**

仓库自己的 README 写得很清楚：

> `ChinaMax.list`、`ChinaMax_Domain.list` **共同使用**。

同目录下另有：

| 文件 | 大小 | 内容 |
|---|---|---|
| `ChinaMax.list` | 454 KB | IP 为主（上面那张表） |
| `ChinaMax_Domain.list` | 1.5 MB | 纯域名 |
| **`ChinaMax_All_No_Resolve.list`** | **3.42 MB** | **111,332 域名 + 同份 12,472 IP（全带 `no-resolve`）** |

**⇒ 判据是「数域名条目」，不是看文件名，也不是看 README 标题。**

---

## 4. 替换的安全性：覆盖面无损失

换规则集之前必须核对两件事：**IP 覆盖面没变**、**旧版域名全被包含**。

```bash
# IP 段归一化比对（去掉 ,no-resolve 后逐条比）
grep -E '^IP-CIDR' 旧.list | sed 's/,no-resolve$//' | sort -u > ipA.txt
grep -E '^IP-CIDR' 新.list | sed 's/,no-resolve$//' | sort -u > ipB.txt
diff ipA.txt ipB.txt && echo "IP 段逐条相同 ✅"

# 域名段：旧的是不是新的子集
grep -E '^DOMAIN' 旧.list | sort -u > dA.txt
grep -E '^DOMAIN' 新.list | sort -u > dB.txt
comm -23 dA.txt dB.txt | wc -l    # 期望 0
```

实测结果：

| 核对项 | 结果 |
|---|---|
| IP 段（去 `,no-resolve` 后） | **12,472 条逐条相同** ✅ |
| 旧版 64 条域名 | **全部被新版包含**（差集 0）✅ |
| 新版域名条目 | **64 → 111,332** |
| 新版 IP 条目是否带 `no-resolve` | **12,473 条全部带** ⇒ 不会重新引入"为判定而强制解析" ✅ |

---

## 5. 验证：一个能复现用户现象的脚本

光比对文件不够 —— 必须**拿真实域名走一遍规则链**，看它到底命中哪条、被判给什么策略。

`audit_routing_coverage.py` 就是干这个的。它的设计有两个关键点：

1. **探针域名必须"不以 `.cn` 结尾"。**
   如果探针全是 `xx.cn`，那么 `domain_suffix: cn` 这条兜底会把它们全部救成 `DIRECT`，从而**掩盖"规则集没有域名覆盖"这个事实**。
   所以脚本用的是 `jd.com` / `zhihu.com` / `163.com` / `qq.com` / `douyin.com` / `meituan.com` / `xiaohongshu.com` 这类**国内但非 `.cn`** 的域名。
2. **同时跑境外探针**，确认没有把境外域名误判成直连。

实测结果（同一份脚本跑两个版本）：

| 探针 | v7（问题版） | v8（修复版） |
|---|---|---|
| `jd.com` / `zhihu.com` / `163.com` / `qq.com` / `douyin.com` / `meituan.com` / `xiaohongshu.com` | `default → Final` ❌ | `ChinaMax_All_No_Resolve` → **`DIRECT`** ✅ |
| 国内合计 | **7/15 落 `Final`** | **15/15 `DIRECT`** |
| 境外（google / youtube / github / x / openai / netflix / wikipedia） | — | 各归其组或落 `Final`，**无误判直连** ✅ |

---

## 6. 代价与取舍

| 项 | 旧 | 新 |
|---|---|---|
| 规则集大小 | 454 KB | **3.42 MB** |
| 首次加载/更新时间 | — | 略微增加（之后走缓存） |
| 内存 | — | 略微增加 |

如果感知明显变慢，有两条更轻的路子（**但都必须重跑分流审计**）：

1. 改用 `ChinaMax_Domain.list`（纯域名，1.5 MB）+ 保留 `geoip: CN` 的 IP 判定；
2. 只保留 `ChinaMax_All_No_Resolve.list`，并撤掉额外加的 `domain_suffix: cn` 那条兜底。

**回滚**：把第 44 条规则的 URL 改回 `ChinaMax.list` 即可（一行）。

---

## 7. 固化下来的规则

> **任何一次动 `no_resolve`、换 `rule_set`，都必须同时跑「分流覆盖审计」。**
> 判据是**数域名条目**，不是看规则集名字。
> 三个脚本里，`check_egern_dns.py` 和 `audit_ruleset_noresolve.py` 全绿**不代表配置可用** —— 它们不检查分流。

这条规则现在写进了 `skill/SKILL.md` 的验收标准第 6 条。

---

下一步：[docs/06 实测数据与版本谱系](06-实测数据与版本谱系.md)。
