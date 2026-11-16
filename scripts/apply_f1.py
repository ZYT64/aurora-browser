#!/usr/bin/env python3
"""AURORA-FP F1 应用脚本：WebGL UNMASKED vendor/renderer 引擎级改写。

用法: apply_f1.py <chromium-src-root>

设计原则：
- 精确锚点替换，不依赖行号（抗上游漂移）
- 每个锚点必须恰好命中 1 次，命中数异常即退出非零并打印现场行号
- 替换内容见 EDITS；persona 值来自 aurora_persona.h（编译期常量）
"""
import sys

TARGET = "third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc"

# (旧串, 新串, 说明)
EDITS = [
    (
        '        return WebGLAny(script_state,\n'
        '                        String(ContextGL()->GetString(GL_RENDERER)));',
        '        return WebGLAny(script_state,\n'
        '                        String(kAuroraGLRenderer));',
        'UNMASKED_RENDERER -> persona 常量',
    ),
    (
        '        return WebGLAny(script_state,\n'
        '                        String(ContextGL()->GetString(GL_VENDOR)));',
        '        return WebGLAny(script_state, String(kAuroraGLVendor));',
        'UNMASKED_VENDOR -> persona 常量',
    ),
    (
        '#include "third_party/blink/renderer/modules/webgl/webgl_debug_renderer_info.h"',
        '#include "third_party/blink/renderer/modules/webgl/webgl_debug_renderer_info.h"\n'
        '#include "third_party/blink/renderer/modules/webgl/aurora_persona.h"',
        '插入 aurora_persona.h include',
    ),
]


def main(src_root):
    path = f"{src_root.rstrip('/')}/{TARGET}"
    try:
        s = open(path, encoding='utf-8').read()
    except FileNotFoundError:
        print(f"F1 FAILED: 目标文件不存在: {path}", file=sys.stderr)
        sys.exit(1)

    lines = s.splitlines()
    for old, new, desc in EDITS:
        n = s.count(old)
        if n != 1:
            print(f"F1 FAILED: 锚点命中 {n} 次（期望 1）: {desc}", file=sys.stderr)
            key = old.strip().splitlines()[0][:60]
            for i, line in enumerate(lines, 1):
                if key in line:
                    print(f"  现场行 {i}: {line}", file=sys.stderr)
            sys.exit(1)
        s = s.replace(old, new)
        print(f"F1 OK: {desc}")

    open(path, 'w', encoding='utf-8').write(s)
    # 自检：替换确实落盘
    chk = open(path, encoding='utf-8').read()
    assert 'kAuroraGLRenderer' in chk and 'kAuroraGLVendor' in chk and 'aurora_persona.h' in chk
    print(f"F1 全部应用并落盘: {path}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
