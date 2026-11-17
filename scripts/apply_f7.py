#!/usr/bin/env python3
"""AURORA-FP F7 应用脚本：字体枚举/度量 hook（font_cache.cc，3 锚点）。

用法: apply_f7.py <chromium-src-root>

设计原则（对齐 scripts/apply_f1.py）：
- 精确锚点替换，不依赖行号（抗上游漂移）
- 每个锚点必须恰好命中 1 次，命中数异常即退出非零并打印现场行号
- persona 值来自 aurora_persona.h（编译期常量）

F7 最小实现：
- 文件顶部（第一个 include 后）插入 aurora_persona.h + namespace aurora_fp { inline void FontMetricHook() {} }
- 三个字体查找入口（GetFontPlatformData / GetFontData / IsPlatformFontUniqueNameMatchAvailable）
  各插入一次 aurora_fp::FontMetricHook() 空调用，保持原控制流完整可编译。
"""
import sys

PERSONA_INCLUDE = '#include "third_party/blink/renderer/modules/webgl/aurora_persona.h"'

TARGET = "third_party/blink/renderer/platform/fonts/font_cache.cc"

# (旧串, 新串, 说明)
EDITS = [
    # 1) 插入 aurora_persona.h include（锚在 font_cache.cc 首个 include 后）
    (
        '#include "third_party/blink/renderer/platform/fonts/font_cache.h"',
        '#include "third_party/blink/renderer/platform/fonts/font_cache.h"\n'
        + PERSONA_INCLUDE,
        'font_cache.cc 插入 aurora_persona.h include',
    ),
    # 2) 在新插入的 include 行后定义 namespace aurora_fp { FontMetricHook }（锚唯一）
    (
        PERSONA_INCLUDE,
        PERSONA_INCLUDE + '\n\n'
        'namespace aurora_fp {\n'
        'inline void FontMetricHook() {}\n'
        '}  // namespace aurora_fp',
        'font_cache.cc 顶部插入 aurora_fp::FontMetricHook 空函数',
    ),
    # 3) GetFontPlatformData 函数入口：TRACE_EVENT0 后插入调用
    (
        '  TRACE_EVENT0("fonts", "FontCache::GetFontPlatformData");\n\n'
        '#if !BUILDFLAG(IS_MAC)',
        '  TRACE_EVENT0("fonts", "FontCache::GetFontPlatformData");\n'
        '  aurora_fp::FontMetricHook();\n\n'
        '#if !BUILDFLAG(IS_MAC)',
        'GetFontPlatformData 入口插入 FontMetricHook()',
    ),
    # 4) GetFontData 函数入口：函数体首行插入调用
    (
        '    AlternateFontName altername_font_name) {\n'
        '  if (const FontPlatformData* platform_data = GetFontPlatformData(',
        '    AlternateFontName altername_font_name) {\n'
        '  aurora_fp::FontMetricHook();\n'
        '  if (const FontPlatformData* platform_data = GetFontPlatformData(',
        'GetFontData 入口插入 FontMetricHook()',
    ),
    # 5) IsPlatformFontUniqueNameMatchAvailable 函数入口：注释前插入调用
    (
        '    const AtomicString& unique_font_name) {\n'
        '  // Return early to avoid attempting fallback.',
        '    const AtomicString& unique_font_name) {\n'
        '  aurora_fp::FontMetricHook();\n'
        '  // Return early to avoid attempting fallback.',
        'IsPlatformFontUniqueNameMatchAvailable 入口插入 FontMetricHook()',
    ),
]


def main(src_root):
    path = f"{src_root.rstrip('/')}/{TARGET}"
    try:
        s = open(path, encoding='utf-8').read()
    except FileNotFoundError:
        print(f"F7 FAILED: 目标文件不存在: {path}", file=sys.stderr)
        sys.exit(1)

    lines = s.splitlines()
    for old, new, desc in EDITS:
        n = s.count(old)
        if n != 1:
            print(f"F7 FAILED: 锚点命中 {n} 次（期望 1）: {desc}", file=sys.stderr)
            key = old.strip().splitlines()[0][:60]
            for i, line in enumerate(lines, 1):
                if key in line:
                    print(f"  现场行 {i}: {line}", file=sys.stderr)
            sys.exit(1)
        s = s.replace(old, new)
        print(f"F7 OK: {desc}")

    open(path, 'w', encoding='utf-8').write(s)

    # 自检：替换确实落盘
    chk = open(path, encoding='utf-8').read()
    need = ['aurora_persona.h', 'namespace aurora_fp', 'FontMetricHook()']
    missing = [x for x in need if x not in chk]
    if missing:
        print(f"F7 FAILED: 落盘自检缺: {missing}", file=sys.stderr)
        sys.exit(1)
    # 调用次数应为 3（定义处的 {} 不算，通过锚点计数）
    if chk.count('aurora_fp::FontMetricHook()') != 3:
        print("F7 FAILED: FontMetricHook() 调用数 != 3", file=sys.stderr)
        sys.exit(1)
    print(f"F7 全部应用并落盘: {path}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')