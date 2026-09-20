#!/usr/bin/env bash
# Egern 审计脚本回归测试 —— 把 skill/tests/ 的 fixture 同时喂给两个脚本。
#
# 为什么需要它（2026-09-20 二次核查报告 P1 #3）：
#   此前 fixture 只手工喂给 check_egern_dns.py，audit_dns_forward.py 那一半从没跑过，
#   于是 `ok_route.yaml` 差一点就能抓到 `audit_dns_forward.py` 的 UnboundLocalError 崩溃。
#   ⇒ 把「N 个 fixture × 2 个脚本」串成一条命令，退出码非 0 即失败。
#
# 用法：
#   bash skill/tests/run.sh                       # 用 PATH 里的 python
#   PY=/path/to/python bash skill/tests/run.sh    # 指定解释器
#   在仓库根目录执行（脚本会自己定位 skill/tests/ 的上级）。

set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$(cd "$HERE/../scripts" && pwd)"
PY="${PY:-python3}"

# ⚠️ Git Bash / MSYS 下 `pwd` 返回 `/c/Users/...` 这种 MSYS 风格路径，
#    Windows 版 Python 打不开（会报 `can't open file 'C:\\c\\Users\\...'`）。
#    用 cygpath -w 转成 `C:\Users\...`；非 MSYS 环境（cygpath 不存在）保持原样。
if command -v cygpath >/dev/null 2>&1; then
  HERE_W="$(cygpath -w "$HERE")"
  SCRIPTS_W="$(cygpath -w "$SCRIPTS")"
else
  HERE_W="$HERE"
  SCRIPTS_W="$SCRIPTS"
fi

# 断言表：fixture 期望退出码（check_egern_dns / audit_dns_forward）
#   ok_route      : 判据 A 生效 -> 两脚本都应通过（0 / 0）
#   bad_foreign   : 兜底全境外 IP -> 两脚本都应判负（1 / 1）
#   bad_hostname  : 兜底含主机名   -> 两脚本都应判负（1 / 1）
#   ipv6_only     : 端点仅 IPv6 国内解析器 -> 两脚本必须**同结论**且都通过（0 / 0）
#                   （这是 ep_ip IPv6 截断 bug 的守卫：修之前是 0 / 1）
CASES="
ok_route.yaml:0:0
bad_foreign.yaml:1:1
bad_hostname.yaml:1:1
ipv6_only.yaml:0:0
"

pass=0; fail=0
printf '%-22s %-18s %-20s %s\n' "FIXTURE" "check_egern_dns" "audit_dns_forward" "RESULT"
printf '%s\n' "--------------------------------------------------------------------------------"

for case in $CASES; do
  f="${case%%:*}"; rest="${case#*:}"
  exp_chk="${rest%%:*}"; exp_adf="${rest##*:}"
  path="$HERE/$f"
  path_w="$HERE_W\\$f"
  [ -f "$path" ] || { printf '%-22s %s\n' "$f" "❌ fixture 缺失"; fail=$((fail+1)); continue; }

  "$PY" "$SCRIPTS_W\\check_egern_dns.py" "$path_w" >/dev/null 2>&1; got_chk=$?
  "$PY" "$SCRIPTS_W\\audit_dns_forward.py" "$path_w" >/dev/null 2>&1; got_adf=$?

  if [ "$got_chk" = "$exp_chk" ] && [ "$got_adf" = "$exp_adf" ]; then
    res="✅ OK"; pass=$((pass+1))
  else
    res="❌ 期望 ${exp_chk}/${exp_adf}"; fail=$((fail+1))
  fi
  printf '%-22s %-18s %-20s %s\n' "$f" "exit=$got_chk" "exit=$got_adf" "$res"
done

printf '%s\n' "--------------------------------------------------------------------------------"
printf 'result: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" = "0" ] || exit 1
exit 0
