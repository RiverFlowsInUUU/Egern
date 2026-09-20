# Egern 防 DNS 泄露配置模板

一份面向 [Egern](https://egernapp.com) 的代理配置模板。它不绑定任何特定节点或订阅，
核心目标只有一个：**在不依赖外部信息的前提下，彻底消除 DNS 泄露面**。

---

## 仓库内容

| 路径 | 说明 |
|---|---|
| `profiles/egern-anti-dns-leak.template.yaml` | 带注释版，每段都附有原理说明 |
| `profiles/egern-anti-dns-leak.template.min.yaml` | 纯配置版，与上面内容一致，仅去掉注释 |
| `icons/` | 模板用到的全部分流组图标（已整合进本仓库） |
| `docs/` | 原理深挖、审计清单与实测谱系 |
| `skill/` | 配套的 DNS 泄露诊断 / 加固脚本 |

> 两个模板文件**内容完全一致**，区别只在注释。按习惯取用其一即可。

---

## 配置框架

模板由若干顶层段组成，各司其职：

- **`proxies`** —— 你的节点。模板此处为空 `[]`，由你自行填写；填写后把下方分流组的
  `policies` 填上对应节点名（或订阅组名）。
- **`policy_groups`** —— 分流组，四种类型：
  - `select`：手动选路（如 `Proxy` / `Final` / 各类 App 组）
  - `smart`：按节点名 / 地区正则自动归类（如 `Hong Kong` / `USA` / `Japan`）
  - `fallback`：按延迟自动回退
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
所有 IP 类规则（`geoip` / `ip_cidr` …）都带 `no_resolve`，它们只匹配「已经是 IP」的连接，
不再触发任何域名解析。需要靠域名判定归属的国内直连，由**带域名的规则集**
（如 `ChinaMax_All_No_Resolve.list`）承接——它既有域名条目做直连判定，又有带 `no-resolve`
的 IP 条目不重新触发解析。两者绑定，缺一不可。

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

---

## 使用

1. 在 `proxies` 填入节点，或用 `policy_groups` 里 `external` 组的订阅 URL（把
   `sub.example.com?token=REPLACE_WITH_YOUR_TOKEN` 换成你自己的）。
2. 把空 `[]` 的分流组填上节点名 / 订阅组名。
3. 按需增删 `rules` 引用的规则集。

需要逐段深挖或跑审计，见 [`docs/`](docs/) 与 [`skill/`](skill/)。

---

## 图标与许可

- 模板用到的分流组图标整合自 [RiverFlowsInUUU/Rule]、[jnlaoshu/MySelf]、
  [Koolson/Qure](https://github.com/Koolson/Qure)，已统一存入本仓库 `icons/`，
  **不跨项目引用任何图标地址**。
- 本项目采用 MIT 许可证，见 [LICENSE](LICENSE)。
- 第三方规则集（blackmatrix7 / ACL4SSR / AWAvenue / Qure 等）版权归其原作者。
