# -*- coding: utf-8 -*-
"""Egern 审计脚本的共享工具 —— 消灭「同一判据两份拷贝」。

背景（2026-09-20，二次核查报告 P1）：
  `check_egern_dns.py` 与 `audit_dns_forward.py` 各自实现了一份「端点主机名解析 +
  是否为 IP 字面量 + 国内知名解析器白名单」的逻辑，靠注释互相提醒同步。
  结果：判据本体同步了，**喂给判据的 helper 没同步** ——
  `audit_dns_forward.ep_ip('https://[2400:3200::1]/dns-query')` 返回被截断的 `'[2400:3200:'`，
  而 `check_egern_dns.hostpart()` 正确返回 `'2400:3200::1'`。
  ⇒ 同一份配置，两个脚本给出**相反结论**。

  结论：**靠注释提醒同步两份拷贝是不可靠的。** 本模块把这些共用逻辑收编到一处，
  两个脚本都从这里 import，从结构上消灭拷贝。

后续修正（2026-09-20，三次核查报告 P2）：
  「收编」这一次动作本身引入了新回归 —— `hostpart()` 剥 scheme 从「通用剥离」
  退化成「大小写敏感白名单」，于是 `HTTPS://223.5.5.5/dns-query` 被解析出主机名
  `HTTPS`，端点从 IP 字面量误判成待解析域名，同一份配置读数从 0 high 翻成 9 high。
  已改回大小写不敏感的通用正则，并由 `tests/scheme_case.yaml` 守卫生效。

用法：
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _egern_common import DOMESTIC_RESOLVER_IPS, ep_ip, ip_literal, hostpart
"""

import re

# ⭐ 国内知名公共 DNS 解析器 IP —— 「兜底组直连可达」的第二判据。
# 在 profile 文本内无法证明任意 IP 是否可直连，但这些 IP 的归属与服务商是公开事实，
# 且在国内任何链路上都直连可达 —— 与「在 rules 里判给 DIRECT」等价，且不需要
# 配置里额外写装饰性规则。
# ⚠️ 只收「国内」解析器：境外解析器（8.8.8.8 等）必须经代理才可达，一个全由境外 IP
# 组成的组即便端点全是 IP 字面量也**不能**判为直连可达（f5 的真实踩坑）。
DOMESTIC_RESOLVER_IPS = {
    # 阿里 AliDNS
    "223.5.5.5", "223.6.6.6", "2400:3200::1", "2400:3200:baba::1",
    # 腾讯 DNSPod
    "119.29.29.29", "119.28.28.28", "2402:4e00::",
    # DNSPod 备用 / 其他国内公共解析器
    "182.254.116.116", "1.12.12.12", "120.53.53.53", "120.53.53.54",
    # 114DNS
    "114.114.114.114", "114.114.115.115",
    # 百度
    "180.76.76.76",
    # 360
    "101.226.4.6", "218.30.118.6", "123.125.81.6", "140.205.1.1",
    # 中国电信 / 联通 / 移动 常见递归（非必须，仅作识别）
    "1.2.4.8", "210.2.4.8",
}

_IP4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

# ⭐ 通用 scheme 前缀：`scheme://`，**大小写不敏感**，不枚举具体 scheme。
# ⚠️ 不要改成白名单（`("https://", "tls://", ...)`）：那会让 scheme 的拼法参与
#    审计结论。三次核查报告 P2 的回归正是如此 —— 端点写 `HTTPS://223.5.5.5/dns-query`
#    时，白名单失配，`HTTPS` 被当成主机名，端点从「IP 字面量」误判成「待解析域名」，
#    同一份配置的读数从 0 high 翻成 9 high。scheme 拼法不是本工具要审的对象。
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")


def hostpart(ep):
    """从端点字符串里取出主机部分（去 scheme、去 path/query、去 :port）。

    正确处理这些形态（scheme 拼法任意、大小写任意）：
      - `https://223.5.5.5/dns-query`      -> `223.5.5.5`
      - `HTTPS://223.5.5.5/dns-query`      -> `223.5.5.5`
      - `dot://223.6.6.6`                  -> `223.6.6.6`
      - `https://[2400:3200::1]/dns-query` -> `2400:3200::1`   ← IPv6（方括号）
      - `[2400:3200::1]:443`               -> `2400:3200::1`
      - `tls://223.5.5.5:853`              -> `223.5.5.5`
      - `dns.google` / `2001:db8::1`       -> 原样
    """
    s = str(ep).strip()
    m = _SCHEME_RE.match(s)
    if m:
        s = s[m.end():]
    s = s.split("/")[0]                        # 去 path
    s = s.split("?")[0].split("#")[0]          # 去 query / fragment
    if s.startswith("["):                      # IPv6 带方括号
        end = s.find("]")
        return s[1:end] if end != -1 else s.lstrip("[")
    if s.count(":") == 1:                      # host:port（IPv4 或域名）
        return s.split(":")[0]
    return s                                   # 裸 IPv4 / 裸 IPv6 / 域名


def ip_literal(ep):
    """端点是不是 IP 字面量（不需要任何解析）。"""
    host = hostpart(ep)
    if _IP4_RE.match(host):
        return True
    return ":" in host                         # IPv6 字面量


# 兼容旧调用名（audit_dns_forward.py 历史上用的是 ep_ip）
ep_ip = hostpart
