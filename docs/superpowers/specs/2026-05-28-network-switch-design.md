# 一键网络切换设计文档

## 背景

用户在两个网络环境间频繁切换：
- **外网**（手机热点）：WiFi SSID `spp`，需要设置代理才能访问 GitHub 等服务
- **内网**（企业内网）：WiFi SSID `SUNING-Office`，需要恢复企业代理配置

当前痛点：切换网络时需要手动连接 WiFi、手动调整代理设置（包括自动检测和配置脚本），操作繁琐。

## 目标

运行一个脚本，选择「切到外网」或「切到内网」，自动完成 WiFi 切换 + 代理配置，无需手动干预。

## 设计

### 配置文件

可变配置提取到项目根目录 `config.env`，脚本启动时读取：

```env
# WiFi SSID 配置
EXTERNAL_WIFI_SSID=spp
INTERNAL_WIFI_SSID=SUNING-Office

# 代理配置
PROXY_PORT=10808

# 企业内网自动配置脚本地址
AUTO_CONFIG_URL=http://it.cnsuning.com/zongbu.pac
```

脚本手动解析读取（避免引入第三方依赖）。如文件不存在，使用上述默认值。

`config.env` 应加入 `.gitignore`，因为包含环境特定配置。同时提供 `config.env.example` 作为模板。

### 菜单

```
请选择操作:
(1) 切到外网 (手机热点 spp)
(2) 切到内网 (公司 SUNING-Office)
(q) 退出
```

菜单中 SSID 名称从 `config.env` 读取显示。

### 切到外网流程

1. `netsh wlan connect name=<EXTERNAL_WIFI_SSID>` 切换 WiFi
2. 轮询 `netsh wlan show interfaces` 等待连接成功（超时 15 秒，每秒检查一次）
3. 自动检测 WLAN 网关 IP（复用现有 `get_wlan_default_gateway()`）
4. 设置 Windows 代理注册表：
   - `ProxyEnable` = 1
   - `ProxyServer` = `<网关IP>:<PROXY_PORT>`
   - `AutoDetect` = 0（关闭「自动检测设置」）
   - 清除 `AutoConfigURL`（关闭「使用设置脚本」）
5. 通知系统代理设置已更改（`InternetSetOptionW`）
6. 设置 Git / npm / Codex 代理

### 切到内网流程

1. `netsh wlan connect name=<INTERNAL_WIFI_SSID>` 切换 WiFi
2. 轮询等待连接成功
3. 恢复 Windows 代理注册表：
   - `ProxyEnable` = 0
   - `ProxyServer` = `""`
   - `AutoDetect` = 1（开启「自动检测设置」）
   - `AutoConfigURL` = `<AUTO_CONFIG_URL>`（恢复「使用设置脚本」）
4. 通知系统代理设置已更改
5. 取消 Git / npm / Codex 代理

### 新增函数

#### `connect_wifi(ssid: str) -> bool`

- 调用 `netsh wlan connect name=<ssid>`
- 轮询 `netsh wlan show interfaces` 检查状态
- 超时 15 秒，每 1 秒检查一次
- 返回 True/False

#### 修改 `set_windows_proxy(ip_address, port, enable=True, auto_config_url=None)`

- `enable=True`：设 ProxyEnable=1, AutoDetect=0, 清除 AutoConfigURL
- `enable=False`：设 ProxyEnable=0, AutoDetect=1, 恢复 AutoConfigURL（由 `auto_config_url` 参数指定，值来自 `config.env`）

### 错误处理

- WiFi 连接失败：提示错误，不继续设置代理，返回菜单
- 网关检测失败：提示用户手动输入 IP（保留现有 fallback）
- 操作完成后显示汇总：当前 WiFi、代理状态

### 不变的部分

- `proxySetting1.bat` 保持不变，继续作为启动器
- Git / npm / Codex 代理函数逻辑不变
- 代理端口从 `config.env` 读取，默认 10808

## 注册表路径

`HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Internet Settings`

| 值 | 类型 | 作用 |
|---|---|---|
| `ProxyEnable` | DWORD | 启用/禁用代理 |
| `ProxyServer` | SZ | 代理地址:端口 |
| `AutoDetect` | DWORD | 自动检测设置 |
| `AutoConfigURL` | SZ | 自动配置脚本地址 |
