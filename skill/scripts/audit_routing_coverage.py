#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审计 Egern profile 的**分流覆盖**：给一批域名，看它们按规则顺序实际会落到哪条规则、哪个策略。

为什么必须有这个脚本
--------------------
`check_egern_dns.py` 只看 DNS 面，`audit_ruleset_noresolve.py` 只看"会不会强制解析"。
两者都看不见**路由本身对不对**。本项目第三类事故（2026-09-19 v8）正是栽在这里：

    v7 给 `geoip: CN` 加 `no_resolve: true` 治好了 DNS 泄露（官方语义：不再触发解析），
    但这同时让 geoip **不再匹配域名** —— 而那条 geoip 恰恰是原配置里
    "国内域名走直连"的唯一机制（收到域名 → 强制解析 → 判出 CN IP → DIRECT）。
    本该补位的 ChinaMax 规则兜不住：按 blackmatrix7 自己的 README，
    `ChinaMax.list` 只是 **IP 规则集**（实测 12614 条里 12472 条 IP-CIDR，域名只有 64 条），
    域名规则在同目录的 `ChinaMax_Domain.list` 里，两条"共同使用"。
    ⇒ 现象：「ChinaMax 里基本只有一些 IP 走直连，国内域名基本都走 final」。

结论：**修 DNS 泄露的动作会悄悄改掉分流**。凡是动了 `no_resolve` 或替换了规则集，
都必须复跑本脚本，对一批真实域名验证"命中规则 + 策略"。

用法
----
    python audit_routing_coverage.py profile.yaml
    python audit_routing_coverage.py profile.yaml --domain www.baidu.com --domain x.com
    python audit_routing_coverage.py profile.yaml --offline      # 只用规则集缓存

内置默认探针域名分两类（国内 / 境外），零命中率会直接暴露"国内域名整片落 default"。

退出码：0 = 所有国内探针都命中 DIRECT 类策略；1 = 有国内探针落到代理/兜底。
"""
import argparse
import io
import os
import re
import sys
import tempfile
import urllib.request
from fnmatch import fnmatch

try:
    import yaml
except ImportError:
    print("需要 PyYAML：<venv>/Scripts/python -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)

CACHE = os.path.join(tempfile.gettempdir(), "egern-ruleset-cache")

# 国内探针：全部是 .com/.net 等**不以 .cn 结尾**的常见站，专门用来暴露
# 「.cn 兜底掩盖了国内域名无覆盖」这种假象。
CN_PROBES = [
    "www.baidu.com", "www.taobao.com", "www.jd.com", "www.bilibili.com",
    "www.zhihu.com", "weibo.com", "www.163.com", "www.qq.com",
    "www.douyin.com", "www.iqiyi.com", "www.meituan.com", "www.xiaohongshu.com",
    "www.alipay.com", "www.12306.cn", "www.gov.cn",
]
FOREIGN_PROBES = [
    "www.google.com", "www.youtube.com", "github.com", "x.com",
    "api.openai.com", "www.netflix.com", "www.wikipedia.org",
]
DOMAIN_TYPES = ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-REGEX", "DOMAIN-WILDCARD")


def fetch(url, offline=False):
    os.makedirs(CACHE, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", url.rstrip("/").split("/")[-1]) or "ruleset"
    path = os.path.join(CACHE, name)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return io.open(path, encoding="utf-8", errors="replace").read()
    if offline:
        return None
    req = urllib.request.Request(url, headers={"User-Agent": "egern-routing-audit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = r.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None
    io.open(path, "w", encoding="utf-8", newline="\n").write(body)
    return body


def rule_set_domains(url, offline=False):
    """把远程规则集解析成 [(类型, 值)]，只保留域名类条目；返回 (域名条目, IP类条目, 缺no-resolve数)"""
    body = fetch(url, offline)
    if body is None:
        return None
    doms, ip, missing = [], 0, 0
    for raw in body.split("\n"):
        l = raw.strip()
        if not l or l.startswith(("#", "//", ";")):
            continue
        if l.startswith("- "):          # Clash YAML payload
            l = l[2:].strip().strip("'\"")
        if "," not in l and l.startswith("."):    # 裸域名（QuantumultX / Egern 写法）
            l = "DOMAIN-SUFFIX," + l.lstrip(".")
        parts = [p.strip() for p in l.split(",")]
        t = parts[0].upper()
        if t in DOMAIN_TYPES:
            doms.append((t, parts[1] if len(parts) > 1 else ""))
        elif t.startswith("IP-") or t in ("GEOIP",):
            ip += 1
            if "no-resolve" not in l.lower():
                missing += 1
    return doms, ip, missing


def dom_match(t, pat, host):
    host = host.lower()
    pat = pat.lower()
    if not pat:
        return False
    if t == "DOMAIN":
        return host == pat
    if t == "DOMAIN-SUFFIX":
        p = pat.lstrip("*.")
        return host == p or host.endswith("." + p)
    if t == "DOMAIN-KEYWORD":
        return pat in host
    if t == "DOMAIN-REGEX":
        try:
            return re.search(pat, host) is not None
        except re.error:
            return False
    if t == "DOMAIN-WILDCARD":
        return fnmatch(host, pat)
    return False


def first_hit(doc, host, sets_cache, offline):
    """按 Egern 语义走一遍 rules，返回 (序号, 规则描述, 策略) 或 (None,'无','-')"""
    rules = doc.get("rules") or []
    for i, r in enumerate(rules):
        if not isinstance(r, dict):
            continue
        for t, b in r.items():
            if not isinstance(b, dict):
                continue
            if b.get("disabled"):
                continue
            if t == "default":
                return i, "default(兜底)", b.get("policy")
            m = str(b.get("match") or "")
            if t in ("domain", "domain_suffix", "domain_keyword", "domain_regex", "domain_wildcard"):
                if dom_match({"domain": "DOMAIN", "domain_suffix": "DOMAIN-SUFFIX",
                              "domain_keyword": "DOMAIN-KEYWORD", "domain_regex": "DOMAIN-REGEX",
                              "domain_wildcard": "DOMAIN-WILDCARD"}[t], m, host):
                    return i, f"{t}:{m}", b.get("policy")
            elif t in ("rule_set", "proxy_rule_set") and m.startswith("http"):
                if m not in sets_cache:
                    sets_cache[m] = rule_set_domains(m, offline)
                got = sets_cache[m]
                if got:
                    for dt, dv in got[0]:
                        if dom_match(dt, dv, host):
                            return i, f"rule_set({m.rstrip('/').split('/')[-1]}):{dv}", b.get("policy")
    return None, "无", "-"


def main():
    ap = argparse.ArgumentParser(description="审计 Egern profile 的分流覆盖（域名 → 命中规则 → 策略）")
    ap.add_argument("profile")
    ap.add_argument("--domain", action="append", default=[], help="追加探针域名，可重复")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()

    doc = yaml.safe_load(io.open(a.profile, encoding="utf-8"))
    cache = {}

    # ---- 先盘一遍启用的 DIRECT 规则集里到底有多少域名条目（ChinaMax 那类坑）----
    print("=" * 100)
    print("【一】启用的 rule_set 的域名/IP 构成（DIRECT 规则集域名条目≈0 ⇒ 兜不住国内域名）")
    print("-" * 100)
    print(f"{'规则集':40s} {'策略':10s} {'域名条目':>9s} {'IP条目':>8s} {'缺no-resolve':>13s}")
    direct_domains = 0
    for i, r in enumerate(doc.get("rules") or []):
        if not isinstance(r, dict):
            continue
        for t, b in r.items():
            if t != "rule_set" or not isinstance(b, dict):
                continue
            m = str(b.get("match") or "")
            if not m.startswith("http"):
                continue
            if b.get("disabled"):
                continue
            got = rule_set_domains(m, a.offline)
            name = m.rstrip("/").split("/")[-1] or m
            if got is None:
                print(f"{name:40s} {'取失败':10s} {'-':>9s} {'-':>8s} {'-':>13s}")
                continue
            doms, ipn, miss = got
            pol = str(b.get("policy"))
            print(f"{name:40s} {pol:10s} {len(doms):>9d} {ipn:>8d} {miss:>13d}")
            if pol.upper() == "DIRECT":
                direct_domains += len(doms)

    # ---- 再逐个探针域名走规则 ----
    probes = [("CN", h) for h in CN_PROBES] \
        + [("  ", d) for d in a.domain if d not in CN_PROBES] \
        + [("  ", h) for h in FOREIGN_PROBES if h not in CN_PROBES and h not in a.domain]
    print()
    print("=" * 100)
    print("【二】探针域名实际命中的规则（按 rules 顺序，首次命中即止）")
    print("-" * 100)
    print(f"{'类':3s} {'域名':30s} {'序':>3s} {'命中规则':52s} {'策略'}")
    bad, wrong_direct = [], []
    for kind, h in probes:
        idx, desc, pol = first_hit(doc, h, cache, a.offline)
        print(f"{kind:3s} {h:30s} {('' if idx is None else idx):>3} {desc:52s} {pol}")
        if kind == "CN" and str(pol).upper() != "DIRECT":
            bad.append((h, desc, pol))
        if h in FOREIGN_PROBES and str(pol).upper() == "DIRECT":
            wrong_direct.append((h, desc, pol))

    print()
    print("=" * 100)
    print(f"启用的 DIRECT 规则集域名条目合计: {direct_domains}")
    if wrong_direct:
        print(f"注意 —— {len(wrong_direct)} 个境外探针被判给了 DIRECT（规则集覆盖过宽，需人工确认）：")
        for h, d, p in wrong_direct:
            print(f"  * {h:28s} -> {d}  (policy={p})")
        print()
    if bad:
        print(f"HIGH —— {len(bad)}/{len(CN_PROBES)} 个国内探针未被判给 DIRECT：")
        for h, d, p in bad:
            print(f"  * {h:28s} -> {d}  (policy={p})")
        print()
        print("诊断要点：国内域名整片落到 default/Final，通常是这两种原因之一 ——")
        print("  1) 那条 'geoip: CN' 带了 no_resolve（治 DNS 泄露的常规动作）⇒ geoip 不再匹配域名，")
        print("     而它原本正是国内域名走直连的唯一机制（靠强制解析判出 CN IP）。")
        print("  2) 用来补位的 DIRECT 规则集其实**不含域名规则**。著名例子：blackmatrix7 的")
        print("     `ChinaMax.list` 按仓库 README 只是 IP 规则集（实测 12472 IP / 64 域名），")
        print("     域名在 `ChinaMax_Domain.list` 里，两条需'共同使用'；")
        print("     直接换成 `ChinaMax_All_No_Resolve.list`（111k 域名 + 同份 IP，且全带 no-resolve）最省事。")
        return 1
    print(f"OK —— {len(CN_PROBES)} 个国内探针全部命中 DIRECT。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
