#!/usr/bin/env python3
"""AURORA-FP F4 应用脚本：AudioContext 微扰（采样/频率固定种子噪声）。

用法: apply_f4.py <chromium-src-root>

两个锚点文件：
  - third_party/blink/renderer/modules/webaudio/audio_buffer.cc
  - third_party/blink/renderer/modules/webaudio/realtime_analyser.cc
"""
import sys

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

# (文件相对路径, 旧串, 新串, 说明)
EDITS = [
    # ---- audio_buffer.cc ----
    (
        "third_party/blink/renderer/modules/webaudio/audio_buffer.cc",
        '#include "third_party/blink/renderer/modules/webaudio/audio_buffer.h"',
        '#include "third_party/blink/renderer/modules/webaudio/audio_buffer.h"\n'
        '#include "third_party/blink/renderer/modules/webaudio/aurora_persona.h"\n'
        + AURORA_FP_KERNEL,
        'audio_buffer.cc: 插入 aurora_persona.h include + 微扰内核',
    ),
    (
        "third_party/blink/renderer/modules/webaudio/audio_buffer.cc",
        'NotShared<DOMFloat32Array> AudioBuffer::getChannelData(unsigned channel_index) {\n'
        '  if (channel_index >= channels_.size()) {\n'
        '    return NotShared<DOMFloat32Array>(nullptr);\n'
        '  }\n'
        '\n'
        '  return NotShared<DOMFloat32Array>(channels_[channel_index].Get());\n'
        '}',
        'NotShared<DOMFloat32Array> AudioBuffer::getChannelData(unsigned channel_index) {\n'
        '  if (channel_index >= channels_.size()) {\n'
        '    return NotShared<DOMFloat32Array>(nullptr);\n'
        '  }\n'
        '\n'
        '  NotShared<DOMFloat32Array> result(channels_[channel_index].Get());\n'
        '  // AURORA-FP F4: 对返回的 channel 数据按固定种子加微小幅度噪声（听不见范围）\n'
        '  if (result) {\n'
        '    float* data = result->Data();\n'
        '    size_t length = result->length();\n'
        '    uint64_t noise_state = kAuroraAudioSeed;\n'
        '    for (size_t i = 0; i < length; ++i) {\n'
        '      uint64_t r = aurora_fp::NextNoise(noise_state);\n'
        '      float noise = static_cast<float>(static_cast<int64_t>(r & 0xFFFFu) - 32767) * 1e-7f;\n'
        '      data[i] += noise;\n'
        '    }\n'
        '  }\n'
        '  return result;\n'
        '}',
        'audio_buffer.cc: getChannelData 固定种子采样微扰',
    ),
    # ---- realtime_analyser.cc ----
    (
        "third_party/blink/renderer/modules/webaudio/realtime_analyser.cc",
        '#include "third_party/blink/renderer/modules/webaudio/realtime_analyser.h"',
        '#include "third_party/blink/renderer/modules/webaudio/realtime_analyser.h"\n'
        '#include "third_party/blink/renderer/modules/webaudio/aurora_persona.h"\n'
        + AURORA_FP_KERNEL,
        'realtime_analyser.cc: 插入 aurora_persona.h include + 微扰内核',
    ),
    (
        "third_party/blink/renderer/modules/webaudio/realtime_analyser.cc",
        '  // Convert from linear magnitude to floating-point decibels.\n'
        '  const size_t source_length = magnitude_buffer_.size();\n'
        '  const size_t len = std::min(source_length, destination_array->length());\n'
        '  if (len > 0) {\n'
        '    base::span<float> destination = destination_array->AsSpan();\n'
        '    for (unsigned i = 0; i < len; ++i) {\n'
        '      const float linear_value = magnitude_buffer_[i];\n'
        '      const double db_mag = audio_utilities::LinearToDecibels(linear_value);\n'
        '      destination[i] = static_cast<float>(db_mag);\n'
        '    }\n'
        '  }\n'
        '}',
        '  // Convert from linear magnitude to floating-point decibels.\n'
        '  const size_t source_length = magnitude_buffer_.size();\n'
        '  const size_t len = std::min(source_length, destination_array->length());\n'
        '  if (len > 0) {\n'
        '    base::span<float> destination = destination_array->AsSpan();\n'
        '    for (unsigned i = 0; i < len; ++i) {\n'
        '      const float linear_value = magnitude_buffer_[i];\n'
        '      const double db_mag = audio_utilities::LinearToDecibels(linear_value);\n'
        '      destination[i] = static_cast<float>(db_mag);\n'
        '    }\n'
        '    // AURORA-FP F4: 对 destination 频率数据按同种子加固定扰动\n'
        '    uint64_t noise_state = kAuroraAudioSeed;\n'
        '    for (unsigned i = 0; i < len; ++i) {\n'
        '      uint64_t r = aurora_fp::NextNoise(noise_state);\n'
        '      float noise = static_cast<float>(static_cast<int64_t>(r & 0xFFFFu) - 32767) * 1e-7f;\n'
        '      destination[i] += noise;\n'
        '    }\n'
        '  }\n'
        '}',
        'realtime_analyser.cc: GetFloatFrequencyData destination 微扰',
    ),
]


def main(src_root):
    root = src_root.rstrip('/')
    for relpath, old, new, desc in EDITS:
        path = f"{root}/{relpath}"
        try:
            s = open(path, encoding='utf-8').read()
        except FileNotFoundError:
            print(f"F4 FAILED: 目标文件不存在: {path}", file=sys.stderr)
            sys.exit(1)
        n = s.count(old)
        if n != 1:
            print(f"F4 FAILED: 锚点命中 {n} 次（期望 1）: {desc}", file=sys.stderr)
            key = old.strip().splitlines()[0][:60]
            for i, line in enumerate(s.splitlines(), 1):
                if key in line:
                    print(f"  现场行 {i}: {line}", file=sys.stderr)
            sys.exit(1)
        s = s.replace(old, new)
        open(path, 'w', encoding='utf-8').write(s)
        print(f"F4 OK: {desc}")

    # 自检：两个文件都必须含 aurora_fp::NextNoise + 种子常量
    for relpath in [
        "third_party/blink/renderer/modules/webaudio/audio_buffer.cc",
        "third_party/blink/renderer/modules/webaudio/realtime_analyser.cc",
    ]:
        chk = open(f"{root}/{relpath}", encoding='utf-8').read()
        assert 'aurora_fp::NextNoise' in chk, f"{relpath} 缺 NextNoise"
        assert 'kAuroraAudioSeed' in chk, f"{relpath} 缺 kAuroraAudioSeed"
        assert 'aurora_persona.h' in chk, f"{relpath} 缺 aurora_persona.h"
    print(f"F4 全部应用并落盘: {root}")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')