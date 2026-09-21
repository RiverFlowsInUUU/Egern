# 📝 更新日志

> 记录**模板本身**的显著变动、以及**会误导使用者的文档错误**，按时间倒序。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。
> 配置文件版本的说明见 [`README.md`](README.md) 的 [📦 两个版本](README.md#-两个版本)。

### 2026-09-21

**新增**

- ✨ **`v2.1`** —— `v2` 的精简版：删掉 52 行与官方默认值重复的配置项，**行为完全一致**。
- ✨ **`v2.2`** —— 机场订阅槽位 **4 → 2**（删 `Airport-C` / `Airport-Free`），`MAX` 改为「带节点筛选的 `Smart`」、不再自带订阅 URL；`dns` 段与规则逐行未变。
- ✨ **`v2.3`** —— `v2.2` 的修正后继，修 4 处（`MAX` 的筛选规则、`Korea` 的冗余上游、`Smart` 的 `flatten`、`ChatGPT` / `Gemini` 的空组）；`dns` 段与规则逐行未变。**导入前只剩订阅地址要填**，明细见 [`docs/04` §4](docs/04-模板逐段讲解.md#4-policy_groups-段)。
- ✨ **`v2.4`（当前推荐版）** —— `v2.3` 的补全后继：给全部 21 条 `rule_set` 补上 `update_interval: 86400`，规则集改为**按天自动刷新**；`dns` 段、规则内容与顺序、`policy_groups` 段逐字未变。

**变更**

- 🔧 **推荐版当天三次移交** —— `v2.1` → `v2.2` → `v2.3` → `v2.4`；`v2.2` / `v2.3` 降为保留版。
- 📝 **README 首页的版本介绍改为「两个版本」，旧版细节移入新文档** —— 平铺 7 行容易让人以为要从中挑一个。实际只有 `v2.4`（推荐，完整分流）与 `v0`（极简懒人版）两个可选，其余 5 个都是 `v2.4` 的历代旧版、保留以备对照。各版逐项差异、组 / 规则数与审计读数统一收进新增的 [`docs/07-文件版本沿革.md`](docs/07-文件版本沿革.md)，README / `docs/04` 头部 / `DetailsReadme` §6 三处只留指针。
- 🛡️ **`v0` / `v1` / `v2`** —— 规则数 22 → 24（`v0` 为 7 → 9），新增广告白名单守卫。
- 🔧 **`v0`** —— `AD` 组只保留 `REJECT`；`Final` 组不再显示在策略列表中。

**移除**

- 🧹 **`v0` / `v1`** —— 删除与官方默认值重复的配置项（−17 / −52 行），**行为无变化**。

**修复**

- 🐛 **`DetailsReadme` 页脚三个导航链接此前无法跳转** —— 相对路径缺 `../`（实际指向不存在的 `DetailsReadme/docs/`），现已能正确进入 `docs/01` / `02` / `03`。
- 🐛 **FAQ 里的模板文件名是改名前的旧称** —— 原文写 `*.template.yaml` / `*.template.min.yaml`，实际文件名是 `profiles/v2.3.yaml` / `profiles/v2.3.min.yaml`（其余版本同理）。
- 🐛 **`docs/06` 的谱系范围标注错误** —— 此前称其收录 v1~v10，实际只到 v8；v9–v10 的完整谱系在 `DetailsReadme` §3。
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
