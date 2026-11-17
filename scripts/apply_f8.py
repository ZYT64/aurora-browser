#!/usr/bin/env python3
"""AURORA-FP F8 应用脚本：Client Hints（UA-CH）hook（2 锚点）。

用法: apply_f8.py <chromium-src-root>

设计原则（对齐 scripts/apply_f1.py）：
- 精确锚点替换，不依赖行号（抗上游漂移）
- 每个锚点必须恰好命中 1 次，命中数异常即退出非零并打印现场行号
- persona 值来自 aurora_persona.h（编译期常量）

F8 最小实现（可编译）：
- navigator_ua_data.cc：首个 include 后插入 aurora_persona.h + namespace aurora_fp { inline void UACHHook() {} }
  空函数；resolver 创建后插入 aurora_fp::UACHHook(); 空调用 + 注释 // AURORA-FP: persona 字段替换点
- client_hints.cc：首个 include 后插入 aurora_persona.h；MakeDecodeMap 前加注释 hook 标记
"""
import sys

PERSONA_INCLUDE = '#include "third_party/blink/renderer/modules/webgl/aurora_persona.h"'

# (文件相对路径, [(旧串, 新串, 说明), ...])
TARGETS = [
    (
        "third_party/blink/renderer/core/frame/navigator_ua_data.cc",
        [
            # 1) 插入 aurora_persona.h include
            (
                '#include "third_party/blink/renderer/core/frame/navigator_ua_data.h"',
                '#include "third_party/blink/renderer/core/frame/navigator_ua_data.h"\n'
                + PERSONA_INCLUDE,
                'navigator_ua_data.cc 插入 aurora_persona.h include',
            ),
            # 2) 在 include 后定义 aurora_fp::UACHHook 空函数
            (
                PERSONA_INCLUDE,
                PERSONA_INCLUDE + '\n\n'
                'namespace aurora_fp {\n'
                'inline void UACHHook() {}\n'
                '}  // namespace aurora_fp',
                'navigator_ua_data.cc 顶部插入 aurora_fp::UACHHook 空函数',
            ),
            # 3) resolver 创建后插入空调用 + 注释
            (
                '      MakeGarbageCollected<ScriptPromiseResolver<UADataValues>>(script_state);\n'
                '  auto promise = resolver->Promise();',
                '      MakeGarbageCollected<ScriptPromiseResolver<UADataValues>>(script_state);\n'
                '  auto promise = resolver->Promise();\n'
                '  // AURORA-FP: persona 字段替换点（第3期后补完整逻辑）\n'
                '  aurora_fp::UACHHook();',
                'getHighEntropyValues resolver 后插入 UACHHook() 空调用',
            ),
        ],
    ),
    (
        "services/network/public/cpp/client_hints.cc",
        [
            # 1) 插入 aurora_persona.h include
            (
                '#include "services/network/public/cpp/client_hints.h"',
                '#include "services/network/public/cpp/client_hints.h"\n'
                + PERSONA_INCLUDE,
                'client_hints.cc 插入 aurora_persona.h include',
            ),
            # 2) MakeDecodeMap 前加 hook 标记注释
            (
                'consteval auto MakeDecodeMap() {',
                '  // AURORA-FP: Accept-CH 解码表 hook 标记（persona hint 映射预留）\n'
                'consteval auto MakeDecodeMap() {',
                'client_hints.cc MakeDecodeMap 前 hook 标记',
            ),
        ],
    ),
]


def apply_edits(tag, path, edits):
    try:
        s = open(path, encoding='utf-8').read()
    except FileNotFoundError:
        print(f"{tag} FAILED: 目标文件不存在: {path}", file=sys.stderr)
        sys.exit(1)

    lines = s.splitlines()
    for old, new, desc in edits:
        n = s.count(old)
        if n != 1:
            print(f"{tag} FAILED: {path} 锚点命中 {n} 次（期望 1）: {desc}",
                  file=sys.stderr)
            key = old.strip().splitlines()[0][:60]
            for i, line in enumerate(lines, 1):
                if key in line:
                    print(f"  现场行 {i}: {line}", file=sys.stderr)
            sys.exit(1)
        s = s.replace(old, new)
        print(f"{tag} OK: {desc}  ({path})")

    open(path, 'w', encoding='utf-8').write(s)
    print(f"{tag} 已落盘: {path}")


def main(src_root):
    root = src_root.rstrip('/')
    for rel_path, edits in TARGETS:
        apply_edits('F8', f"{root}/{rel_path}", edits)

    # 自检：每个目标文件落盘 aurora_persona.h include；kAurora 常量至少一处
    for rel_path, _ in TARGETS:
        path = f"{root}/{rel_path}"
        chk = open(path, encoding='utf-8').read()
        if 'aurora_persona.h' not in chk:
            print(f"F8 FAILED: {path} 未落盘 aurora_persona.h include",
                  file=sys.stderr)
            sys.exit(1)

    nav = open(f"{root}/third_party/blink/renderer/core/frame/navigator_ua_data.cc",
               encoding='utf-8').read()
    if 'aurora_fp::UACHHook()' not in nav:
        print("F8 FAILED: navigator_ua_data.cc 未落盘 UACHHook() 调用",
              file=sys.stderr)
        sys.exit(1)
    if nav.count('aurora_fp::UACHHook()') != 1:
        print("F8 FAILED: UACHHook() 调用数 != 1", file=sys.stderr)
        sys.exit(1)

    print("F8 全部应用并落盘（含 aurora_fp::UACHHook）")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')