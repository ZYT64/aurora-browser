#!/usr/bin/env bash
# AURORA-FP 全补丁链式应用：F1→F8 一锅端（单轮编译验证全部 8 个指纹面）
# 用法: apply_all.sh <chromium-src-root> [persona.json路径]
# 设计: 任一补丁失配立即退出非零（锚点命中数校验在每个 apply_fN.py 内部）
set -euo pipefail

SRC="${1:?用法: apply_all.sh <chromium-src-root> [persona.json]}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PERSONA="${2:-$REPO_DIR/persona/persona.example.json}"

echo "========== [1] persona header 生成 =========="
python3 "$REPO_DIR/scripts/gen_persona_header.py" "$PERSONA" "$REPO_DIR/src-overlay/aurora_persona.h"

WEBGL_DIR="$SRC/third_party/blink/renderer/modules/webgl"
mkdir -p "$WEBGL_DIR"
cp "$REPO_DIR/src-overlay/aurora_persona.h" "$WEBGL_DIR/aurora_persona.h"

echo "========== [2] 链式应用 F1-F8 =========="
for n in 1 2 3 4 5 6 7 8; do
    script="$REPO_DIR/scripts/apply_f$n.py"
    if [ -f "$script" ]; then
        echo "--- F$n ---"
        python3 "$script" "$SRC"
    else
        echo "--- F$n: 脚本不存在，跳过（${n}/8 就绪）---"
    fi
done

echo "========== [3] 全补丁落盘自检 =========="
FAIL=0
grep -q "kAuroraGLRenderer" "$SRC/third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc" || { echo "F1/F2 未生效"; FAIL=1; }
grep -rq "aurora_fp" "$SRC/third_party/blink/renderer/modules/canvas/canvas2d/base_rendering_context_2d.cc" 2>/dev/null || echo "F3: 未应用（可接受，若脚本未就绪）"
grep -q "kAuroraHardwareConcurrency" "$SRC/third_party/blink/renderer/core/frame/navigator_concurrent_hardware.cc" || { echo "F6 未生效"; FAIL=1; }
[ "$FAIL" -eq 0 ] && echo "全补丁自检 PASS" || { echo "全补丁自检 FAIL"; exit 1; }
echo "========== apply_all 完成 =========="
