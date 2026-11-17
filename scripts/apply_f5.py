#!/usr/bin/env python3
"""AURORA-FP F5 应用脚本：WebGPU adapter 信息 persona 替换。

用法: apply_f5.py <chromium-src-root>

设计原则（对齐 scripts/apply_f1.py）：
- 精确锚点替换，不依赖行号（抗上游漂移）
- 每个锚点必须恰好命中 1 次，命中数异常即退出非零并打印现场行号
- persona 值来自 aurora_persona.h（编译期常量）

F5 锚点（3 个）：
1. gpu_adapter.cc: vendor_ / architecture_ -> kAuroraWGVendor / kAuroraWGArch
2. gpu_adapter.cc: device_ / description_ / driver_ -> kAuroraGLDeviceName 占位
3. gpu.cc: GPU::RequestAdapterImpl 入口 -> 标注统一 persona 替换点
外加 2 个 include 锚点（每个目标文件首个 #include 后插入 aurora_persona.h）。
"""
import sys

PERSONA_INCLUDE = ('#include "third_party/blink/renderer/modules/webgl/'
                    'aurora_persona.h"')

# (文件相对路径, [(旧串, 新串, 说明), ...])
TARGETS = [
    (
        "third_party/blink/renderer/modules/webgpu/gpu_adapter.cc",
        [
            (
                '  vendor_ = String::FromUtf8(info.vendor);\n'
                '  architecture_ = String::FromUtf8(info.architecture);',
                '  vendor_ = String(kAuroraWGVendor);\n'
                '  architecture_ = String(kAuroraWGArch);',
                'WebGPU vendor/architecture -> persona 常量',
            ),
            (
                '  if (info.deviceID <= 0xffff) {\n'
                '    device_ = Format("0x{:04x}", info.deviceID);\n'
                '  } else {\n'
                '    device_ = Format("0x{:08x}", info.deviceID);\n'
                '  }\n'
                '  description_ = String::FromUtf8(info.device);\n'
                '  driver_ = String::FromUtf8(info.description);',
                '  // TODO(persona): 固定 device/description/driver 占位，后续按 persona 细化\n'
                '  device_ = String(kAuroraGLDeviceName);\n'
                '  description_ = String(kAuroraGLDeviceName);\n'
                '  driver_ = String(kAuroraGLDeviceName);',
                'WebGPU device/description/driver -> 固定占位 + TODO(persona)',
            ),
            (
                '#include "third_party/blink/renderer/modules/webgpu/gpu_adapter.h"',
                '#include "third_party/blink/renderer/modules/webgpu/gpu_adapter.h"\n'
                + PERSONA_INCLUDE,
                'gpu_adapter.cc 插入 aurora_persona.h include',
            ),
        ],
    ),
    (
        "third_party/blink/renderer/modules/webgpu/gpu.cc",
        [
            (
                'void GPU::RequestAdapterImpl(\n'
                '    ScriptState* script_state,\n'
                '    const GPURequestAdapterOptions* options,\n'
                '    ScriptPromiseResolver<IDLNullable<GPUAdapter>>* resolver) {',
                'void GPU::RequestAdapterImpl(\n'
                '    ScriptState* script_state,\n'
                '    const GPURequestAdapterOptions* options,\n'
                '    ScriptPromiseResolver<IDLNullable<GPUAdapter>>* resolver) {\n'
                '  // AURORA-FP F5: 返回的 adapter 信标在 GPUAdapter 构造中统一做 persona\n'
                '  // 替换（vendor/architecture/device/description/driver，见 gpu_adapter.cc）。',
                'gpu.cc RequestAdapterImpl 标注统一 persona 替换点',
            ),
            (
                '#include "third_party/blink/renderer/modules/webgpu/gpu.h"',
                '#include "third_party/blink/renderer/modules/webgpu/gpu.h"\n'
                + PERSONA_INCLUDE,
                'gpu.cc 插入 aurora_persona.h include',
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
        apply_edits('F5', f"{root}/{rel_path}", edits)

    # 自检：替换确实落盘且含 persona 常量 / include
    for rel_path, _ in TARGETS:
        path = f"{root}/{rel_path}"
        chk = open(path, encoding='utf-8').read()
        if 'aurora_persona.h' not in chk or 'kAurora' not in chk:
            print(f"F5 FAILED: {path} 未落盘 persona 常量或 include", file=sys.stderr)
            sys.exit(1)
    print("F5 全部应用并落盘（含 kAurora）")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
