#!/usr/bin/env python3
"""AURORA-FP F1 验收脚本：在 content_shell 中跑网页读取 WebGL UNMASKED_VENDOR/UNMASKED_RENDERER，
与 persona.json 的 gpu.gl_vendor / gpu.gl_renderer 比对。

用法: verify_f1.py <content_shell路径> [persona.json路径]
       verify_f1.py --selftest  (内置假 dump-dom 自检，不启动浏览器)
"""

import sys
import os
import json
import re
import shutil
import subprocess
import urllib.parse


def load_persona(persona_path):
    """读取 persona.json，返回 (gl_vendor, gl_renderer)"""
    with open(persona_path, encoding='utf-8') as f:
        data = json.load(f)
    return data['gpu']['gl_vendor'], data['gpu']['gl_renderer']


def run_verification(cs_path, persona_path):
    """启动 content_shell 并验证 WebGL UNMASKED 值"""
    expected_vendor, expected_renderer = load_persona(persona_path)

    # 构造测试页：data: URL，提取 UNMASKED_VENDOR/RENDERER 并输出到 body
    js_code = (
        "var gl=document.createElement('canvas').getContext('webgl');"
        "var ext=gl.getExtension('WEBGL_debug_renderer_info');"
        "document.body.innerHTML='VENDOR='+encodeURIComponent(gl.getParameter(ext.UNMASKED_VENDOR_WEBGL))"
        "'|RENDERER='+encodeURIComponent(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL));"
    )
    PAGE = f'data:text/html,<html><body><script>{js_code}</script></body></html>'

    # 运行 content_shell --dump-dom
    # CI runner 无 X 显示：用 xvfb-run 包裹（install-build-deps 会装）；
    # SwiftShader 软渲染 WebGL 需要 --enable-unsafe-swiftshader（Chromium 132+ 强制显式允许）
    cmd = [cs_path, '--dump-dom', '--no-sandbox', '--enable-unsafe-swiftshader',
           '--use-gl=angle', '--use-angle=swiftshader', PAGE]
    if shutil.which('xvfb-run'):
        cmd = ['xvfb-run', '-a', '--server-args=-screen 0 1280x1024x24'] + cmd
    try:
        result = subprocess.run(cmd, timeout=120, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print(f"FAIL: content_shell 超时 (120s)", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"FAIL: 可执行文件不存在: {e}", file=sys.stderr)
        sys.exit(1)

    out = result.stdout

    # 提取 VENDOR=xxx|RENDERER=yyy
    m = re.search(r'VENDOR=([^|&<]+)\|RENDERER=([^|&<]+)', out)
    if not m:
        print(f"FAIL: 无法从 dump-dom 提取 VENDOR/RENDERER", file=sys.stderr)
        print(f"exit code: {result.returncode}", file=sys.stderr)
        print(f"stdout 前500字符: {out[:500]!r}", file=sys.stderr)
        print(f"stderr 前500字符: {(result.stderr or '')[:500]!r}", file=sys.stderr)
        sys.exit(1)

    actual_vendor = urllib.parse.unquote(m.group(1))
    actual_renderer = urllib.parse.unquote(m.group(2))

    # 比对
    if actual_vendor == expected_vendor and actual_renderer == expected_renderer:
        print("PASS")
        sys.exit(0)
    else:
        print(f"FAIL: 实际值与期望值不一致")
        print(f"  期望 VENDOR:   {expected_vendor}")
        print(f"  实际 VENDOR:   {actual_vendor}")
        print(f"  期望 RENDERER: {expected_renderer}")
        print(f"  实际 RENDERER: {actual_renderer}")
        sys.exit(1)


def selftest():
    """内置假 dump-dom 自检：验证提取+比对逻辑，不启动浏览器"""
    expected_vendor = "Google Inc. (NVIDIA)"
    expected_renderer = "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)"

    # 模拟 dump-dom 输出（包含 URL 编码的期望值）
    fake_dump = (
        "<html><head></head><body>"
        f"VENDOR={urllib.parse.quote(expected_vendor)}|"
        f"RENDERER={urllib.parse.quote(expected_renderer)}"
        "</body></html>"
    )

    m = re.search(r'VENDOR=([^|&<]+)\|RENDERER=([^|&<]+)', fake_dump)
    if not m:
        print("SELFTEST FAIL: 正则未匹配", file=sys.stderr)
        sys.exit(1)

    actual_vendor = urllib.parse.unquote(m.group(1))
    actual_renderer = urllib.parse.unquote(m.group(2))

    if actual_vendor == expected_vendor and actual_renderer == expected_renderer:
        print("SELFTEST PASS")
        sys.exit(0)
    else:
        print("SELFTEST FAIL: 提取值与期望不符", file=sys.stderr)
        sys.exit(1)


def main(argv):
    if len(argv) >= 2 and argv[1] == '--selftest':
        selftest()
        return

    if len(argv) < 2:
        print("用法: verify_f1.py <content_shell路径> [persona.json路径]", file=sys.stderr)
        print("      verify_f1.py --selftest", file=sys.stderr)
        sys.exit(1)

    cs_path = argv[1]
    if len(argv) >= 3:
        persona_path = argv[2]
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        persona_path = os.path.join(script_dir, '..', 'persona', 'persona.example.json')

    run_verification(cs_path, persona_path)


if __name__ == '__main__':
    main(sys.argv)