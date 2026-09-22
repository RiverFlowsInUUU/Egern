# 公开模板仓库（本项目的对外交付物）

> 本文是 [`SKILL.md`](../SKILL.md) 的引用文件。 **何时读**：要更新模板 / 了解公开仓库结构时。

---

自用配置已脱敏发布为公开模板 + 文档 + 本 skill：

**https://github.com/RiverFlowsInUUU/egern-anti-dns-leak**

```
README.md                                   # 三条铁律 + 一图看懂回退链
profiles/lazy.yaml / lazy.min.yaml          # 懒人版 · 可选（4 组 / 9 条规则，Final 隐藏、AD 只留 REJECT；不挂版本号）
profiles/routing_v2.5.yaml / .min.yaml      # 分流版 · 推荐（脱敏模板：无节点、无订阅、无证书；机场槽位 2 个）
profiles/routing_v2.4.yaml / .min.yaml      # 保留（与 routing_v2.5 只差广告规则集地址）
profiles/routing_v2.3.yaml / .min.yaml      # 保留（与 routing_v2.4 只差 rule_set 的 update_interval）
profiles/routing_v2.2.yaml / .min.yaml      # 保留（与 routing_v2.3 只差 4 处修正）
profiles/routing_v2.1.yaml / .min.yaml      # 保留（与 routing_v2.2 只差机场槽位：4 个 vs 2 个）
profiles/routing_v2.yaml / .min.yaml        # 保留原样（比 routing_v2.1 多 52 行「值等于默认值」的冗余行）
profiles/routing_v1.yaml / .min.yaml        # 分流线起点，保留不删（dns 段较冗长，功能等价）
profiles/lazy.yaml / lazy.min.yaml          # 懒人配置 · 可选（4 组 / 9 条规则，Final 隐藏、AD 只留 REJECT）
CHANGELOG.md                                # 更新日志（按时间倒序，README 只留引用）
docs/01-DNS是怎么工作的.md                  # 递归解析 / 加密 DNS / Fake IP / Egern 双轨模型
docs/02-DNS为什么会泄露.md                  # 5 个真实案例（每个：现象→机制→修法）
docs/03-加固清单-18项.md                    # 清单 + no_resolve 三层级 + 验收 6 条
docs/04-模板逐段讲解.md                     # 逐段讲模板，含「必须替换的清单」（routing_v2.3 起只需 1 处）
docs/05-分流与no_resolve必须成对交付.md     # f7→f8 事故复盘
docs/06-实测数据与版本谱系.md               # 端点实测表 / 污染实测表 / f1→f8 谱系
docs/07-文件版本沿革.md                     # 两条线 + 分流版 routing_v1→v2.5 逐个说明（含三次改名记录）
docs/08-审计读数.md                         # 5 个审计脚本的读数 / 2 条 LOW 的含义 / 回归测试
docs/09-注意事项.md                         # 使用前必看：lazy 的 Proxy / 规则集刷新 / 刻意不挂 CI
docs/10-图标与许可.md                       # 图标来源 / MIT 许可 / 第三方版权
skill/                                      # 本 skill（含全部脚本）
```

> **可选版本只有两个** —— `routing_v2.5`（分流版 · 推荐）与 `lazy`（懒人版）；
> 其余 `routing_v2.x` / `routing_v1` 都是分流线的历代旧版，保留以备对照。

**要更新模板时**：**直接在仓库里改 `profiles/*.yaml` 即可。** 这份模板早已完成脱敏
（无节点、无订阅、无证书），改它不需要"从自用配置重新生成"。改完跑
`bash skill/tests/run.sh`（两阶段 26 断言）+ 下面那批审计脚本，再提交推送。

> 📦 **历史做法（已不再使用）**：早期由维护者本地的 `outputs/` 脚本链生成 ——
> `_build_public_template.py`（从自用版做**带断言的行级替换** + 38 个敏感串零残留自检）、
> `_transform_template.py`、`_make_min.py`（由带注释版生成纯配置版）、`_fetch_icons.py`、
> `_publish_to_github.py`（Git Data API 单次提交；空仓库需先落初始化提交，
> 否则 `POST /git/blobs` 报 `409 Git Repository is empty`）。
> ⚠️ 这些脚本**不在本仓库**（避免暴露构建侧私人路径）—— 2026-09-21 核查时**本机也已找不到**。
> 换句话说"不要手改仓库里的 yaml"这条老规矩**已作废**：现在的 `routing_v2.1` / `routing_v2.2` / `routing_v2.3`
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
