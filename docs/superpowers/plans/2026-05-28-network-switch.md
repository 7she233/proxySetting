# 一键网络切换实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 改造 proxySettingNew.py，实现一键切换外网/内网络，自动完成 WiFi 切换 + 代理配置。

**Architecture:** 在现有 proxySettingNew.py 中新增配置加载、WiFi 切换函数，扩展 Windows 代理注册表管理（AutoDetect/AutoConfigURL），重写 main() 菜单。

**Tech Stack:** Python 3 (stdlib only), Windows netsh, Windows Registry (winreg)

---

## File Structure

| 操作 | 文件 | 职责 |
|---|---|---|
| Create | `config.env` | 用户环境配置（SSID、端口、AutoConfigURL） |
| Create | `config.env.example` | 配置模板（提交到 git） |
| Create/Modify | `.gitignore` | 排除 config.env |
| Modify | `proxySettingNew.py` | 新增配置加载、WiFi 切换、扩展代理管理、重写菜单 |

---

### Task 1: 配置文件基础设施

**Files:**
- Create: `config.env.example`
- Create: `config.env`
- Create/Modify: `.gitignore`

- [ ] **Step 1: 创建 config.env.example**

```
# WiFi SSID 配置
EXTERNAL_WIFI_SSID=spp
INTERNAL_WIFI_SSID=SUNING-Office

# 代理配置
PROXY_PORT=10808

# 企业内网自动配置脚本地址
AUTO_CONFIG_URL=http://it.cnsuning.com/zongbu.pac
```

- [ ] **Step 2: 创建 config.env（复制 example）**

复制 `config.env.example` 为 `config.env`，内容相同。

- [ ] **Step 3: 更新 .gitignore**

如果 `.gitignore` 不存在则创建，添加：

```
config.env
```

- [ ] **Step 4: 提交**

```bash
git add config.env.example .gitignore
git commit -m "feat: add config file infrastructure"
```

注意：`config.env` 不提交（已在 .gitignore 中）。

---

### Task 2: 配置加载函数

**Files:**
- Modify: `proxySettingNew.py`

- [ ] **Step 1: 在 proxySettingNew.py 顶部（imports 之后）添加 load_config() 函数**

在 `import os` 之后添加：

```python
import time

# 默认配置值
DEFAULTS = {
    'EXTERNAL_WIFI_SSID': 'spp',
    'INTERNAL_WIFI_SSID': 'SUNING-Office',
    'PROXY_PORT': '10808',
    'AUTO_CONFIG_URL': 'http://it.cnsuning.com/zongbu.pac',
}

def load_config():
    """从 config.env 读取配置，文件不存在时使用默认值。

    Returns:
        dict: 配置字典。
    """
    config = dict(DEFAULTS)
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.env')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()
    return config
```

- [ ] **Step 2: 验证语法无误**

```bash
python -c "import py_compile; py_compile.compile('proxySettingNew.py', doraise=True)"
```

Expected: 无输出（无错误）。

- [ ] **Step 3: 提交**

```bash
git add proxySettingNew.py
git commit -m "feat: add config loading from config.env"
```

---

### Task 3: WiFi 切换函数

**Files:**
- Modify: `proxySettingNew.py`

- [ ] **Step 1: 在 get_wlan_default_gateway() 之前添加 connect_wifi() 函数**

```python
def connect_wifi(ssid):
    """连接指定的 WiFi 网络。

    Args:
        ssid (str): WiFi SSID 名称。

    Returns:
        bool: 连接成功返回 True，失败返回 False。
    """
    print(f"正在连接 WiFi: {ssid} ...")
    result = subprocess.run(
        ['netsh', 'wlan', 'connect', f'name={ssid}'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"WiFi 连接命令失败: {result.stderr.strip()}")
        return False

    # 轮询等待连接成功
    for i in range(15):
        time.sleep(1)
        status = subprocess.run(
            ['netsh', 'wlan', 'show', 'interfaces'],
            capture_output=True, text=True
        )
        if ssid in status.stdout:
            print(f"已连接到 WiFi: {ssid}")
            return True

    print(f"WiFi 连接超时（15秒），未能连接到: {ssid}")
    return False
```

- [ ] **Step 2: 验证语法无误**

```bash
python -c "import py_compile; py_compile.compile('proxySettingNew.py', doraise=True)"
```

- [ ] **Step 3: 提交**

```bash
git add proxySettingNew.py
git commit -m "feat: add connect_wifi() for WiFi switching"
```

---

### Task 4: 扩展 Windows 代理注册表管理

**Files:**
- Modify: `proxySettingNew.py` (set_windows_proxy 函数)

- [ ] **Step 1: 替换 set_windows_proxy() 函数**

将现有的 `set_windows_proxy` 函数（第 55-101 行）替换为：

```python
def set_windows_proxy(ip_address, port, enable=True, auto_config_url=None):
    """设置或取消 Windows 系统代理，包括自动检测和配置脚本设置。

    Args:
        ip_address (str): 代理服务器的 IP 地址。
        port (str): 代理服务器的端口号。
        enable (bool): True 表示设置代理，False 表示取消代理。
        auto_config_url (str): 取消代理时恢复的自动配置脚本地址。
    """
    try:
        internet_settings = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                           r'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
                                           0, winreg.KEY_WRITE)

        if enable:
            winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(internet_settings, 'ProxyServer', 0, winreg.REG_SZ, f"{ip_address}:{port}")
            winreg.SetValueEx(internet_settings, 'AutoDetect', 0, winreg.REG_DWORD, 0)
            try:
                winreg.DeleteValue(internet_settings, 'AutoConfigURL')
            except FileNotFoundError:
                pass  # AutoConfigURL 不存在，无需删除
            print(f"Windows 代理已设置为: {ip_address}:{port}")
            print("已关闭「自动检测设置」和「使用设置脚本」")
        else:
            winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(internet_settings, 'ProxyServer', 0, winreg.REG_SZ, "")
            winreg.SetValueEx(internet_settings, 'AutoDetect', 0, winreg.REG_DWORD, 1)
            if auto_config_url:
                winreg.SetValueEx(internet_settings, 'AutoConfigURL', 0, winreg.REG_SZ, auto_config_url)
                print(f"已恢复「使用设置脚本」: {auto_config_url}")
            print("Windows 代理已禁用，已开启「自动检测设置」")

        winreg.CloseKey(internet_settings)

        INTERNET_OPTION_SETTINGS_CHANGED = 39
        INTERNET_OPTION_REFRESH = 37
        try:
            internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
            internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
            internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)
            print("已通知系统代理设置更改。")
        except AttributeError:
            print("警告: 无法加载 Wininet.dll 中的 InternetSetOptionW。")
        except Exception as e_ctypes:
            print(f"通知系统代理设置更改时发生错误: {e_ctypes}")

    except FileNotFoundError:
        print("错误：找不到注册表路径。请确保您在 Windows 系统上运行此脚本。")
    except Exception as e:
        print(f"设置 Windows 代理时出错: {e}")
```

- [ ] **Step 2: 验证语法无误**

```bash
python -c "import py_compile; py_compile.compile('proxySettingNew.py', doraise=True)"
```

- [ ] **Step 3: 提交**

```bash
git add proxySettingNew.py
git commit -m "feat: extend set_windows_proxy with AutoDetect and AutoConfigURL"
```

---

### Task 5: 重写 main() 菜单

**Files:**
- Modify: `proxySettingNew.py` (main 函数)

- [ ] **Step 1: 替换 main() 函数**

将现有的 `main` 函数（第 238-290 行）替换为：

```python
def main():
    """主函数，一键切换外网/内网络。"""
    config = load_config()
    external_ssid = config['EXTERNAL_WIFI_SSID']
    internal_ssid = config['INTERNAL_WIFI_SSID']
    proxy_port = config['PROXY_PORT']
    auto_config_url = config['AUTO_CONFIG_URL']

    while True:
        print(f"\n请选择操作:")
        print(f"  (1) 切到外网 (手机热点 {external_ssid})")
        print(f"  (2) 切到内网 (公司 {internal_ssid})")
        print(f"  (q) 退出")
        choice = input("请输入选择: ").strip().lower()

        if choice == '1':
            # 切到外网
            if not connect_wifi(external_ssid):
                print("WiFi 连接失败，操作中止。")
                continue

            default_gateway = get_wlan_default_gateway()
            if default_gateway:
                print(f"检测到网关 IP: {default_gateway}")
                ip_address = default_gateway
            else:
                ip_input = input("无法自动检测网关 IP，请手动输入代理 IP 地址: ").strip()
                if not ip_input:
                    print("未输入 IP，操作中止。")
                    continue
                ip_address = ip_input

            set_windows_proxy(ip_address, proxy_port, enable=True)
            set_git_proxy(ip_address, proxy_port, enable=True)
            set_npm_proxy(ip_address, proxy_port, enable=True)
            set_codex_proxy(ip_address, proxy_port, enable=True)
            print(f"\n已切换到外网，代理已设置为 {ip_address}:{proxy_port}")
            break

        elif choice == '2':
            # 切到内网
            if not connect_wifi(internal_ssid):
                print("WiFi 连接失败，操作中止。")
                continue

            set_windows_proxy("", "", enable=False, auto_config_url=auto_config_url)
            set_git_proxy("", "", enable=False)
            set_npm_proxy("", "", enable=False)
            set_codex_proxy("", "", enable=False)
            print(f"\n已切换到内网，代理已取消。")
            break

        elif choice == 'q':
            print("退出脚本。")
            break
        else:
            print("无效的选择，请重新输入。")
```

- [ ] **Step 2: 验证语法无误**

```bash
python -c "import py_compile; py_compile.compile('proxySettingNew.py', doraise=True)"
```

- [ ] **Step 3: 提交**

```bash
git add proxySettingNew.py
git commit -m "feat: rewrite main() with WiFi switch menu"
```

---

### Task 6: 更新 CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 更新 CLAUDE.md 中的架构说明**

在 `### Key functions in proxySettingNew.py` 表格前添加配置说明，在表格中添加新函数：

在 `## Architecture` 部分的表格前添加：

```markdown
配置从 `config.env` 读取（SSID、端口、AutoConfigURL），不存在时使用默认值。`config.env.example` 作为模板提交到 git。
```

在表格末尾添加两行：

```markdown
| `load_config()` | 从 config.env 读取配置，不存在时用默认值 |
| `connect_wifi(ssid)` | 通过 netsh 切换 WiFi，轮询等待连接成功 |
```

更新 `### Key functions` 表格中 `set_windows_proxy` 的描述为：

```markdown
| `set_windows_proxy(ip, port, enable, auto_config_url)` | Registry keys + AutoDetect + AutoConfigURL management |
```

- [ ] **Step 2: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with new architecture"
```

---

### Task 7: 最终验证

- [ ] **Step 1: 完整语法检查**

```bash
python -c "import py_compile; py_compile.compile('proxySettingNew.py', doraise=True)"
```

- [ ] **Step 2: 确认 config.env 存在且内容正确**

```bash
cat config.env
```

Expected: 包含 EXTERNAL_WIFI_SSID, INTERNAL_WIFI_SSID, PROXY_PORT, AUTO_CONFIG_URL。

- [ ] **Step 3: 确认 .gitignore 包含 config.env**

```bash
cat .gitignore
```

Expected: 包含 `config.env` 行。

- [ ] **Step 4: 确认 git status 干净（除了 config.env 未跟踪）**

```bash
git status
```

Expected: `config.env` 显示为 untracked（被 .gitignore 忽略），无其他未提交更改。
