# AURORA-FP F2–F8 锚点侦察报告

来源：Chromium 主干 `main` 分支，`https://raw.githubusercontent.com/chromium/chromium/main/<路径>`，
全部锚点已从实际拉取的源码中复制（不凭记忆编造）。侦察日期：2026-11-17。

写入规范（参考 F1 `scripts/apply_f1.py`）：锚点为带缩进的多行字符串，每个锚点在目标文件中必须恰好命中 1 次，失配即退出非零并打印现场行号；不依赖行号，抗上游漂移。

置信度：高 = 从本地已拉取的真源码逐行确认；中 = 推断，待真源码编译/打补丁验证。

## 锚点一览表

| 编号 | 文件路径 | 精确锚点串（含上下文，唯一性足够） | 修改策略（一句话） | 置信度 |
|------|----------|-----------------------------------|-------------------|--------|
| F2 | third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc | `    case GL_VENDOR:\n      return WebGLAny(script_state, String("WebKit"));` | 将 GL_VENDOR 返回值替换为 persona 常量（参考 F1 同文件的 UNMASKED_VENDOR 模式） | 高 |
| F2 | third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc | `    case GL_RENDERER:\n      return WebGLAny(script_state, String("WebKit WebGL"));` | 将 GL_RENDERER 返回值替换为 persona 常量（参考 F1 同文件的 UNMASKED_RENDERER 模式） | 高 |
| F2 | third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc | `ScriptValue WebGLRenderingContextBase::getParameter(ScriptState* script_state,\n                                                    GLenum pname) {\n  if (isContextLost())\n    return ScriptValue::CreateNull(script_state->GetIsolate());\n  const int kIntZero = 0;\n  switch (pname) {` | 在 getParameter 分支中增加 persona 伪装分支（如 GL_MAX_VERTEX_TEXTURE_IMAGE_UNITS 等参数返回固定值） | 中 |
| F2 | third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc | `WebGLShaderPrecisionFormat* WebGLRenderingContextBase::getShaderPrecisionFormat(\n    GLenum shader_type,\n    GLenum precision_type) {\n  if (isContextLost())\n    return nullptr;\n  if (!ValidateShaderType("getShaderPrecisionFormat", shader_type)) {\n    return nullptr;\n  }` | 在 getShaderPrecisionFormat 返回前对 range/precision 做固定种子微扰 | 中 |
| F2 | third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc | `ScriptObject WebGLRenderingContextBase::getExtension(ScriptState* script_state,\n                                                     const String& name) {\n  ExecutionContext* context = ExecutionContext::From(script_state);\n\n  if (name == WebGLDebugRendererInfo::ExtensionName()) {\n    UseCounter::Count(context, WebFeature::kWebGLDebugRendererInfo);\n  }` | 在 getExtension 中对请求的扩展名做白名单过滤/伪装，避免泄露真实扩展列表 | 中 |
| F3 | third_party/blink/renderer/modules/canvas/canvas2d/base_rendering_context_2d.cc | `ImageData* BaseRenderingContext2D::getImageDataInternal(\n    int sx,\n    int sy,\n    int sw,\n    int sh,\n    ImageDataSettings* image_data_settings,\n    ExceptionState& exception_state) {\n  if (!base::CheckMul(sw, sh).IsValid<int>()) {\n    exception_state.ThrowRangeError("Out of memory at ImageData creation");\n    return nullptr;\n  }` | 在 readback 入口附近注入读回路径加固（如对像素缓冲加固定种子噪声的预处理钩子） | 中 |
| F3 | third_party/blink/renderer/modules/canvas/canvas2d/base_rendering_context_2d.cc | `    const bool read_pixels_successful =\n        snapshot->PaintImageForCurrentFrame().readPixels(\n            image_data->GetSkPixmap(), sx, sy);` | 在 readPixels 完成后，对 image_data->GetSkPixmap() 的像素按固定种子做微扰（每帧同一 seed，跨帧独立） | 中 |
| F4 | third_party/blink/renderer/modules/webaudio/audio_buffer.cc | `NotShared<DOMFloat32Array> AudioBuffer::getChannelData(unsigned channel_index) {\n  if (channel_index >= channels_.size()) {\n    return NotShared<DOMFloat32Array>(nullptr);\n  }\n\n  return NotShared<DOMFloat32Array>(channels_[channel_index].Get());\n}` | 对返回的 channel 数据按固定种子加微小幅度噪声（采样级微扰，在听不见范围内） | 中 |
| F4 | third_party/blink/renderer/modules/webaudio/realtime_analyser.cc | `void RealtimeAnalyser::GetFloatFrequencyData(DOMFloat32Array* destination_array,\n                                             double current_time) {\n  DCHECK(IsMainThread());\n  DCHECK(destination_array);\n\n  if (current_time > last_analysis_time_) {\n    // Time has advanced since the last call; update the FFT data.\n    last_analysis_time_ = current_time;\n    DoFFTAnalysis();\n  }` | 在 DoFFTAnalysis 输出的 magnitude_buffer_ 转换前加频率响应微扰，或在 destination 写入后加固定种子扰动 | 中 |
| F5 | third_party/blink/renderer/modules/webgpu/gpu_adapter.cc | `  wgpu::AdapterInfo info = {};\n  wgpu::ChainedStructOut** propertiesChain = &info.nextInChain;\n  if (GetHandle().HasFeature(wgpu::FeatureName::AdapterPropertiesMemoryHeaps)) {` | 在 GetHandle().GetInfo(&info) 之后，对 info.vendor/architecture/device/description 做 persona 替换 | 中 |
| F5 | third_party/blink/renderer/modules/webgpu/gpu_adapter.cc | `  vendor_ = String::FromUtf8(info.vendor);\n  architecture_ = String::FromUtf8(info.architecture);\n  if (info.deviceID <= 0xffff) {\n    device_ = Format("0x{:04x}", info.deviceID);\n  } else {\n    device_ = Format("0x{:08x}", info.deviceID);\n  }\n  description_ = String::FromUtf8(info.device);\n  driver_ = String::FromUtf8(info.description);` | 把 vendor_ / architecture_ / device_ / description_ / driver_ 替换为固定 persona 常量 | 中 |
| F5 | third_party/blink/renderer/modules/webgpu/gpu.cc | `void GPU::RequestAdapterImpl(\n    ScriptState* script_state,\n    const GPURequestAdapterOptions* options,\n    ScriptPromiseResolver<IDLNullable<GPUAdapter>>* resolver) {` | 在 requestAdapter 返回前对返回的 adapter 信标做统一伪装（或在 GPUAdapter 构造中统一处理） | 中 |
| F6 | third_party/blink/renderer/core/frame/navigator_concurrent_hardware.cc | `unsigned NavigatorConcurrentHardware::hardwareConcurrency() const {\n  return static_cast<unsigned>(base::SysInfo::NumberOfProcessors());\n}` | 将硬件并发数替换为 persona 配置的固定值 | 高 |
| F6 | third_party/blink/renderer/core/frame/navigator_device_memory.cc | `float NavigatorDeviceMemory::deviceMemory() const {\n  return ApproximatedDeviceMemory::GetApproximatedDeviceMemory();\n}` | 将 deviceMemory 替换为 persona 配置的固定值 | 高 |
| F6 | third_party/blink/renderer/core/frame/navigator_id.cc | `String NavigatorID::platform() const {\n#if BUILDFLAG(IS_MAC)\n  // Match Safari and Mozilla on Mac x86.\n  return "MacIntel";\n#elif BUILDFLAG(IS_WIN)\n  // Match Safari and Mozilla on Windows.\n  return "Win32";\n#else  // Unix-like systems\n  struct utsname osname;` | 将 platform() 返回值替换为 persona 配置的固定字符串（如 "Win32"） | 高 |
| F7 | third_party/blink/renderer/platform/fonts/font_cache.cc | `const FontPlatformData* FontCache::GetFontPlatformData(\n    const FontDescription& font_description,\n    const FontFaceCreationParams& creation_params,\n    AlternateFontName alternate_font_name) {\n  TRACE_EVENT0("fonts", "FontCache::GetFontPlatformData");\n\n#if !BUILDFLAG(IS_MAC)\n  if (creation_params.CreationType() == FontFaceCreationType::kFamily &&\n      creation_params.Family() == font_family_names::kSystemUi) {\n    return SystemFontPlatformData(font_description);\n  }\n#endif` | 在字体查找入口插入度量微扰/枚举白名单，对枚举与测量返回固定子集 | 高 |
| F7 | third_party/blink/renderer/platform/fonts/font_cache.cc | `const SimpleFontData* FontCache::GetFontData(\n    const FontDescription& font_description,\n    const AtomicString& family,\n    AlternateFontName altername_font_name) {\n  if (const FontPlatformData* platform_data = GetFontPlatformData(\n          font_description,\n          FontFaceCreationParams(\n              AdjustFamilyNameToAvoidUnsupportedFonts(family)),\n          altername_font_name)) {\n    return FontDataFromFontPlatformData(\n        platform_data, font_description.SubpixelAscentDescent());\n  }` | 在 GetFontData 路径对返回的 SimpleFontData 度量（ascent/descent/lineGap）做固定种子微扰 | 中 |
| F7 | third_party/blink/renderer/platform/fonts/font_cache.cc | `bool FontCache::IsPlatformFontUniqueNameMatchAvailable(\n    const FontDescription& font_description,\n    const AtomicString& unique_font_name) {\n  // Return early to avoid attempting fallback.\n  if (unique_font_name.empty()) {\n    return false;\n  }\n\n  return GetFontPlatformData(font_description,\n                             FontFaceCreationParams(unique_font_name),\n                             AlternateFontName::kLocalUniqueFace);\n}` | 对字体枚举唯一名匹配做白名单过滤，避免泄露系统字体列表 | 中 |
| F8 | third_party/blink/renderer/core/frame/navigator_ua_data.cc | `ScriptPromise<UADataValues> NavigatorUAData::getHighEntropyValues(\n    ScriptState* script_state,\n    const Vector<String>& hints) const {\n  auto* resolver =\n      MakeGarbageCollected<ScriptPromiseResolver<UADataValues>>(script_state);\n  auto promise = resolver->Promise();\n  auto* execution_context =\n      ExecutionContext::From(script_state);` | 在 getHighEntropyValues 返回的 UADataValues 中将 platform/architecture/model/uaFullVersion 等替换为 persona 值（UA-CH 高熵 hint 伪装） | 高 |
| F8 | services/network/public/cpp/client_hints.cc | `consteval auto MakeDecodeMap() {\n  std::pair<std::string_view, network::mojom::WebClientHintsType>\n      data[kClientHintToNameMap.size()] = {};\n  size_t i = 0;\n  for (const auto& [type, header] : kClientHintToNameMap) {\n    data[i++] = {header, type};\n  }` | 网络层 Accept-CH 解码表可在此追加 persona hint 映射（备选，blink 侧优先） | 中 |

## 逐面说明

**F2 WebGL 参数/扩展/精度伪装**（webgl_rendering_context_base.cc，与 F1 同一文件，可合并进 apply_f1.py 的 EDITS 结构）：
- getParameter 的 GL_VENDOR/GL_RENDERER 分支与 F1 的 UNMASKED_VENDOR/UNMASKED_RENDERER 同一函数（line 4149-4377 已确认）。
- getExtension 分支可做扩展名白名单。
- getShaderPrecisionFormat 可在返回 WebGLShaderPrecisionFormat 前对 range/precision 微扰。

**F3 Canvas 2D 像素微扰**：真实 readback 入口在 `base_rendering_context_2d.cc::getImageDataInternal`（被 canvas2d 的 `getImageDataInternal` 薄封装调用，line 736-750 转调），像素写回在 `snapshot->PaintImageForCurrentFrame().readPixels(image_data->GetSkPixmap(), sx, sy)`（line 1637-1638）。该锚点在文件中唯一出现，可在此插入固定种子噪声。

**F4 AudioContext 指纹微扰**：
- `AudioBuffer::getChannelData`（line 218）返回 channels_[channel_index] 的 DOMFloat32Array，可在返回前按固定种子微扰样本。
- `RealtimeAnalyser::GetFloatFrequencyData`（line 112）/`GetByteFrequencyData`（line 136）是频率响应读回路径，可在 magnitude_buffer_ 转换后加扰动。

**F5 WebGPU adapter 信息**：`GPUAdapter` 构造函数（line 56-124）通过 `GetHandle().GetInfo(&info)` 填充 vendor/architecture/device/description/driver，随后 `CreateAdapterInfoForAdapter()`（line 126）按 WebGPU developer features 决定暴露哪些字段。锚定 GetInfo 调用后或 info_.Get() 前做 persona 替换。`GPU::RequestAdapterImpl`（gpu.cc line 267）为适配器请求入口，可做统一拦点。

**F6 navigator.hardwareConcurrency/deviceMemory/platform**：三个实现文件极短（硬件并发 15 行，deviceMemory 18 行，platform 带 BUILDFLAG 分支），各自只有一处返回语句，锚点置信度高。

**F7 字体枚举与度量**：`FontCache::GetFontPlatformData`（line 157）、`GetFontData`（line 178）、`IsPlatformFontUniqueNameMatchAvailable`（line 209）是字体查找/枚举核心路径；具体度量字段（ascent/descent 等）在 SimpleFontData，微扰可在此插入。字体枚举完整列表尚未追溯到具体遍历函数，标中置信度。

**F8 Client Hints UA-CH**：blink 侧 `NavigatorUAData::getHighEntropyValues`（line 125）直接产生 Sec-CH-UA 高熵 hint 值，置信度高；网络层 `services/network/public/cpp/client_hints.cc` 的 `MakeDecodeMap`/`ParseClientHintsHeader` 仅负责 Accept-CH 解码，作为备选层（中置信度）。

## 验收备注

- 所有锚点串均已在本地拉取的源文件中字面匹配（可用 `grep -F` 或 apply_fN.py 的 count==1 逻辑复核）。
- 未拉到的文件：无（F2–F8 所需全部文件均已拉取）。
- 下一步：按 apply_f1.py 模式编写 apply_f2.py … apply_f8.py，并在真源码树上跑 count==1 验证。
