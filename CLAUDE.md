# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Windows-only CLI utility for setting/unsetting proxy configurations across multiple tools simultaneously. The use case is tethering a phone hotspot to a Windows 10 PC and needing a proxy to reach GitHub and other services.

## Running

No build step. No third-party dependencies (stdlib only).

```bash
# Via batch launcher (uses .venv Python)
proxySetting1.bat

# Direct execution
python proxySettingNew.py
```

No automated tests exist.

## Architecture

Two standalone scripts, no shared modules:

- **`proxySettingNew.py`** (v2, active) — The primary script. Configures proxy in 4 places: Windows system registry, Git global config, npm global config, and Codex env file (`~/.codex/.env`). Auto-detects the WLAN default gateway IP via PowerShell as the default proxy address.
- **`proxySetting.py`** (v1, legacy) — Original version. Windows system proxy + Git only. Kept for reference.
- **`proxySetting1.bat`** — Thin wrapper that invokes `proxySettingNew.py` through the venv interpreter.

配置从 `config.env` 读取（SSID、端口、AutoConfigURL），不存在时使用默认值。`config.env.example` 作为模板提交到 git。

### Key functions in proxySettingNew.py

| Function | What it configures |
|---|---|
| `get_wlan_default_gateway()` | Detects WLAN gateway IP via PowerShell `Get-NetRoute` with WMI fallback |
| `set_windows_proxy(ip, port, enable, auto_config_url)` | Registry keys + AutoDetect + AutoConfigURL management |
| `set_git_proxy(ip, port, enable)` | `git config --global http.proxy` / `https.proxy` |
| `set_npm_proxy(ip, port, enable)` | `npm config set proxy` / `https-proxy` |
| `set_codex_proxy(ip, port, enable)` | Writes env vars to `~/.codex/.env` |
| `load_config()` | 从 config.env 读取配置，不存在时用默认值 |
| `connect_wifi(ssid)` | 通过 netsh 切换 WiFi，轮询等待连接成功 |

## Platform Constraints

- **Windows-only**: uses `winreg`, `ctypes.windll`, and PowerShell subprocess calls
- Requires Git in PATH; npm is optional (gracefully skipped if absent)
- All user-facing strings and code comments are in Chinese
