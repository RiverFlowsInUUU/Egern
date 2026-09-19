#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
逐个实测 Egern profile 里声明的每个加密 DNS 端点，确认它真的能用。

为什么需要它（本轮真实教训）：
  「把端点写成 IP 字面量」是为了消灭 bootstrap 的用途①（官方：bootstrap 会用来
  解析 upstreams 中加密 DNS 服务器的主机名）。但**写成 IP 之后证书不一定覆盖该 IP**，
  写错形式就白占一个端点，而且是**静默失效** —— 配置校验不会报错。
  实测反例：https://9.9.9.9/dns-query 直接 `HTTP Version Not Supported`
  （Quad9 在 9.9.9.9 上只提供 HTTP/3，不响应 RFC8484 的 HTTP/1.1 线格式），
  但 tls://9.9.9.9 正常（证书 CN=dns.quad9.net）。

用法：
  python probe_dns_endpoints.py profile.yaml          # 从 profile 里抽出所有 dns 端点
  python probe_dns_endpoints.py 8.8.8.8 1.1.1.1      # 或直接给端点/主机
  python probe_dns_endpoints.py tls://9.9.9.9

覆盖协议：udp:// / 裸 IP（传统 UDP:53）、tls://（DoT 853）、https://（DoH，RFC8484 线格式）。
不做 JSON API 判断（见 SKILL 坑 1）。
"""
import base64
import socket
import ssl
import struct
import sys
import urllib.request

TIMEOUT = 12
QNAME = "example.com"


# ---------------------------------------------------------------- DNS 报文
def build_query(name=QNAME, qtype=1, rd=True):
    flags = 0x0100 if rd else 0x0000
    head = struct.pack(">HHHHHH", 0x1234, flags, 1, 0, 0, 0)
    body = b"".join(bytes([len(p)]) + p.encode() for p in name.split("."))
    return head + body + b"\x00" + struct.pack(">HH", qtype, 1)


def parse_answers(buf):
    """返回 [(type, 值)]；只解 A / AAAA / CNAME。"""
    out, i = [], 12
    if len(buf) < 12:
        return out
    qd, an = struct.unpack(">HH", buf[4:8])
    for _ in range(qd):
        while buf[i]:
            i += buf[i] + 1
        i += 5
    for _ in range(an):
        if buf[i] & 0xC0 == 0xC0:
            i += 2
        else:
            while buf[i]:
                i += buf[i] + 1
            i += 1
        rtype, _cls, _ttl, dl = struct.unpack(">HHIH", buf[i:i + 10])
        i += 10
        data = buf[i:i + dl]
        i += dl
        if rtype == 1 and dl == 4:
            out.append(("A", socket.inet_ntoa(data)))
        elif rtype == 28 and dl == 16:
            out.append(("AAAA", socket.inet_ntop(socket.AF_INET6, data)))
        elif rtype == 5:
            # CNAME：可能是压缩指针，简单跳过
            out.append(("CNAME", "<见应答>"))
    return out


# ---------------------------------------------------------------- 各协议
def hostport(s):
    """'tls://8.8.8.8:853' -> ('8.8.8.8', 853, 'tls')"""
    proto, rest = (s.split("://", 1) + [""])[:2] if "://" in s else ("udp", s)
    rest = rest.split("/")[0]
    if ":" in rest:
        h, p = rest.rsplit(":", 1)
        return proto, h, int(p)
    return proto, rest, {"udp": 53, "tls": 853, "https": 443}.get(proto, 53)


def try_udp(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(TIMEOUT)
    s.sendto(build_query(), (host, port))
    # 跳过发往本机的 ICMP 导致的假连接（UDP 无连接，直接看是否有回包）
    data, _ = s.recvfrom(4096)
    return parse_answers(data)


def try_dot(host, port, server_hostname=None):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=TIMEOUT) as raw:
        with ctx.wrap_socket(raw, server_hostname=server_hostname or host) as ts:
            m = build_query()
            ts.sendall(struct.pack(">H", len(m)) + m)
            ln = struct.unpack(">H", ts.recv(2))[0]
            buf = b""
            while len(buf) < ln:
                buf += ts.recv(ln - len(buf))
            cn = dict(x[0] for x in ts.getpeercert().get("subject", ())).get("commonName", "?")
            return parse_answers(buf), cn


def try_doh(host, port, path="/dns-query", server_hostname=None):
    """RFC 8484 线格式：GET ?dns=<base64url> + accept: application/dns-message"""
    enc = base64.urlsafe_b64encode(build_query()).rstrip(b"=").decode()
    url = f"https://{host}:{port}{path}?dns={enc}"
    req = urllib.request.Request(url, headers={"accept": "application/dns-message"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status, parse_answers(r.read())


# ---------------------------------------------------------------- 入口
def endpoints_from_profile(path):
    try:
        import yaml
    except ImportError:
        sys.exit("需要 pyyaml 才能读 profile；或直接把端点作为参数传入")
    doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
    dns = doc.get("dns") or {}
    out = []
    for grp, servers in (dns.get("upstreams") or {}).items():
        for s in servers or []:
            out.append((f"upstream {grp}", str(s)))
    for s in dns.get("proxy_nameservers") or []:
        out.append(("proxy_nameservers", str(s)))
    for r in dns.get("forward") or []:
        for b in r.values():
            v = str((b or {}).get("value") or "")
            if "://" in v and v not in [x[1] for x in out]:
                out.append(("forward 内联端点", v))
    for s in dns.get("bootstrap") or []:
        out.append(("bootstrap（明文 UDP）", str(s)))
    return out


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    items = []
    for a in args:
        if a.endswith((".yaml", ".yml")):
            items += endpoints_from_profile(a)
        else:
            items.append(("CLI", a))

    print("%-22s %-38s %-10s %s" % ("来源", "端点", "结果", "应答 / 说明"))
    print("-" * 112)
    bad = 0
    for where, s in items:
        proto, host, port = hostport(s)
        try:
            if proto == "https":
                st, ans = try_doh(host, port)
                res = f"HTTP {st}"
                detail = ans or "（无 A 记录）"
            elif proto == "tls":
                ans, cn = try_dot(host, port)
                res = "OK"
                detail = f"cert CN={cn}  {ans}"
            else:
                ans = try_udp(host, port)
                res = "OK"
                detail = f"{ans}  ⚠️ 明文 UDP:53"
            print("%-22s %-38s %-10s %s" % (where, s, res, detail))
        except Exception as e:
            bad += 1
            m = str(getattr(e, "reason", e)).replace("\n", " ")[:56]
            print("%-22s %-38s %-10s %s" % (where, s, "FAIL", m))
    print()
    print(f"失效端点：{bad} / {len(items)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
