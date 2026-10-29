# D3D12 on macOS with native NVK

This fork packages vkd3d-proton 3.1 for HighDelay's NVIDIA macOS driver.
The runtime DLLs are **unmodified upstream binaries**, not a new D3D12 compiler.
The macOS presentation bridge, DLSS setup and Wine-prefix rollback helper live
in [nvidia-macos-driver](https://github.com/HighDelay/nvidia-macos-driver).

The rendering path is:

`D3D12 → vkd3d-proton → Wine Vulkan bridge → native NVK → NVIDIA GPU`

It bypasses MoltenVK and the Metal shader translation route. Wine, vkd3d-proton,
NVK shader compilation and GPU-copy presentation remain. No measured speedup is
claimed. D3D11 continues to use the driver's matched DXVK-NVK pair.

## Installation

Install a driver release whose Wine provider contains `vkd3d` in
`/Library/GPUBundles/nvmtl/wine/nvk-wine-runtime.json`. The driver's older
D3D11-only releases do not include these components; source integration alone
does not update an installed driver.

Use [the driver setup guide](https://github.com/HighDelay/nvidia-macos-driver/blob/main/nvk/wine-macos/INSTALL.md)
for dedicated Wine prefixes or duplicate CrossOver bottles. Its helper installs
the matched `d3d12.dll` / `d3d12core.dll` pair and DXGI dependency with original
backups. Do not mix DLLs from different releases or replace CrossOver.app files.

```sh
nvk_runtime=/Library/GPUBundles/nvmtl/wine
nvk_prefix="$HOME/Library/Application Support/Wine/NVK"
"$nvk_runtime/bin/nvk-runtime" check "$nvk_runtime"
"$nvk_runtime/bin/nvk-runtime" install-d3d12 "$nvk_runtime" "$nvk_prefix"
```

The prefix must already be initialized. Launch using the guide's scoped native
provider environment and `WINEDLLOVERRIDES='d3d11,dxgi,d3d12,d3d12core=n'`.
Select the game's D3D12 renderer. ZZZ uses `-use-d3d12`, without `-force-d3d11`.
YAAGL users should use [YAAGL NVK](https://github.com/HighDelay/yaagl-nvk): it
consumes the driver provider and has separate D3D12, DLSS and HUD controls.
Keep ZZZ's Steam Patch and timeout fix enabled; HSR/GI keep their D3D11 defaults.

The new driver build is currently held at the user's request. The existing
published D3D11-only driver cannot use D3D12/DLSS yet; install the matching
updated provider when that driver is built and released.

The standalone release here is a matched **x64 DLL pair**, not a complete NVK
provider, Wine installation or game. Prefer the full driver's helper for setup
and rollback. It supplies DXGI, NVK, NGX/NVAPI and their provenance together.

## DLSS and HUD

The driver adds optional NVIDIA Wine NGX and DXVK-NVAPI components, using the
game's original `nvngx_dlss.dll`. The helper's `install-dlss` command requires
the matching Wine executable so it can register NGX in the correct prefix and
preserve its original registry value. Read the driver guide before enabling it.

The Wine frontend forwards `WINE_NVK_EXPERIMENTAL=dlss` before loading Mesa, so
the setting reaches PE child processes. `WINE_NVK_HUD=fps,frametimes` enables
its presentation FPS/ms overlay. The overlay uploads a small cached bitmap;
the game image is not copied through the CPU. DLSS Super Resolution is verified
on RTX 2060 SUPER. DLSSG is not forcibly blocked; the game/library retains its
normal hardware checks. Frame generation and ray tracing are unqualified.

## Validation and binary provenance

Tested on RTX 2060 SUPER / macOS Tahoe 26.7.1, YAAGL Wine 11.0-1:

- D3D12 device creation, DXIL compute/root UAV, fences, 1,024-word readback,
  vertex/pixel rendering, 120 presentations, pixel checks and resize.
- ZZZ D3D12 scenery, characters and UI, confirmed by the user.
- DLSS SR: three real evaluations, 320×180 to 640×360, 4,680 checked colour
  values with zero mismatches, including launch through a Wine child process.
- ZZZ DLSS Quality and the native FPS/ms HUD, confirmed by the user.

The tested runtime source is upstream commit
`4522cc1a8b1347f1ab1b0f7b14a23ed9444d95d1` (v3.1).
Its original release archive SHA-256 is
`b85ea8219b71093a3924913dd7aae6172333dc0c069983ed510816d67f02120b`.
`BUILD.json` in this fork's release records the original URL and each DLL hash.
The fork changes documentation/packaging only. Other GPUs, commercial CrossOver,
long sessions and all game shader permutations still need testing.

## Reproduce the release

Python 3.14+ with Zstandard support is needed to read the upstream `.tar.zst`.
From a clean checkout, supply the original verified archive:

```sh
python3 tools/package-nvk.py --upstream-archive /absolute/vkd3d-proton-3.1.tar.zst \
  --output /absolute/clean-release-directory
```

This extracts and verifies upstream DLL bytes; it does not rebuild or patch them.
The result includes licenses, source identity, setup notes and checksums.
