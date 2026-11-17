#!/usr/bin/env python3
"""AURORA-FP F2 应用脚本：WebGL 参数/精度/扩展 引擎级改写。

用法: apply_f2.py <chromium-src-root>

设计原则（与 apply_f1.py 一致）：
- 精确锚点替换，不依赖行号（抗上游漂移）
- 每个锚点必须恰好命中 1 次，命中数异常即退出非零并打印现场行号
- 不重复添加 aurora_persona.h include（F1 已加）

EDITS（5 个锚点，目标文件同 F1：webgl_rendering_context_base.cc）：
  1. GL_VENDOR 分支: String("WebKit") -> String(kAuroraGLVendor)
  2. GL_RENDERER 分支: String("WebKit WebGL") -> String(kAuroraGLRenderer)
  3. GL_VERSION 分支: ContextGL()->GetString(GL_VERSION) -> kAuroraGLVersion
  4. getShaderPrecisionFormat: 插入确定性 precision hook（注释标记+aurora_fp::PrecisionHook() 调用，不破坏控制流）
  5. getExtension: 插入注释标记 // AURORA-FP: F2 extension filter hook
"""
import sys

TARGET = "third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc"

# (旧串, 新串, 说明)
EDITS = [
    (
        '    case GL_VENDOR:\n'
        '      return WebGLAny(script_state, String("WebKit"));',
        '    case GL_VENDOR:\n'
        '      return WebGLAny(script_state, String(kAuroraGLVendor));',
        'GL_VENDOR -> kAuroraGLVendor',
    ),
    (
        '    case GL_RENDERER:\n'
        '      return WebGLAny(script_state, String("WebKit WebGL"));',
        '    case GL_RENDERER:\n'
        '      return WebGLAny(script_state, String(kAuroraGLRenderer));',
        'GL_RENDERER -> kAuroraGLRenderer',
    ),
    (
        '    case GL_VERSION:\n'
        '      return WebGLAny(\n'
        '          script_state,\n'
        '          StrCat({"WebGL 1.0 (", String(ContextGL()->GetString(GL_VERSION)),\n'
        '                  ")"}));',
        '    case GL_VERSION:\n'
        '      return WebGLAny(script_state, String(kAuroraGLVersion));',
        'GL_VERSION -> kAuroraGLVersion',
    ),
    (
        '  return MakeGarbageCollected<WebGLShaderPrecisionFormat>(range[0], range[1],\n'
        '                                                          precision);',
        '  // AURORA-FP: F2 deterministic precision hook\n'
        '  aurora_fp::PrecisionHook();\n'
        '  return MakeGarbageCollected<WebGLShaderPrecisionFormat>(range[0], range[1],\n'
        '                                                          precision);',
        'getShaderPrecisionFormat 插入 precision hook',
    ),
    (
        '  WebGLExtension* extension = EnableExtensionIfSupported(name, context);',
        '  // AURORA-FP: F2 extension filter hook\n'
        '  WebGLExtension* extension = EnableExtensionIfSupported(name, context);',
        'getExtension 插入 extension filter 注释标记',
    ),
]


def main(src_root):
    path = f"{src_root.rstrip('/')}/{TARGET}"
    try:
        s = open(path, encoding='utf-8').read()
    except FileNotFoundError:
        print(f"F2 FAILED: 目标文件不存在: {path}", file=sys.stderr)
        sys.exit(1)

    lines = s.splitlines()
    for old, new, desc in EDITS:
        n = s.count(old)
        if n != 1:
            print(f"F2 FAILED: 锚点命中 {n} 次（期望 1）: {desc}", file=sys.stderr)
            key = old.strip().splitlines()[0][:60]
            for i, line in enumerate(lines, 1):
                if key in line:
                    print(f"  现场行 {i}: {line}", file=sys.stderr)
            sys.exit(1)
        s = s.replace(old, new)
        print(f"F2 OK: {desc}")

    open(path, 'w', encoding='utf-8').write(s)
    # 自检：替换确实落盘
    chk = open(path, encoding='utf-8').read()
    assert 'kAuroraGLVendor' in chk and 'kAuroraGLRenderer' in chk and 'kAuroraGLVersion' in chk, "kAuroraGL 常量未落盘"
    assert 'AURORA-FP: F2 deterministic precision hook' in chk, "precision hook 未落盘"
    assert 'AURORA-FP: F2 extension filter hook' in chk, "extension filter 标记未落盘"
    print(f"F2 全部应用并落盘: {path}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
