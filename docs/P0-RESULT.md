# P0 快捷路径实验结果（2026-11-16）

## 实验目的
验证 Chromium 官方 GPU 测试开关（`--gpu-testing-gl-renderer` 等）能否在不 fork 源码的前提下改写 WebGL 对外暴露值（引擎级效果）。

## 实验环境
- Chromium 155.0.0（/usr/lib/chromium/chromium），headless=new
- 开关组合：`--gpu-testing-vendor-id=0x10de --gpu-testing-device-id=0x2188 --gpu-testing-gl-vendor="Google Inc. (NVIDIA)" --gpu-testing-gl-renderer="ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)" --gpu-testing-gl-version --gpu-testing-device-name --use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`
- 取值方式：CDP 直连，页面内 `WEBGL_debug_renderer_info` 扩展取 UNMASKED 值

## 结果（第一轮：开关无效）
```
VENDOR           = WebKit
RENDERER         = WebKit WebGL
UNMASKED_VENDOR  = Google Inc. (Google)          ← 期望 Google Inc. (NVIDIA)
UNMASKED_RENDERER= ANGLE (Google, Vulkan 1.3.0 (SwiftShader...))  ← 期望 GTX 1650
```

## 源码级归因
1. **作用域错位**：`--gpu-testing-gl-*` 开关的官方定义是 "Override gl renderer **from the GpuInfoCollector**"——只改写 GPUInfoCollector 收集的内部 GPUInfo（chrome://gpu、blocklist 判定、feature flags 用）。WebGL 的 UNMASKED_VENDOR/RENDERER 不走这条路，它直接取自 GL 上下文（ANGLE `glGetString`），测试开关管不到。
2. **开关正在被移除**：上游已有 commit "Remove GPUInfo testing commandline switches"（新测试机制改用 test_group），155 版本这些开关已不可靠。

## 结论
- ❌ **官方测试开关快捷路判死**——不 fork 源码无法实现引擎级环境配置，与项目书路线判定表一致（源码补丁是唯一路）。
- ✅ **P1 构建管线选型升级为当前最高优先级**（P0 原本是"若成立可省去 fork"，现已证伪）。

## 下一步（P1）
构建管线三选一：
1. ungoogled-chromium 打补丁自构建（最干净）
2. Bromite 补丁集移植（ARM 友好先例）
3. 远程构建机/免费 CI（GitHub Actions 公共仓库免费）

配套动作：AURORA-FP v0 补丁集（F1 WebGL 面先行）可以立即开写，与管线选型并行。

## 实验产物
- gpu_test.py（已修：补 import/调试端口/headless，CDP 直读取值）
- gputest.png（webglreport 页面截图）
