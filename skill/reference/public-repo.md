# 公开模板仓库（本项目的对外交付物）

> 本文是 [`SKILL.md`](../SKILL.md) 的引用文件。 **何时读**：要更新模板 / 了解公开仓库结构时。

---

自用配置已脱敏发布为公开模板 + 文档 + 本 skill：

**https://github.com/RiverFlowsInUUU/Egern**

```
README.md                                   # 三条铁律 + 一图看懂回退链
profiles/lazy.yaml / lazy.min.yaml          # 懒人版 · 可选（4 组 / 9 条规则，Final 隐藏、AD 只留 REJECT；不挂版本号）
profiles/routing_v3.yaml / .min.yaml        # 分流版 · 推荐（脱敏模板：无节点、无订阅、无证书；机场槽位 1 个）
profiles/routing_v2.4.yaml / .min.yaml      # 保留（v3 前一版）
profiles/routing_v2.3.yaml / .min.yaml      # 保留（与 routing_v2.4 只差 rule_set 的 update_interval）
profiles/routing_v2.2.yaml / .min.yaml      # 保留（与 routing_v2.3 只差 4 处修正）
profiles/routing_v2.1.yaml / .min.yaml      # 保留（与 routing_v2.2 只差机场槽位：4 个 vs 2 个）
profiles/routing_v2.yaml / .min.yaml        # 保留原样（比 routing_v2.1 多 52 行「值等于默认值」的冗余行）
profiles/routing_v1.yaml / .min.yaml        # 分流线起点，保留不删（dns 段较冗长，功能等价）
CHANGELOG.md                                # 更新日志（按时间倒序，README 只留引用）
docs/01-DNS是怎么工作的.md                  # 递归解析 / 加密 DNS / Fake IP / Egern 双轨模型
docs/02-DNS为什么会泄露.md                  # 5 个真实案例（每个：现象→机制→修法）
docs/03-加固清单-18项.md                    # 清单 + no_resolve 三层级 + 验收 6 条
docs/04-模板逐段讲解.md                     # 逐段讲模板，含「必须替换的清单」（routing_v2.3 起只需 1 处）
docs/05-分流与no_resolve必须成对交付.md     # f7→f8 事故复盘
docs/06-实测数据与版本谱系.md               # 端点实测表 / 污染实测表 / f1→f8 谱系
docs/07-文件版本沿革.md                     # 两条线 + 分流版 routing_v1→v2.4 逐个说明（含四次改名记录）
docs/08-审计读数.md                         # 5 个审计脚本的读数 / 2 条 LOW 的含义 / 回归测试
docs/09-注意事项.md                         # 使用前必看：lazy 的 Proxy / 规则集刷新 / 刻意不挂 CI
docs/10-图标与许可.md                       # 图标来源 / MIT 许可 / 第三方版权
skill/                                      # 本 skill（含全部脚本）
```

> **可选版本只有两个** —— `routing_v3`（分流版 · 推荐）与 `lazy`（懒人版）；
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
> 换句话说"不要手改仓库里的 yaml"这条老规矩**已作废**：现在的 `routing_v2.1` / `routing_v2.2` / `routing_v2.3` / `routing_v2.4` / `routing_v3`
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

---

## README 只讲产品，不讲我们怎么改的

README 是**产品介绍** —— 读者要知道「这东西是什么、怎么用」。以下三类**不属于**它：

- 🚫 **归类 / 设计自述** —— 「某组为什么不算开关」「**上面是分类顺序**」这类解释我们怎么想的话。
- 🚫 **与评审 / 工单的对话** —— 「原写 X 属误标，已按功能拆开」。
- 🚫 **内部判据与断言名** —— 「由 `architecture.sh` ④ 断言守着」。

该放哪：**改动记录 → [`CHANGELOG.md`](../../CHANGELOG.md)；判据与原理 → [`DetailsReadme/`](../../DetailsReadme/DetailsReadme.md) 或 [`docs/`](../../docs/)。**

**自查**：README 里出现「为什么…」「不算」「误标」「判据」「原写」「上面是…顺序」，
八成就是改动记录漏出来了。**挪走，别只删** —— 判据必须仍能在 `DetailsReadme` 里查到。

同一事实要用**使用者视角的性质**表述：`不被规则引用`（内部判据）→ `独立于规则链路`（读者能懂）。

实测反例（2026-09-22）：在 README 里补「我们为什么这样归类 / 上面是分类顺序」这类说明，
用户一句打回 —— 「readme 是产品介绍，不是自说自话的地方」。

---

## 首页不列规则集

规则集属**实现侧**：用了哪些 `.list`、从哪个仓库拉、顺序怎么排。使用者关心的是**分流结果**。

| | 首页（`README.md`） | 组件页（`docs/`） |
|:--|:--|:--|
| 顺序表 | 「匹配什么 → 去向」（白名单 / 广告 / 按应用 / 国内…） | 逐条列出规则集名与参数 |
| 规则集清单 | ❌ 一个都不出现 | ✅ 文件名 · 去向 · 来源 URL |
| 来源仓库 | ❌ | ✅ 含图标、数据库、许可 |

**判据**：首页上这句话，对读者**用**这份配置有没有帮助？
「`OpenAI.list` → `ChatGPT`」没有意义 —— 使用者不能按规则集文件名分流；
「ChatGPT 走 `ChatGPT` 组，面板上可改道」才有意义。

实测（2026-09-22）：首页原挂着「📚 规则来源」段 + 「分流版的应用规则」表 + 「排序约束」，
用户连判两次 —— 先要求来源段下沉，随即补充：「不仅是规则集的来源，而且是有哪些规则集……
我认为都没必要放在首页的 README 里面。」处理后新开
[`docs/11-规则集与来源.md`](../../docs/11-规则集与来源.md) 承接全部规则集信息，
首页只在文件结构 / 更多文档里留一个链接。

闸门：`_base/verify_readme_tone.py` 的「首页无规则集文件与来源仓库」一项
（匹配 `*.list` / `*.txt` / `*.mmdb` / `*.mrs`、`GEOIP` / `GEOSITE`、来源仓库 owner）。
⚠️ 只对**配置模板仓**生效 —— `jinx` 本身是规则集仓，README 讲规则集是它的产品，不适用这条。
