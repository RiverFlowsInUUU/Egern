# Egern 防 DNS 泄露配置模板

一份面向 [Egern](https://egernapp.com) 的代理配置模板。它不绑定任何特定节点或订阅，
核心目标只有一个：**在不依赖外部信息的前提下，彻底消除 DNS 泄露面**。

---

## 仓库内容

| 路径 | 说明 |
|---|---|
| `profiles/v2.yaml` | **推荐** · 带注释版，每段都附有原理说明 |
| `profiles/v2.min.yaml` | **推荐** · 纯配置版，与上面内容一致，仅去掉注释 |
| `profiles/v1.yaml` | 旧版 · 带注释版。`dns` 段较冗长（40 行），功能与 v2 等价 |
| `profiles/v1.min.yaml` | 旧版 · 纯配置版 |
| `icons/` | 模板用到的全部分流组图标（已整合进本仓库） |
| `docs/` | 原理深挖、审计清单与实测谱系 |
| `skill/` | 配套的 DNS 泄露诊断 / 加固脚本 |

> **推荐用 v2。** v1 与 v2 的差别**只在 `dns` 段**，其余顶层段逐字相同。
> v2 把 `dns` 段从 40 行压到 22 行：删掉了没有任何引用点的 `hosts:` 段、
> 与 catch-all 语义完全重叠的第二条兜底规则，并把 6 个端点收敛为「2 机构 × 2 协议」的 4 个。
> 防泄露能力经仓库自带审计脚本实测**逐项等价** —— 差异仅为被删端点各自的逐条检查项，
> 结构性判据（兜底组直连可达 / 无待解析项 / `proxy_nameservers` 已设置）全部照旧通过。
>
> 同版本内「带注释」与「纯配置」两份**内容完全一致**，区别只在注释。按习惯取用其一即可。
>
> ⚠️ **别和「配置迭代谱系」混淆**：`docs/06` 里的 v1~v10 指的是本配置**自身的历史迭代**
> （v7 引入 `proxy_nameservers`、v10 塌缩 `forward` …）；而 `profiles/v1.yaml` / `v2.yaml`
> 指的是**文件版本**（v1 = 初版，v2 = DNS 段精简版）。两者是不同维度，别对号入座。

---

## 配置框架

模板由若干顶层段组成，各司其职：

- **`proxies`** —— 你的节点。模板此处为空 `[]`，由你自行填写；填写后把下方分流组的
  `policies` 填上对应节点名（或订阅组名）。
- **`policy_groups`** —— 分流组，本模板用到四种类型：
  - `select`：手动选路（如 `Proxy` / `Final` / 各类 App 组）
  - `smart`：智能选优 —— 组内多轮测速、按延迟/抖动/可靠性综合打分，自动选当前最稳的节点。
    模板里的地区组（`Hong Kong` / `USA` / `Japan` …）是 `smart` 再配一条 `filter` 正则，
    把订阅里名字匹配该地区的节点筛进来（**「按正则归类」是 `filter` 干的，不是 `smart` 本身**）。
  - `fallback`：故障转移 —— 按 `policies` 顺序依次尝试，选**第一个可用**的节点；当前节点不可用时
    才切到下一个，高优先级节点恢复后自动切回。（**不是**「按延迟选优」，那是 `auto_test` 的行为。）
  - `external`：从订阅 URL 拉取节点（模板里是 `sub.example.com` 占位）
  - 组与组之间可以互相引用；暂时没有成员的组留 `[]`，你再补。
- **`rules`** —— 匹配表：域名 / IP / 规则集 / `geoip` → 策略（`DIRECT` / 某个代理组 / `REJECT`）。
  这是「什么流量走哪里」的总指挥。
- **`dns`** —— 双 DNS 模型的核心（见下）。
- 其余（`real_ip_domains`、`*_latency_test_url`、`geoip_db_url` 等）—— 全局开关、测速地址、
  地理库来源等辅助项。

---

## 防泄露原理

理解这一节，只需记住一个事实：**Egern 有两套 DNS**。

1. **默认 DNS** —— 处理业务流量的域名解析。按 `dns.forward` 匹配上游，未命中则回退到
   `dns.bootstrap`。
2. **代理 DNS**（`dns.proxy_nameservers`）—— 只负责解析「节点 `server` 里的域名」，且强制在
   **直连侧**完成（代理还没通，不可能让代理去解析自己的地址）。

**泄露只会发生在一条路径上：明文 `UDP:53` 的 bootstrap。** 本模板用三条原则让它「无事可做」：

### ① 端点全部写成 IP 字面量
`dns.upstreams` 与 `dns.proxy_nameservers` 里**不出现任何主机名**。
没有需要解析的目标 ⇒ bootstrap 的用途①（解析加密 DNS 服务器主机名）被直接消灭。

### ② `no_resolve` 成对出现
所有 **IP 类规则**（`geoip` / `ip_cidr` …）都带 `no_resolve` —— 它们只匹配「已经是 IP」的连接，
不再触发任何域名解析（否则每个走到它的域名都会被强制本地解析一次，正是泄露来源）。
代价是 IP 规则不再能靠解析判定域名归属，所以必须有一份**域名条目足够多的国内直连规则集**兜住域名，
例如 Loyalsoldier `direct.txt`（11 万条，纯域名）。两者成对，缺一不可。

### ③ `forward` 塌缩为两条兜底
```yaml
forward:
  - domain_regex: '.'        value: Domestic-DNS
  - domain_wildcard: '*'     value: Domestic-DNS
```
原因有两层，决定了「不必在 forward 里列举任何节点 / 订阅域名」：
- 配了 `proxy_nameservers` 后，**代理 DNS 会跳过 forward** —— 节点域名根本不走这里；
- 兜底 `value` 为单值时，**规则顺序与域名清单都不影响结果**。

于是 forward 与订阅彻底解耦：你换十个订阅，这里一行都不用改。防泄露的安全性由
「兜底组本身是否直连可达」承担，而非由「在 forward 里罗列域名」承担。

**结论**：启动期、节点域名解析、业务解析三条路径，都不再接触明文 `:53`。

### 审计读数
本仓库附带的审计脚本可直接对本模板运行（`skill/scripts/`），**四个脚本全绿**：

| 脚本 | 本模板读数 |
|---|---|
| `check_egern_dns.py` | ✅ 0 high（退出码 0）—— 另有 2 条 `LOW`（见下） |
| `audit_ruleset_noresolve.py` | ✅ OK 19/19 规则集（IP 类条目全部带 `no-resolve`） |
| `audit_routing_coverage.py` | ✅ 15/15 国内探针 `DIRECT` |
| `audit_dns_forward.py` | ✅ 通过（退出码 0；`--drill` 可选，加不加都通过） |

两条 `LOW` 都是**刻意为之、需你确认**的：① 设置了 `proxy_nameservers`（它会成为代理侧解析的唯一出口）；
② 兜底指向国内组（需要本地解析的境外域名会拿到国内答案，实际影响面仅限 DIRECT 域名）。
**它们不是缺陷，是设计取舍。**

**回归测试**：`bash skill/tests/run.sh` 把 5 个 fixture 同时喂给两个脚本（10 个断言），退出码非 0 即失败。
CI 见 `.github/workflows/audit-regression.yml`。

---

## 使用

1. 在 `proxies` 填入节点（模板此处为空 `[]`），或用 `policy_groups` 里 `external` 组的订阅 URL（把
   `sub.example.com?token=REPLACE_WITH_YOUR_TOKEN` 换成你自己的）。
2. 把空 `[]` 的分流组填上节点名 / 订阅组名。
3. 按需增删 `rules` 引用的规则集。

需要逐段深挖或跑审计，见 [`docs/`](docs/) 与 [`skill/`](skill/)。
被本文省略的全部细节——逐段框架、原理推导、v1–v10 版本谱系、18 项审计清单、规则集开销实测、已知取舍，以及配套 Skill 的方法论——集中于 [`DetailsReadme/`](DetailsReadme/)。

---

## 图标与许可

- 模板用到的分流组图标整合自 [RiverFlowsInUUU/Rule]、[jnlaoshu/MySelf]、
  [Koolson/Qure](https://github.com/Koolson/Qure)，已统一存入本仓库 `icons/`，
  **不跨项目引用任何图标地址**。
- 本项目采用 MIT 许可证，见 [LICENSE](LICENSE)。
- 第三方规则集（blackmatrix7 / ACL4SSR / AWAvenue / jinx-ads-rules / Qure 等）版权归其原作者。
