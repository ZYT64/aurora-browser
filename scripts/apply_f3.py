#!/usr/bin/env python3
"""AURORA-FP F3 应用脚本：Canvas 2D 像素微扰（固定种子 LSB 噪声）。

用法: apply_f3.py <chromium-src-root>

设计原则：同 apply_f1.py —— 精确锚点替换，不依赖行号，每个锚点恰好命中 1 次。
"""
import sys

TARGET = "third_party/blink/renderer/modules/canvas/canvas2d/base_rendering_context_2d.cc"

# aurora_fp 微扰内核（与 F4/F5 同款，跨会话恒定）
AURORA_FP_KERNEL = r'''
namespace aurora_fp {
  inline uint64_t NextNoise(uint64_t& s) {
    s ^= s << 13;
    s ^= s >> 7;
    s ^= s << 17;
    return s;
  }
}  // namespace aurora_fp
'''

EDITS = [
    # ① include 锚点：第一个 #include 后插入 aurora_persona.h
    (
        '#include "third_party/blink/renderer/modules/canvas/canvas2d/base_rendering_context_2d.h"',
        '#include "third_party/blink/renderer/modules/canvas/canvas2d/base_rendering_context_2d.h"\n'
        '#include "third_party/blink/renderer/modules/canvas/canvas2d/aurora_persona.h"',
        '插入 aurora_persona.h include',
    ),
    # ② getImageDataInternal 锚点：函数体开头插入噪声预处理注释与调用点
    (
        'ImageData* BaseRenderingContext2D::getImageDataInternal(\n'
        '    int sx,\n'
        '    int sy,\n'
        '    int sw,\n'
        '    int sh,\n'
        '    ImageDataSettings* image_data_settings,\n'
        '    ExceptionState& exception_state) {\n'
        '  if (!base::CheckMul(sw, sh).IsValid<int>()) {\n'
        '    exception_state.ThrowRangeError("Out of memory at ImageData creation");\n'
        '    return nullptr;\n'
        '  }',
        'ImageData* BaseRenderingContext2D::getImageDataInternal(\n'
        '    int sx,\n'
        '    int sy,\n'
        '    int sw,\n'
        '    int sh,\n'
        '    ImageDataSettings* image_data_settings,\n'
        '    ExceptionState& exception_state) {\n'
        '  if (!base::CheckMul(sw, sh).IsValid<int>()) {\n'
        '    exception_state.ThrowRangeError("Out of memory at ImageData creation");\n'
        '    return nullptr;\n'
        '  }\n'
        '  // AURORA-FP F3: 固定种子像素微扰预处理钩子（canvas 2D 读回路径加固）\n'
        '  uint64_t canvas_noise_state = kAuroraCanvasSeed;\n'
        + AURORA_FP_KERNEL +
        '\n',
        'getImageDataInternal: 注入噪声预处理钩子 + aurora_fp 内核',
    ),
    # ③ readPixels 锚点：完成后对 pixmap 每像素 ±1 LSB 加噪
    (
        '    const bool read_pixels_successful =\n'
        '        snapshot->PaintImageForCurrentFrame().readPixels(\n'
        '            image_data->GetSkPixmap(), sx, sy);',
        '    const bool read_pixels_successful =\n'
        '        snapshot->PaintImageForCurrentFrame().readPixels(\n'
        '            image_data->GetSkPixmap(), sx, sy);\n'
        '\n'
        '  // AURORA-FP F3: readPixels 后对 pixmap 像素按固定种子做 ±1 LSB 微扰\n'
        '  if (read_pixels_successful) {\n'
        '    SkPixmap& pixmap = image_data->GetSkPixmap();\n'
        '    uint64_t noise_state = kAuroraCanvasSeed;\n'
        '    int width = pixmap.width();\n'
        '    int height = pixmap.height();\n'
        '    for (int y = 0; y < height; ++y) {\n'
        '      for (int x = 0; x < width; ++x) {\n'
        '        uint32_t* pixel = const_cast<uint32_t*>(pixmap.GetPixelAddr(x, y));\n'
        '        if (pixel) {\n'
        '          uint32_t noise = static_cast<uint32_t>(aurora_fp::NextNoise(noise_state) & 0x3u);\n'
        '          *pixel ^= noise;\n'
        '        }\n'
        '      }\n'
        '    }\n'
        '  }',
        'readPixels: 固定种子像素微扰循环',
    ),
]


def main(src_root):
    path = f"{src_root.rstrip('/')}/{TARGET}"
    try:
        s = open(path, encoding='utf-8').read()
    except FileNotFoundError:
        print(f"F3 FAILED: 目标文件不存在: {path}", file=sys.stderr)
        sys.exit(1)

    lines = s.splitlines()
    for old, new, desc in EDITS:
        n = s.count(old)
        if n != 1:
            print(f"F3 FAILED: 锚点命中 {n} 次（期望 1）: {desc}", file=sys.stderr)
            key = old.strip().splitlines()[0][:60]
            for i, line in enumerate(lines, 1):
                if key in line:
                    print(f"  现场行 {i}: {line}", file=sys.stderr)
            sys.exit(1)
        s = s.replace(old, new)
        print(f"F3 OK: {desc}")

    open(path, 'w', encoding='utf-8').write(s)
    chk = open(path, encoding='utf-8').read()
    assert 'aurora_persona.h' in chk
    assert 'aurora_fp::NextNoise' in chk
    assert 'kAuroraCanvasSeed' in chk
    print(f"F3 全部应用并落盘: {path}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')