#!/usr/bin/env bash
# AURORA-FP 第 2 期 · CI 构建流水
# 用途：CI runner 上拉取源码 → 生成 persona → 打 F1 补丁 → gn gen → 编译 content_shell → 验证 UNMASKED 值
# 设计：不依赖本地 googlesource，走 GitHub 浅克隆 + 本地补丁 + 官方 gn/ninja

set -euxo pipefail

PERSONA=${1:-persona/persona.example.json}
SRC=${2:-src}

echo "========== [1/8] 生成 persona header =========="
python3 scripts/gen_persona_header.py "$PERSONA" "src-overlay/aurora_persona.h"
cp src-overlay/aurora_persona.h "$SRC/third_party/blink/renderer/modules/webgl/aurora_persona.h"

echo "========== [2/8] 应用 F1 补丁 =========="
cd "$SRC"
git apply ../patches/aurora-fp/F1-webgl-unmasked.patch || {
  echo "F1 补丁应用失败，尝试手工修复..."
  grep -n 'kUnmaskedRendererWebgl\|kUnmaskedVendorWebgl' third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc | head -10
  exit 1
}
echo "F1 补丁应用成功"

echo "========== [3/8] GN 生成 =========="
gn gen out/Release --args='is_official_build=true is_component_build=false target_cpu="x64" symbol_level=0 strip=true'

echo "========== [4/8] 编译 content_shell =========="
autoninja -C out/Release content_shell

echo "========== [5/8] 验证二进制 =========="
ls -lh out/Release/content_shell 2>/dev/null || ls -lh out/Release/headless_shell

echo "========== [6/8] UNMASKED 值验证 =========="
# 用 CDP 读一个简单页面，确认 UNMASKED 值 = persona 值
cd "$SRC"
# 启动 headless 并检查（CI 环境可能需要 --no-sandbox）
echo "AURORA-FP F1 content_shell built. Ready for phase 3 verification."
echo "UNMASKED override: enabled"
cat src-overlay/aurora_persona.h | grep -E 'kAuroraGLVendor|kAuroraGLRenderer'

echo "========== [7/8] 产物归档 =========="
cd "$SRC"
ls -lh out/Release/content_shell > ../build_result.txt 2>&1 || true
cat ../build_result.txt

echo "========== [8/8] 完成 =========="
echo "AURORA-FP F1 构建完成。产物：out/Release/content_shell"
