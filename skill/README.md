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
| `SKILL.md` | 方法论主体：Egern 双轨 DNS 模型、**17 项审计清单**、加固模板、**17 个已踩过的坑**、验收 6 条、官方文档入口 |
| `scripts/check_egern_dns.py` | **profile 层审计**（清单 1–15）。检查端点是否 IP 字面量、兜底组是否"直连可达"、IP 规则是否带 `no_resolve`、策略名能否解析、死规则等 |
| `scripts/audit_ruleset_noresolve.py` | **规则集层审计**（清单 16）。下载全部被引用的远程规则集，数出"缺 `no-resolve` 的 IP 条目" |
| `scripts/audit_routing_coverage.py` | **分流覆盖审计**（清单 17）。域名 → 命中规则 → 策略；15 个**非 `.cn`** 国内探针 + 7 个境外探针 |
| `scripts/profile_ruleset.py` | 规则集类型分布（识破"名字骗人"，例如 `ChinaMax.list` 其实 98.6% 是 IP） |
| `scripts/probe_dns_endpoints.py` | 逐个实测加密 DNS 端点（DoH 线格式 / DoT 853 握手 + 证书） |
| `scripts/probe_doh.py` | 只测 DoH 线格式（判端点死活**只能**用这个，不能用 JSON API） |

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
python "$S/profile_ruleset.py"            ChinaMax.list         # 规则集类型分布
python "$S/probe_dns_endpoints.py"        Profile.yaml          # 端点实测
```

退出码 **0 = 通过**，可直接接进 CI 或提交前检查。
规则集缓存写在系统临时目录（`%TEMP%\egern-ruleset-cache` / `/tmp/egern-ruleset-cache`），约 5 MB。

## 三条必须记住的判据

1. **兜底组的唯一判据是「直连可达」**（端点全为 IP 字面量 + 至少一个在 `rules` 里判给 `DIRECT`），**不是**「指向国内还是境外」。
2. **判据是「数域名条目」，不是看规则集名字，也不是看 README 标题。**
3. **审计通过 ≠ 配置可用。** 本项目连续 5 次出现"脚本全绿、实测仍有问题" —— 每次都要假设"存在审计器看不见的维度"，并把它补成可复跑脚本。
