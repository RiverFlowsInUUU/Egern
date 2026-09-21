# 公开模板仓库（本项目的对外交付物）

> 本文是 [`SKILL.md`](../SKILL.md) 的引用文件。 **何时读**：要更新模板 / 了解公开仓库结构时。

---

自用配置已脱敏发布为公开模板 + 文档 + 本 skill：

**https://github.com/RiverFlowsInUUU/egern-anti-dns-leak**

```
README.md                                   # 三条铁律 + 一图看懂回退链
profiles/v2.4.yaml                          # 脱敏模板 · 推荐版（无节点、无订阅、无证书；机场槽位 2 个）
profiles/v2.4.min.yaml                      # 同上，纯配置版（去注释）
profiles/v2.3.yaml / v2.3.min.yaml          # 保留（与 v2.4 只差 rule_set 的 update_interval）
profiles/v2.2.yaml / v2.2.min.yaml          # 保留（与 v2.3 只差 4 处修正）
profiles/v2.1.yaml / v2.1.min.yaml          # 保留（与 v2.2 只差机场槽位：4 个 vs 2 个）
profiles/v2.yaml / v2.min.yaml              # 保留原样（比 v2.1 多 52 行「值等于默认值」的冗余行）
profiles/v1.yaml / v1.min.yaml              # 旧版，保留不删（dns 段较冗长，功能等价）
profiles/v0.yaml / v0.min.yaml              # 极简懒人版 · 可选（4 组 / 9 条规则，Final 隐藏、AD 只留 REJECT）
CHANGELOG.md                                # 更新日志（按时间倒序，README 只留引用）
docs/01-DNS是怎么工作的.md                   # 递归解析 / 加密 DNS / Fake IP / Egern 双轨模型
docs/02-DNS为什么会泄露.md                   # 5 个真实案例（每个：现象→机制→修法）
docs/03-加固清单-18项.md                     # 清单 + no_resolve 三层级 + 验收 6 条
docs/04-模板逐段讲解.md                      # 逐段讲模板，含「必须替换的清单」（v2.3 起只需 1 处）
docs/05-分流与no_resolve必须成对交付.md       # v7→v8 事故复盘
docs/06-实测数据与版本谱系.md                 # 端点实测表 / 污染实测表 / v1→v8 谱系
skill/                                       # 本 skill（含全部脚本）
```

> **可选版本只有两个** —— `v2.4`（推荐，完整分流）与 `v0`（极简懒人版）；
> 其余 `v2.x` / `v1` 都是 `v2.4` 的历代旧版，保留以备对照。

**要更新模板时**：**直接在仓库里改 `profiles/*.yaml` 即可。** 这份模板早已完成脱敏
（无节点、无订阅、无证书），改它不需要"从自用配置重新生成"。改完跑
`bash skill/tests/run.sh`（两阶段 24 断言）+ 下面那批审计脚本，再提交推送。

> 📦 **历史做法（已不再使用）**：早期由维护者本地的 `outputs/` 脚本链生成 ——
> `_build_public_template.py`（从自用版做**带断言的行级替换** + 38 个敏感串零残留自检）、
> `_transform_template.py`、`_make_min.py`（由带注释版生成纯配置版）、`_fetch_icons.py`、
> `_publish_to_github.py`（Git Data API 单次提交；空仓库需先落初始化提交，
> 否则 `POST /git/blobs` 报 `409 Git Repository is empty`）。
> ⚠️ 这些脚本**不在本仓库**（避免暴露构建侧私人路径）—— 2026-09-21 核查时**本机也已找不到**。
> 换句话说"不要手改仓库里的 yaml"这条老规矩**已作废**：现在的 `v2.1` / `v2.2` / `v2.3`
> 就是在仓库里直接改出来的。若将来要恢复"从自用配置生成"的流程，方法论见 skill
> `github-publish-sanitized-repo`，需按它重建脚本。

📌 **全部验证都在本地完成 —— 本仓库刻意不挂 CI / 任何自动化（2026-09-21 决定）。**
这是个人模板仓库，不会有外部贡献者，"自动验 PR"没有服务对象；而本地跑一次
`bash skill/tests/run.sh` + 5 个审计脚本只要几十秒。少一个对外暴露的面就少一份事。

⇒ 全部验证用本地命令复现：`bash skill/tests/run.sh` + `check_egern_dns.py` /
`audit_dns_forward.py` / `audit_ruleset_noresolve.py` / `audit_routing_coverage.py` /
`audit_region_filters.py`。
功能上没有任何损失。

**脱敏清单（这五类必须洗）**：节点 server/凭据/sni/reality 公钥 → 占位；
机场订阅 URL（含 token）→ 占位；`mitm.ca_p12` + `ca_passphrase`（个人 CA 私钥）→ **注释掉**；
机场组名/节点名 → `Airport-A` / `Node-1`；`dns.forward` 里的**节点域名** → `example-node.com`。
