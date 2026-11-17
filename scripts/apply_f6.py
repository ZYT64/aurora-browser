#!/usr/bin/env python3
"""AURORA-FP F6 应用脚本：navigator 三件套 persona 替换。

用法: apply_f6.py <chromium-src-root>

设计原则（对齐 scripts/apply_f1.py）：
- 精确锚点替换，不依赖行号（抗上游漂移）
- 每个锚点必须恰好命中 1 次，命中数异常即退出非零并打印现场行号
- persona 值来自 aurora_persona.h（编译期常量）

F6 锚点（3 个，三个文件各 1 处）：
1. navigator_concurrent_hardware.cc: hardwareConcurrency() -> kAuroraHardwareConcurrency
2. navigator_device_memory.cc: deviceMemory() -> static_cast<float>(kAuroraDeviceMemory)
3. navigator_id.cc: platform() 全函数体三分支 -> return String(kAuroraPlatform)
外加 3 个 include 锚点（每个目标文件首个 #include 后插入 aurora_persona.h）。
"""
import sys

PERSONA_INCLUDE = ('#include "third_party/blink/renderer/modules/webgl/'
                    'aurora_persona.h"')

# (文件相对路径, [(旧串, 新串, 说明), ...])
TARGETS = [
    (
        "third_party/blink/renderer/core/frame/navigator_concurrent_hardware.cc",
        [
            (
                '#include "third_party/blink/renderer/core/frame/'
                'navigator_concurrent_hardware.h"',
                '#include "third_party/blink/renderer/core/frame/'
                'navigator_concurrent_hardware.h"\n'
                + PERSONA_INCLUDE,
                'navigator_concurrent_hardware.cc 插入 aurora_persona.h include',
            ),
            (
                'unsigned NavigatorConcurrentHardware::hardwareConcurrency() const {\n'
                '  return static_cast<unsigned>(base::SysInfo::NumberOfProcessors());\n'
                '}',
                'unsigned NavigatorConcurrentHardware::hardwareConcurrency() const {\n'
                '  return kAuroraHardwareConcurrency;\n'
                '}',
                'hardwareConcurrency() -> kAuroraHardwareConcurrency',
            ),
        ],
    ),
    (
        "third_party/blink/renderer/core/frame/navigator_device_memory.cc",
        [
            (
                '#include "third_party/blink/renderer/core/frame/'
                'navigator_device_memory.h"',
                '#include "third_party/blink/renderer/core/frame/'
                'navigator_device_memory.h"\n'
                + PERSONA_INCLUDE,
                'navigator_device_memory.cc 插入 aurora_persona.h include',
            ),
            (
                'float NavigatorDeviceMemory::deviceMemory() const {\n'
                '  return ApproximatedDeviceMemory::GetApproximatedDeviceMemory();\n'
                '}',
                'float NavigatorDeviceMemory::deviceMemory() const {\n'
                '  return static_cast<float>(kAuroraDeviceMemory);\n'
                '}',
                'deviceMemory() -> static_cast<float>(kAuroraDeviceMemory)',
            ),
        ],
    ),
    (
        "third_party/blink/renderer/core/frame/navigator_id.cc",
        [
            (
                '#include "third_party/blink/renderer/core/frame/navigator_id.h"',
                '#include "third_party/blink/renderer/core/frame/navigator_id.h"\n'
                + PERSONA_INCLUDE,
                'navigator_id.cc 插入 aurora_persona.h include',
            ),
            (
                'String NavigatorID::platform() const {\n'
                '#if BUILDFLAG(IS_MAC)\n'
                '  // Match Safari and Mozilla on Mac x86.\n'
                '  return "MacIntel";\n'
                '#elif BUILDFLAG(IS_WIN)\n'
                '  // Match Safari and Mozilla on Windows.\n'
                '  return "Win32";\n'
                '#else  // Unix-like systems\n'
                '  struct utsname osname;\n'
                '  static base::NoDestructor<ThreadSpecific<String>> platform_name;\n'
                '  if ((*platform_name)->IsNull()) {\n'
                '    StringBuilder result;\n'
                '    if (uname(&osname) >= 0) {\n'
                '      result.Append(osname.sysname);\n'
                '      if (strlen(osname.machine) != 0) {\n'
                '        result.Append(" ");\n'
                '        result.Append(osname.machine);\n'
                '      }\n'
                '    }\n'
                '    **platform_name = result.ToString();\n'
                '  }\n'
                '  return **platform_name;\n'
                '#endif\n'
                '}',
                'String NavigatorID::platform() const {\n'
                '  // AURORA-FP F6: platform() 统一返回 persona 配置值，移除平台分支\n'
                '  return String(kAuroraPlatform);\n'
                '}',
                'platform() 三分支 -> 统一 return String(kAuroraPlatform)',
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
        apply_edits('F6', f"{root}/{rel_path}", edits)

    # 自检：替换确实落盘且含 persona 常量 / include
    for rel_path, _ in TARGETS:
        path = f"{root}/{rel_path}"
        chk = open(path, encoding='utf-8').read()
        if 'aurora_persona.h' not in chk or 'kAurora' not in chk:
            print(f"F6 FAILED: {path} 未落盘 persona 常量或 include", file=sys.stderr)
            sys.exit(1)
    print("F6 全部应用并落盘（含 kAurora）")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
