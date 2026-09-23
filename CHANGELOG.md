# 📝 更新日志

> 记录**模板本身**的显著变动、以及**会误导使用者的文档错误**，按时间倒序。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
> 各版本说明见 [`README.md`](README.md) 的 [📥 两份配置](README.md#-两份配置)。
>
> 📌 **历史条目里的旧文件名**（按发生时的事实保留，不改写）—— 对应现在的名字：
>
> | 旧称 | 现名 |
> |:-----|:-----|
> | `v0` | `lazy`（2026-09-21 改名） |
> | `v1` / `v2` / `v2.1` ~ `v2.5` | `routing_v1` / `routing_v2` / `routing_v2.1` ~ `routing_v2.5`（2026-09-22 改名） |
>
> 上表只讲**文件名**。**迭代谱系**（`f1`~`f10`）是另一个维度，2026-09-22 起统一用 `f` 前缀 ——
> 历史条目里原本写作 `v1`…`v10` 的迭代编号也已一并改为 `f`（只改标签，事实未动）。
>
> 🏷️ **仓库曾用名**：`egern-anti-dns-leak` → **`Egern`**（2026-09-22 改名）。
> GitHub 对改名仓保留 **301 跳转**，**旧订阅地址与图标 URL 仍然可用**；
> 仓库内的引用已全部改成新名，新写地址请用 `.../RiverFlowsInUUU/Egern/...`。

### 2026-09-23

### 新增

- 🆕 **`routing_v3`（分流版 · 推荐）** —— 相对 `routing_v2.4` 的四项变化：
  1. **订阅槽位 2 → 1**：`Airport-A` / `Airport-B` 合并为单个隐藏 `Airport`（`hidden: true`），组数 `27 → 26`。
  2. **`dns.forward` 1 → 4 条**：`白名单(white-guard → Domestic-DNS)` → `Jinx-Ads / AWAvenue (value: reject)`
     → `catch-all`。官方 `value` 字段规定特殊值 `reject` =「refuse the query and return an empty response」，
     命中即在**解析阶段**拒答 ⇒ 等价 Surge 的 `pre-matching REJECT`。
     ⚠️ **白名单必须排在两条广告清单之前**（AWAvenue 会命中白名单里 10 条功能域），否则白名单域名连解析都拿不到。
     防泄露面不变：查询去向仍是 `Domestic-DNS`（加密）或拒答二选一，`proxy_nameservers` 绕过 forward、`bootstrap` 依旧闲置。
  3. **`rules` 补 `Private`（`private.txt` → `DIRECT`）**、**删内联 `domain_suffix: cn`**
     （`direct.txt` 第 23828 行已含 `DOMAIN-SUFFIX,cn`，属重复）；`rule_set` 条数 `21 → 22`，`rules` 总数仍 24。
  4. **规则段与 Surge `routing_v3` 内容与顺序逐行对拍**：内网段提前到应用之前，`WeChat` 后移到 `Apple` 之后。
- 🧪 **审计脚本判据扩展**：`audit_dns_forward.py` 原先要求 forward 的 `value` 全体单值，
  现改为「**非 `reject` 去向单值且等于兜底组**」—— `reject` 是终止动作（拒答、不产生解析），与兜底组可并存。
  已用 5 个 fixture 回归（`bad_*` 仍判负、`ok_*` 仍通过）。

### 变更

- 📝 **文档同步 v3**：`README`（订阅地址 → `routing_v3.min.yaml`、组数徽章 26、订阅槽位说明改为 1 处）、
  `DetailsReadme`（§1.5 forward 表、§2.3 ③、§2.4 判据、§6 已知代价、Q8）、
  `docs/04`（组数 / 规则构成 / forward 说明）、`docs/06`、`docs/07`（新增 `routing_v3` 行与差异明细）、
  `docs/08` `docs/09` `docs/11`（规则表整段重写）、`skill/SKILL.md`、`skill/reference/*`。
- ⚠️ **文件名与 Surge 对齐**：Surge 同日把 `routing.conf` 改名为 `routing_v3.conf`（旧地址 404）。

---

## 2026-09-22

**变更**

- 🪟 **README 去掉「防泄露原理」整节 —— 门面只讲功能** —— 原 `## 🌐 防泄露原理`（两套 DNS 分工表 + `bootstrap` 两个用途与堵法表）是机制推导，不该出现在产品页。改为 `## 🌐 DNS 防泄漏` 的**能力清单**：`hijack_dns: '*'` 全量接管 · 4 个加密端点全为 IP 字面量 · catch-all 兜住全部域名、永不落到 `bootstrap` · `proxy_nameservers` 专用通道强制直连 · `no_resolve` 与 `direct.txt` 成对交付 · 审计读数 **0 high**、路由覆盖 **15/15**。只讲「得到什么」，不讲「为什么」。
  - 📌 口径入 [`skill/reference/public-repo.md`](skill/reference/public-repo.md)：合法的产品内容也要分层，`README` 只放「有什么 · 怎么用 · 防在哪」；连「原理」二字都不出现在门面标题里。
  - ✅ 配置与 `dns` 段一行未动；推导仍在 [`DetailsReadme` §2](DetailsReadme/DetailsReadme.md#2-防泄露原理从机制到推导)。
- 🔗 **README「文件结构」改为可点击跳转** —— 原先是 fenced code block 里的目录树，而 GitHub **不解析代码块内的 markdown**，那些路径一个都点不动、只能靠手翻。改为表格（图标 / 路径 / 说明），路径列写成相对链接，点一下直达对应目录或文件 —— `profiles/` · `icons/` · `docs/` · `DetailsReadme/` · `CHANGELOG.md` · `skill/` 六个入口全部可点。三仓同步同一版式。
  - 📌 顺带用修正后的 `check_links.py`（借姊妹仓 `Surge` 的）跑了一遍本仓全部 markdown：21 个文件 / 108 条相对链接与锚点**全部可解析**。此前它报 `#4-policy_groups-段`、`#13-policy_groups--四种类型组间引用图标` 两条「失效」是**脚本自身的 bug**（下划线被误删），链接本来就是对的 —— 详见 `Surge` 仓 CHANGELOG 同日「`check_links.py` 锚点算法三处修正」。
- 📚 **首页下沉规则集信息，新开专题接住** —— 首页原有三处规则集层面的内容：「📋 规则顺序」表（`Jinx white-guard` / `Apple_All_No_Resolve` / `direct.txt` / `geoip: CN` 等）、「分流版的应用规则」表（13 行「规则集 → 去向」）与「📚 规则来源」整节。规则集属**实现侧**，读者只关心「能实现怎样的分流」，于是：
  - 📋 「规则顺序」改为 **「分流顺序」** —— 列「匹配什么 → 去向」（白名单域名 / 广告域名 / 内网 / 按应用 / Apple / 微信 / 国内 / 其余全部），首页不再出现规则集文件名与 `geoip` 这类规则类型；
  - 📚 「分流版的应用规则」表与「三条排序约束」撤下首页（**应用组的默认出口表留下** —— 那是组级信息，使用者要按组改道）；
  - 📚 「规则来源」整节撤下首页；
  - 🆕 新开 [`docs/11-规则集与来源.md`](docs/11-规则集与来源.md) —— 8 项共用规则集 + 15 条分流版专有项的「指向 / 作用 / 去向 / 来源」、两版逐条匹配顺序、四条排序约束、数据库与许可；
  - 🔗 首页只在「文件结构」与「更多文档」里各留一个入口（篇数 10 → **11**）；
  - 📌 口径入 [`skill/reference/public-repo.md`](skill/reference/public-repo.md)（新增「首页不列规则集」一节）。

**修复**

- ✂️ **README 移除一段「文档自述」—— 产品介绍不写我们怎么改的** —— 「📋 规则顺序」表下原有一段
  📌 讲「**上面是分类顺序**，文件里真正的匹配顺序…」。那是改动记录 / 文档自指，不是产品说明。
  已整段移除；其中唯一的事实（`routing_v2.4` 里「应用」之后有一条 `Proxy` 规则被
  `disabled: true` 关掉）移入 [`DetailsReadme` §1.4](DetailsReadme/DetailsReadme.md#14-rules--匹配表与直连规则集)，
  并顺手补全**完整的实际匹配顺序**。
  - 📌 口径入 [`skill/reference/public-repo.md`](skill/reference/public-repo.md)（新增「README 只讲产品，不讲我们怎么改的」一节）：
    README 不写归类自述 / 文档自指 / 评审对话 / 内部断言名。
  - ✅ 表内数据一行未动（规则顺序表与实际匹配顺序本就一致，只缺那条 disabled 的 `Proxy`）；
    配置与规则顺序未动。
- 🔗 **修一处因首页下沉而失效的仓内指路** —— README 章节撤下会让引用它的链接**静默失效**（GitHub 不报错，读者点 404）：`docs/10-图标与许可.md` 的「规则集来源清单见 README 的 📚 规则来源」→ 改指 [`docs/11`](docs/11-规则集与来源.md)。由 `check_links.py` 抓出。

**移除**

- 🗑️ **撤销 `routing_v2.5`，推荐版交回 `routing_v2.4`** —— 删除 `profiles/routing_v2.5.yaml` /
  `routing_v2.5.min.yaml`。v2.5 相对 v2.4 的**唯一**差异就是广告拦截规则集换用 `Jinx` 的
  **差集版**清单（`surge-ads.list` → `surge-ads-delta.list`）；而差集版已于同日被上游删除
  （该 URL 现已 **404**）⇒ 改回黑名单后两者**逐字相同**，v2.5 沦为纯冗余版本。
  留着它就是「同一件事写在两个地方，早晚只会改一处」。
  ⚠️ **订阅地址变更**：指向 `profiles/routing_v2.5(.min).yaml` 的地址会 404，改用
  `profiles/routing_v2.4(.min).yaml`。`routing_v2.4` 的表头本来就写着「正式版 · 推荐」，
  该文件**一字未动**。详见 [`docs/07`](docs/07-文件版本沿革.md) 的「已撤销」。
- 🏷️ **术语与上游对齐** —— 「白名单守卫」→「**白名单**」（与 `Jinx` 的用词统一）。
  文件名 `surge-white-guard.list` 未动，订阅地址不受影响。

**变更**

- 🧭 **分流版加 `routing_` 前缀** —— `profiles/v1.yaml` → `routing_v1.yaml`，
  `v2` / `v2.1` ~ `v2.5` 同理（`.min` 一并改），共 14 个文件。
  **配置内容逐字未变**（有效配置逐行 diff 为空），只动文件名与注释头。
  原因：`lazy` 退出 `vN` 体系后（见 2026-09-21），`v1`…`v2.5` 不再有「起点」，读起来像一串孤立的旧版号；
  加前缀明确它们是**同一条线**，也与姊妹项目 `Surge` 的 `routing.conf` 命名对齐。
- 📝 **首页说法与 `Surge` 对齐** —— 「两份配置」改为
  🪶 **懒人版 · 一个出口** / 🧭 **分流版 · 按应用 + 按地区**，两节标题随之改为「懒人版」「分流版」；
  懒人版一节移到分流版之前，与 Surge 的排布一致。
- 📝 **文档全线改用新命名** —— README / `docs/04`·`06`·`07`·`08`·`09` / `DetailsReadme` /
  `skill/` 共 12 个文件。⚠️ **`docs/06` 与 `DetailsReadme` §3 的「配置迭代谱系」是另一个维度** ——
  这次**刻意未动**，当日稍后单独处理（见下条）。
- 🔤 **迭代谱系 `v` → `f`** —— 文档里的**配置迭代编号**由 `v1`…`v10` 统一改为 `f1`…`f10`
  （含 `v3.1` / `v10.1` ~ `v10.3`）。**只改标签，事实未动** —— 每一代改了什么、审计读数如何，一字未改。
  原因：文件版本已叫 `routing_v1`…`routing_v2.5`，与迭代编号撞了同一个 `v`，
  同一段话里 `v1` 有时指文件、有时指迭代；顶部映射表也无法消歧（两行的 `v1` / `v2` 会重叠）。
  现在固定为 **`v` = 文件版本，`f` = 迭代谱系**。涉及 README / `docs/01`~`07` / `DetailsReadme` /
  `skill/`（含脚本注释）/ `profiles/*.yaml` 注释，共 26 个文件。
  ⚠️ **未触碰**：订阅 URL 里的 `api/v1`、第三方内核版本 `mihomo v1.19`、以及文件版本 `routing_vN` 本身。
- 📝 **[`docs/07`](docs/07-文件版本沿革.md) 重写为「两条线」结构** —— 新增「改名记录」一节，把各次改名
  （`v0`→`lazy`、`v1`~`v2.5`→`routing_*`、迭代编号 `v`→`f`）的**旧名 → 新名对照**与原因都记下来。
- 🏷️ **项目定位调整** —— 本仓交付的是**两份模板**（🪶 懒人版 / 🧭 分流版），
  **防 DNS 泄露是它们的特色，不是全部定位**。README 首页标题由「Egern 防 DNS 泄露配置」
  改为「Egern 配置模板」，副标题摆出两个模板、DNS 零泄露降为特色一句；
  badge 行把 `Profiles` / `Groups` 提到 `DNS` 之前。
- 📦 **仓库改名 `egern-anti-dns-leak` → `Egern`** —— 原名把定位写死在「防泄露」上；
  同日随后做了**大小写规范化**（`egern` → `Egern`），与官方写法一致。
  ⚠️ **旧链接不会失效**：GitHub 对改名仓保留 301 跳转，旧订阅地址与图标 URL 仍能下载
  （**实测**：raw 旧名 HTTP 200、jsDelivr 旧名 HTTP 200、`github.com` 旧名 301 → 新名）。
  仓内引用共改两轮 —— 首轮 557 处（图标 URL / 订阅地址 / 文档自引用 / 姊妹仓交叉引用），
  本轮再改 **562 处**。姊妹项目 `surge-anti-dns-leak` 同步改名为 `Surge`。
  - 📌 **代码标识符与文件名保持小写**：`check_egern_dns.py` / `_egern_common.py` /
    `egern-profile-dns-hardening` 等一律未动，只改文本里的裸称呼。
- 📝 **GitHub 仓库描述同步修正** —— 改为「两个模板 + DNS 特色」的说法，
  并修掉两处过期数字（加固清单 17 → **18** 项、审计脚本 6 → **5** 个）。
- 🏷️ **16 条 `rule_set` 补上 `name`** —— 14 份 profile 共 **202 处**（14 文件 ×5 条 + 12 文件 ×11 条）。
  在此之前只有 5 条 AI 相关规则集带 `name`（`ChatGPT` / `Gemini` / `Anthropic` / `Claude` / `AI`），
  其余全是匿名。本次补全为：
  `Jinx-Ads` / `AWAvenue-Ads` / `Jinx-CN` / `Lan` / `Apple` / `CN` /
  `Github` / `Google` / `Microsoft` / `Proxy` / `Spotify` / `Telegram` / `Twitter` / `WeChat` /
  `YouTube` / `YTM`。
  官方字段说明：`name` 为**可选**（"The rule name, used for logging and debugging"），
  必填的是 `match` / `policy` ⇒ **本次改动不改变任何路由行为**。
  ⚠️ 已命名的 5 条与四处 `name` 值**一字未动**；`disabled` / `update_interval` / 规则顺序全部保持原样。
  实测依据：**202 处纯新增、0 删除**；`yaml.safe_load` 解析后「剥掉 `name`」与改动前**逐字段等价**；
  仓内回归 **19 passed / 0 failed**（阶段 1·5 + 阶段 2·14，与改动前一致）。

**修复**

- 🐛 **AWAvenue 广告规则集换用 RULE-SET 版** —— **14 份 profile + 5 个测试 fixture** 的地址由
  `.../Filters/AWAvenue-Ads-Rule-Surge.list` 改为 `.../Filters/AWAvenue-Ads-Rule-Surge-RULE-SET.list`。
  两者同仓同源、**格式不同**：前者是**裸域名**（`.8le8le.com`，前导点 = 该域及其所有子域），
  对应 Surge 的 **`DOMAIN-SET`** 规则类型；后者是 `DOMAIN,xxx` 规则行，对应 **`RULE-SET`**。
  而 profile 用的是 `rule_set`（消费 Surge RULE-SET 格式）⇒ 原地址与消费方式不匹配。
  同时 RULE-SET 版**内容更全：965 条 vs 961 条** —— 多出的 4 条是无法写成裸域名的
  `DOMAIN-KEYWORD` / `DOMAIN-SUFFIX` 条目。
  ⚠️ **未实测 Egern 是否容忍裸域名文件**（其 `rule_set` 文档未明确）；但换成 RULE-SET 版在两种情形下
  都正确 —— 格式确定匹配，且条目更全。判据依据 Surge 官方语法：`RULE-SET` 可含所有类型子规则，
  `DOMAIN-SET` 仅可含 `DOMAIN` / `DOMAIN-SUFFIX` 两种形式的内容。
  姊妹仓 `Surge` 无此问题（全部使用 `RULE-SET`，且未引用 AWAvenue），已核对。

> ⚠️ **旧 raw 链接已失效** —— 原先指向 `profiles/v2.5.min.yaml` 的订阅地址现在会 404，
> 改用 `profiles/routing_v2.5.min.yaml`。
> （⚠️ 该文件**同日又随 `routing_v2.5` 撤销而删除** —— 现应用 `profiles/routing_v2.4.min.yaml`，见本节顶部。）

### 2026-09-21

**变更**

- 🪶 **`v0` 改名为 `lazy.yaml`** —— 「懒人配置」不再挂版本号，`profiles/v0.yaml` → `profiles/lazy.yaml`、
  `v0.min.yaml` → `lazy.min.yaml`。**配置内容逐字未变**（`git diff` 零增删），只动文件名与注释头。
  原因：它是长期沿用的懒人入口、不随完整分流迭代而变，挂 `v0` 反被误读成「最早的旧版」。
  `vN` 链条现在从 `v1` 起，与 `lazy` 是两条独立的线；`v1` ~ `v2.5` 照常保留以备对照。
  （次日 `v1`…`v2.5` 又加 `routing_` 前缀，见上。）

**新增**

- ✨ **`v2.1`** —— `v2` 的精简版：删掉 52 行与官方默认值重复的配置项，**行为完全一致**。
- ✨ **`v2.2`** —— 机场订阅槽位 **4 → 2**（删 `Airport-C` / `Airport-Free`），`MAX` 改为「带节点筛选的 `Smart`」、不再自带订阅 URL；`dns` 段与规则逐行未变。
- ✨ **`v2.3`** —— `v2.2` 的修正后继，修 4 处（`MAX` 的筛选规则、`Korea` 的冗余上游、`Smart` 的 `flatten`、`ChatGPT` / `Gemini` 的空组）；`dns` 段与规则逐行未变。**导入前只剩订阅地址要填**，明细见 [`docs/04` §4](docs/04-模板逐段讲解.md#4-policy_groups-段)。
- ✨ **`v2.4`** —— `v2.3` 的补全后继：给全部 21 条 `rule_set` 补上 `update_interval: 86400`，规则集改为**按天自动刷新**；`dns` 段、规则内容与顺序、`policy_groups` 段逐字未变。
- ✨ **`v2.5`（当前推荐版）** —— `v2.4` 的后继：广告拦截规则集换用 `Jinx` 的 **delta 版**清单（`surge-ads.list` → `surge-ads-delta.list`，路径同时改为显式的 `refs/heads/main/`）；`dns` 段、`policy_groups` 段与其余规则逐字未变。

**变更**

- 🔧 **推荐版当天四次移交** —— `v2.1` → `v2.2` → `v2.3` → `v2.4` → `v2.5`；`v2.2` / `v2.3` / `v2.4` 降为保留版。
- 📝 **README 首页的版本介绍改为「两个版本」，旧版细节移入新文档** —— 平铺 7 行容易让人以为要从中挑一个。实际只有 `v2.4`（推荐，完整分流）与 `v0`（极简懒人版）两个可选，其余 5 个都是 `v2.4` 的历代旧版、保留以备对照。各版逐项差异、组 / 规则数与审计读数统一收进新增的 [`docs/07-文件版本沿革.md`](docs/07-文件版本沿革.md)，README / `docs/04` 头部 / `DetailsReadme` §6 三处只留指针。
- 📝 **README 再精简：三节移入 `docs/`** —— 「审计读数」「注意事项」「图标与许可」整节迁入 [`docs/08-审计读数.md`](docs/08-审计读数.md) / [`docs/09-注意事项.md`](docs/09-注意事项.md) / [`docs/10-图标与许可.md`](docs/10-图标与许可.md)，README 只留一张「更多文档」表列出全部入口；另去掉与表内 `CHANGELOG.md` 那行重复的「更新日志」指针小节。**270 → 229 行**。
- 📝 **README 文风改为陈述式，解释性长段下沉 `DetailsReadme`** —— `flatten` 的两级 / 一级选优推导、`fallback` 为何必须配 `flatten`、`v0` 的两处专属调整、地区组负向断言的维护提醒、`v2.1` 及更早的 4 个订阅槽位，全部迁入 [`DetailsReadme` §1.3](DetailsReadme/DetailsReadme.md#13-policy_groups--四种类型组间引用图标) 新增的「组清单与要点」；README 只留表格与结论句，hero 标题居中、页脚补回许可入口。**229 → 215 行，内容零丢失**。
- 🛡️ **`v0` / `v1` / `v2`** —— 规则数 22 → 24（`v0` 为 7 → 9），新增广告白名单。
- 🔧 **`v0`** —— `AD` 组只保留 `REJECT`；`Final` 组不再显示在策略列表中。

**移除**

- 🧹 **`v0` / `v1`** —— 删除与官方默认值重复的配置项（−17 / −52 行），**行为无变化**。

**修复**

- 🐛 **`DetailsReadme` 页脚三个导航链接此前无法跳转** —— 相对路径缺 `../`（实际指向不存在的 `DetailsReadme/docs/`），现已能正确进入 `docs/01` / `02` / `03`。
- 🐛 **FAQ 里的模板文件名是改名前的旧称** —— 原文写 `*.template.yaml` / `*.template.min.yaml`，实际文件名是 `profiles/v2.3.yaml` / `profiles/v2.3.min.yaml`（其余版本同理）。
- 🐛 **`docs/06` 的谱系范围标注错误** —— 此前称其收录 f1~f10，实际只到 f8；f9–f10 的完整谱系在 `DetailsReadme` §3。
- 🐛 **`DetailsReadme` 大量描述停在 `v1` 时期** —— `dns` 子段端点数（6 / 3 / 6 → 实际 4 / 2 / 4）、`forward` 兜底（2 条 → 1 条）、顶层段（约 15 个 → 12 个，并删掉三个不存在的键）、`Foreign-DNS`（写成「注释保留」→ `v2` 起已整段删除）、`ChatGPT` / `Gemini`（写成待填空组 → `v2.3` 起已填 `[Proxy]` + `flatten`）。
- 🐛 **`DetailsReadme` §4 的脚本表只列 3 个审计脚本** —— 实际 5 个（漏了 `audit_dns_forward.py` / `audit_region_filters.py`）；§3 的 `check_egern_dns.py` 读数写成 30 ok，那是 `v1` 的值（`v2` 起为 24 ok）。
- 🐛 **多份文档写死 `direct.txt` 的条目数**（111,160 条，`DetailsReadme` / `docs/04` / `docs/05` / `docs/06`）—— 该列表随上游更新，改用约数。
- 🐛 **`skill/` 下三处回归断言数停在 22** —— 阶段 2 的 profile 份数随 `v2.4` 从 12 增到 14，总数应为 24（`skill/README.md` / `skill/reference/checker.md` / `skill/reference/public-repo.md`）。

**安全**

- 🔒 新增 `skill/scripts/audit_region_filters.py` —— 守住 `Other Regions` 负向断言与 6 个地区组关键词的「两份拷贝」同步（漏同步会让两组不再互斥）。

### 2026-09-20

**新增**

- ✂️ **`v2`** —— `dns` 段从 40 行精简到 22 行：删掉无引用点的 `hosts:` 段、语义重叠的第二条兜底规则，端点 6 → 4。原模板保留为 **`v1`**。
- 🍃 **`v0`** —— 极简版：4 个策略组 + 7 条规则。

**变更**

- 🔗 **`forward` 与订阅解耦** —— 换订阅、换机场、换节点域名，`dns` 段一个字都不用改。
- 🎯 国内域名直连改用 Loyalsoldier `direct.txt`；AI 分区接入 ACL4SSR `AI.list`。

**移除**

- 🗑️ 15 条 DNS 端点固定路由规则、10 条 `disabled: true` 的遗留规则。
- 🔒 全部虚拟节点 / 机场订阅 URL / 证书 —— 仓库转为纯模板发布。

**修复**

- 🐛 `audit_dns_forward.py` 不带参数即崩溃（`UnboundLocalError`）。
- 🐛 IPv6 端点被截断成 `'[2400:3200:'`，同一份配置两个脚本结论相反。
- 🐛 `group_reach` 判据失效，会把本模板误报成 3 个高危、退出码 1。

### 2026-09-19

**新增**

- 🎉 仓库初始化。
