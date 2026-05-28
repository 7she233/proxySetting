import subprocess
import winreg
import ctypes
import shutil
import re
import os
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

def get_wlan_default_gateway():
    """获取 WLAN 无线网卡的默认网关地址。

    Returns:
        str: 默认网关地址，如果未找到则返回 None。
    """
    try:
        # 使用 PowerShell 获取 WLAN 接口的默认网关
        # Get-NetRoute 获取 IPv4 默认路由，筛选 InterfaceAlias 包含 WLAN 或 Wi-Fi 的项
        ps_cmd = (
            "Get-NetRoute -DestinationPrefix '0.0.0.0/0' -AddressFamily IPv4 | "
            "Where-Object { $_.InterfaceAlias -match 'WLAN|Wi-Fi|无线' } | "
            "Select-Object -First 1 -ExpandProperty NextHop"
        )

        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-Command', ps_cmd],
            capture_output=True,
            text=True
        )

        gateway = result.stdout.strip()
        if gateway and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', gateway):
            return gateway

        # 备选方案：使用 WMI 查询
        ps_cmd_wmi = (
            "Get-WmiObject Win32_NetworkAdapterConfiguration -Filter \"IPEnabled = True\" | "
            "Where-Object { $_.Description -match 'Wireless|WiFi|WLAN|802.11' -or $_.SettingID -match 'WLAN' } | "
            "ForEach-Object { $_.DefaultIPGateway } | Select-Object -First 1"
        )

        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-Command', ps_cmd_wmi],
            capture_output=True,
            text=True
        )

        gateway = result.stdout.strip()
        if gateway and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', gateway):
            return gateway

        return None
    except Exception as e:
        print(f"获取 WLAN 默认网关时出错: {e}")
        return None

def set_windows_proxy(ip_address, port, enable=True):
    """设置或取消 Windows 系统代理。
    
    Args:
        ip_address (str): 代理服务器的 IP 地址。
        port (str): 代理服务器的端口号。
        enable (bool): True 表示设置代理，False 表示取消代理。
    """
    try:
        # 打开注册表项
        internet_settings = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                           r'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
                                           0, winreg.KEY_WRITE)

        if enable:
            # 启用代理并设置代理服务器地址和端口
            winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(internet_settings, 'ProxyServer', 0, winreg.REG_SZ, f"{ip_address}:{port}")
            print(f"Windows 代理已设置为: {ip_address}:{port}")
        else:
            # 禁用代理
            winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 0)
            # 清除代理服务器设置
            winreg.SetValueEx(internet_settings, 'ProxyServer', 0, winreg.REG_SZ, "") 
            print("Windows 代理已禁用。")

        # 关闭注册表项
        winreg.CloseKey(internet_settings)

        # 通知系统设置已更改
        INTERNET_OPTION_SETTINGS_CHANGED = 39
        INTERNET_OPTION_REFRESH = 37
        
        try:
            internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
            internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
            internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)
            print("已通知系统代理设置更改。请注意，某些应用程序可能需要重启才能应用新的代理设置。")
        except AttributeError:
            print("警告: 无法加载 Wininet.dll 中的 InternetSetOptionW。系统可能未自动刷新代理设置。")
        except Exception as e_ctypes:
            print(f"通知系统代理设置更改时发生错误: {e_ctypes}。可能需要管理员权限或手动刷新。")

    except FileNotFoundError:
        print("错误：找不到注册表路径。请确保您在 Windows 系统上运行此脚本。")
    except Exception as e:
        print(f"设置 Windows 代理时出错: {e}")

def set_git_proxy(ip_address, port, enable=True):
    """设置或取消 Git 全局代理。

    Args:
        ip_address (str): 代理服务器的 IP 地址 (取消时未使用)。
        port (str): 代理服务器的端口号 (取消时未使用)。
        enable (bool): True 表示设置代理，False 表示取消代理。
    """
    if not shutil.which("git"):
        print("错误: 'git' 命令未找到。请确保已安装 Git 并且在 PATH 中。")
        return
        
    try:
        if enable:
            proxy_url = f"http://{ip_address}:{port}" # Git 代理通常是 http
            # 设置 http 和 https 代理
            subprocess.run(['git', 'config', '--global', 'http.proxy', proxy_url], check=True)
            subprocess.run(['git', 'config', '--global', 'https.proxy', proxy_url], check=True)
            print(f"Git 全局代理已设置为: {proxy_url}")
        else:
            # 尝试取消 http 和 https 代理
            http_proxy_get_cmd = ['git', 'config', '--global', '--get', 'http.proxy']
            http_proxy_result = subprocess.run(http_proxy_get_cmd, capture_output=True, text=True)

            if http_proxy_result.returncode == 0 and http_proxy_result.stdout.strip():
                subprocess.run(['git', 'config', '--global', '--unset', 'http.proxy'], check=True)
                print("Git 全局 http.proxy 已取消。")
            else:
                print("Git 全局 http.proxy 未设置或已取消。")

            https_proxy_get_cmd = ['git', 'config', '--global', '--get', 'https.proxy']
            https_proxy_result = subprocess.run(https_proxy_get_cmd, capture_output=True, text=True)
            
            if https_proxy_result.returncode == 0 and https_proxy_result.stdout.strip():
                subprocess.run(['git', 'config', '--global', '--unset', 'https.proxy'], check=True)
                print("Git 全局 https.proxy 已取消。")
            else:
                print("Git 全局 https.proxy 未设置或已取消。")
            
    except subprocess.CalledProcessError as e:
        print(f"设置/取消 Git 代理时出错: {e}.")
    except Exception as e:
        print(f"设置/取消 Git 代理时发生未知错误: {e}")

def set_npm_proxy(ip_address, port, enable=True):
    """设置或取消 npm 全局代理。

    Args:
        ip_address (str): 代理服务器的 IP 地址 (取消时未使用)。
        port (str): 代理服务器的端口号 (取消时未使用)。
        enable (bool): True 表示设置代理，False 表示取消代理。
    """
    # 检查 npm 命令是否存在
    if not shutil.which("npm"):
        print("错误: 'npm' 命令未找到。请确保已安装 Node.js 和 npm 并且在 PATH 中。")
        return

    try:
        if enable:
            proxy_url = f"http://{ip_address}:{port}"
            # 使用 shell=True 让系统 shell 查找 npm 命令
            subprocess.run(f'npm config set proxy {proxy_url}', check=True, shell=True)
            subprocess.run(f'npm config set https-proxy {proxy_url}', check=True, shell=True)
            print(f"npm 全局代理已设置为: {proxy_url}")
        else:
            # 使用 shell=True 查找和执行命令
            proxy_result = subprocess.run('npm config get proxy', capture_output=True, text=True, shell=True)
            if proxy_result.returncode == 0 and proxy_result.stdout.strip() != 'null':
                subprocess.run('npm config delete proxy', check=True, shell=True)
                print("npm 全局 proxy 已取消。")
            else:
                print("npm 全局 proxy 未设置或已取消。")

            https_proxy_result = subprocess.run('npm config get https-proxy', capture_output=True, text=True, shell=True)
            if https_proxy_result.returncode == 0 and https_proxy_result.stdout.strip() != 'null':
                subprocess.run('npm config delete https-proxy', check=True, shell=True)
                print("npm 全局 https-proxy 已取消。")
            else:
                print("npm 全局 https-proxy 未设置或已取消。")
            
    except subprocess.CalledProcessError as e:
        print(f"设置/取消 npm 代理时出错: {e}.")
    except Exception as e:
        print(f"设置/取消 npm 代理时发生未知错误: {e}")

def set_codex_proxy(ip_address, port, enable=True):
    """设置或取消 ~/.codex/.env 文件中的代理环境变量。

    Args:
        ip_address (str): 代理服务器的 IP 地址。
        port (str): 代理服务器的端口号。
        enable (bool): True 表示设置代理，False 表示取消代理。
    """
    codex_env_path = os.path.expanduser("~/.codex/.env")
    codex_dir = os.path.dirname(codex_env_path)

    os.makedirs(codex_dir, exist_ok=True)

    proxy_keys = ['https_proxy=', 'http_proxy=', 'all_proxy=']

    if enable:
        existing_lines = []
        if os.path.exists(codex_env_path):
            with open(codex_env_path, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()

        filtered_lines = [line for line in existing_lines
                         if not any(line.strip().startswith(key) for key in proxy_keys)]

        proxy_lines = [
            f"https_proxy=http://{ip_address}:{port}\n",
            f"http_proxy=http://{ip_address}:{port}\n",
            f"all_proxy=socks5://{ip_address}:{port}\n",
        ]
        filtered_lines.extend(proxy_lines)

        with open(codex_env_path, 'w', encoding='utf-8') as f:
            f.writelines(filtered_lines)

        print(f"Codex .env 代理已设置为: {codex_env_path}")
    else:
        if os.path.exists(codex_env_path):
            with open(codex_env_path, 'r', encoding='utf-8') as f:
                existing_lines = f.readlines()

            filtered_lines = [line for line in existing_lines
                             if not any(line.strip().startswith(key) for key in proxy_keys)]

            with open(codex_env_path, 'w', encoding='utf-8') as f:
                f.writelines(filtered_lines)

            print(f"Codex .env 代理已取消: {codex_env_path}")
        else:
            print(f"Codex .env 文件不存在，无需取消: {codex_env_path}")

def main():
    """主函数，处理用户输入并调用相应功能。"""
    while True:
        choice = input("请选择操作: (1) 设置代理 (2) 取消代理 (q) 退出: ").strip().lower()
        if choice == '1':
            default_gateway = get_wlan_default_gateway()
            default_ip = default_gateway if default_gateway else "192.168.20.190"
            
            if default_gateway:
                print(f"检测到 WLAN 默认网关: {default_gateway}")
            
            ip_input = input(f"请输入代理 IP 地址 ({default_ip}): ").strip()
            if ip_input:
                ip_address = ip_input
            else:
                ip_address = default_ip
                print(f"使用默认代理 IP 地址: {ip_address}")
            
            port_str = input("请输入代理端口号 (10808): ").strip()
            if not port_str:
                port = 10808
                print("未输入端口号，已使用默认端口号 10808。")
            else:
                try:
                    port = int(port_str)
                    if not (0 < port < 65536):
                        print("端口号必须是 1 到 65535 之间的数字。")
                        continue
                except ValueError:
                    print("端口号必须是数字。")
                    continue

            set_windows_proxy(ip_address, str(port), enable=True)
            set_git_proxy(ip_address, str(port), enable=True)
            set_npm_proxy(ip_address, str(port), enable=True)
            set_codex_proxy(ip_address, str(port), enable=True)
            print("\n代理设置完成。")
            break
        elif choice == '2':
            set_windows_proxy("", "", enable=False) # IP 和端口在禁用时未使用
            set_git_proxy("", "", enable=False)   # IP 和端口在禁用时未使用
            set_npm_proxy("", "", enable=False)   # IP 和端口在禁用时未使用
            set_codex_proxy("", "", enable=False) # IP 和端口在禁用时未使用
            print("\n代理已取消。")
            break
        elif choice == 'q':
            print("退出脚本。")
            break
        else:
            print("无效的选择，请重新输入。")

if __name__ == "__main__":
    main()