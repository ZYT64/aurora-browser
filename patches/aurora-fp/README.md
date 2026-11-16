# AURORA-FP 引擎补丁集

每个补丁按需求编号命名（F1-F13），对应项目书 3.1/3.1.1 节。

| 编号 | 配置面 | Chromium 源码位置 | 状态 |
|---|---|---|---|
| F1 | WebGL UNMASKED_VENDOR/RENDERER | gpu/config/gpu_info_collector.cc + blink webgl | 设计中 |
| F2 | WebGL 参数/扩展/精度 | blink/renderer/modules/webgl/ | 待开工 |
| F3 | Canvas 像素微扰 | canvas2d readback 路径 | 待开工 |
| F4 | AudioContext 微扰 | blink/renderer/modules/webaudio/ | 待开工 |
| F5 | WebGPU adapter | gpu/webgpu/ | 待开工 |
| F6 | navigator.hardware/deviceMemory | blink/renderer/core/frame/navigator*.cc | 待开工 |
| F7 | 字体枚举与度量 | blink/renderer/platform/fonts/ | 待开工 |
| F8 | Client Hints (UA-CH) | services/network/public/cpp/client_hints.cc | 待开工 |

补丁格式：`git format-patch` 标准补丁，跟随上游 milestone rebase。
