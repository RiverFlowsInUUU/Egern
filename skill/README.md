# skill · egern-profile-dns-hardening

给 AI Agent 用的**审计方法论 + 可复跑脚本**。也可以纯手工用（每个脚本都能独立跑）。

## 安装

```bash
# 拷到 Agent skills 目录（以 WorkBuddy 为例）
cp -r skill ~/.workbuddy/skills/egern-profile-dns-hardening
```

之后对话里提到「Egern 配置」「DNS 泄露」「上游显示 bootstrap」「规则集缺 no-resolve」等，Agent 会自动加载。

## 内容

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 方法论主体：Egern 双轨 DNS 模型、**18 项审计清单**、加固模板、**18 个已踩过的坑**、验收 7 条、官方文档入口 |
| `scripts/check_egern_dns.py` | **profile 层审计**（清单 1–15）。检查端点是否 IP 字面量、兜底组是否"直连可达"、IP 规则是否带 `no_resolve`、策略名能否解析、死规则等 |
| `scripts/audit_ruleset_noresolve.py` | **规则集层审计**（清单 16）。下载全部被引用的远程规则集，数出"缺 `no-resolve` 的 IP 条目" |
| `scripts/audit_routing_coverage.py` | **分流覆盖审计**（清单 17）。域名 → 命中规则 → 策略；15 个**非 `.cn`** 国内探针 + 7 个境外探针 |
| `scripts/audit_dns_forward.py` | **forward 单值性 / 订阅耦合审计**（清单 18）。判断 `forward` 的 value 是否单值、有没有把节点域名写死、`--drill` 用合成"未来订阅"域名演练 |
| `scripts/audit_region_filters.py` | **地区组 filter 同步审计**。6 个地区组的关键词是「两份拷贝」（各自一份 + `Other Regions` 负向断言里一份），漏同步会让两组不再互斥；本脚本逐字比对，缺项即报错 |
| `scripts/profile_ruleset.py` | 规则集类型分布（识破"名字骗人"，例如 `ChinaMax.list` 其实 98.6% 是 IP） |
| `scripts/probe_dns_endpoints.py` | 逐个实测加密 DNS 端点（DoH 线格式 / DoT 853 握手 + 证书） |
| `scripts/probe_doh.py` | 只测 DoH 线格式（判端点死活**只能**用这个，不能用 JSON API） |
| `scripts/weigh_ruleset.py` | 规则集"重量"：构成 / 冗余 / 深度 / 耗时 / 覆盖对比（评估大规则集的内存与加载代价） |

## 依赖

Python 3.8+ 与 `PyYAML`：

```bash
pip install pyyaml
```

## 用法

```bash
S=./skill/scripts

python "$S/check_egern_dns.py"            Profile.yaml          # 期望 0 high
python "$S/audit_ruleset_noresolve.py"    Profile.yaml          # 期望 OK
python "$S/audit_routing_coverage.py"     Profile.yaml          # 期望 15/15 DIRECT
python "$S/audit_dns_forward.py"           Profile.yaml          # 期望 通过（forward 与订阅解耦）
                                                                 # --drill 可选（加演练域名），不加也应通过
python "$S/audit_region_filters.py"       Profile.yaml          # 期望 地区组关键词全部同步（v0 无此结构，自动跳过）
python "$S/profile_ruleset.py"            ChinaMax.list         # 规则集类型分布
python "$S/probe_dns_endpoints.py"        Profile.yaml          # 端点实测

bash ./skill/tests/run.sh                                       # 回归测试两阶段，共 22 断言
```

退出码 **0 = 通过**，用于提交前检查（本仓库**不挂 CI**，全部本地手动跑）。
规则集缓存写在系统临时目录（`%TEMP%\egern-ruleset-cache` / `/tmp/egern-ruleset-cache`），约 5 MB。

> `tests/run.sh` 是**防退化守卫**，分两阶段：
> **阶段 1** 把 `tests/` 下的 fixture 同时喂给 `check_egern_dns.py` 与 `audit_dns_forward.py`
> （5 × 2 = 10 断言），确保两个脚本对同一份配置给出一致结论；
> **阶段 2** 对仓库里全部 12 份 `profiles/*.yaml` 跑 `audit_region_filters.py`（12 断言），
> 守住地区组关键词与 `Other Regions` 负向断言的同步。
> ⚠️ 阶段 2 的断言对象必须是**真实 profile** —— `tests/` 的 fixture 是 DNS 面的合成配置、
> 没有地区组，喂给 `audit_region_filters.py` 只会走"无需校验"分支（看着绿，其实没测）。
> **改完脚本或 profile 后手动跑一次。**
> 共享逻辑（`hostpart` / `ip_literal` / `DOMESTIC_RESOLVER_IPS`）集中在 `scripts/_egern_common.py`，
> 避免"同一判据两份拷贝、改一处漏另一处"。两个脚本的运行目录里必须有这个文件。
>
> 📌 **全部验证都在本地完成 —— 本仓库刻意不挂 CI / 任何自动化**（2026-09-21 决定）。
> 这是个人模板仓库，不会有外部贡献者，"自动验 PR"价值接近于零，而本地跑一次只要几十秒；
> 少一个对外暴露的面就少一份事。
> 全部验证用上面的本地命令即可完整复现，功能上没有任何损失。

## 三条必须记住的判据

1. **兜底组的唯一判据是「直连可达」**（端点全为 IP 字面量，**且**至少一个在 `rules` 里判给 `DIRECT`、**或**至少一个是已知的国内解析器 IP），**不是**「指向国内还是境外」。
2. **判据是「数域名条目」，不是看规则集名字，也不是看 README 标题。**
3. **审计通过 ≠ 配置可用。** 本项目连续 5 次出现"脚本全绿、实测仍有问题" —— 每次都要假设"存在审计器看不见的维度"，并把它补成可复跑脚本。
