"""
背景：使用手机热点作为电脑WiFi使用，需要在Windows10电脑端使用代理访问GitHub
目标：
编写Python脚本实现，当用户输入代理ip地址和端口号后
1. 脚本自动设置Windows10网络代理ip和端口
2. 脚本自动设置git的全局代理

"""
import subprocess
import winreg
import ctypes # 新增导入

def set_windows_proxy(ip_address, port=3067, enable=True):
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
    try:
        if enable:
            proxy_url = f"http://{ip_address}:{port}" # Git 代理通常是 http
            # 设置 http 和 https 代理
            subprocess.run(['git', 'config', '--global', 'http.proxy', proxy_url], check=True)
            subprocess.run(['git', 'config', '--global', 'https.proxy', proxy_url], check=True)
            print(f"Git 全局代理已设置为: {proxy_url}")
        else:
            # 尝试取消 http 和 https 代理
            # 使用 check=False 避免在代理未设置时出错
            # 检查 http.proxy 是否已设置
            http_proxy_get_cmd = ['git', 'config', '--global', '--get', 'http.proxy']
            http_proxy_result = subprocess.run(http_proxy_get_cmd, capture_output=True, text=True)

            if http_proxy_result.returncode == 0 and http_proxy_result.stdout.strip():
                subprocess.run(['git', 'config', '--global', '--unset', 'http.proxy'], check=True)
                print("Git 全局 http.proxy 已取消。")
            else:
                print("Git 全局 http.proxy 未设置或已取消。")

            # 检查 https.proxy 是否已设置
            https_proxy_get_cmd = ['git', 'config', '--global', '--get', 'https.proxy']
            https_proxy_result = subprocess.run(https_proxy_get_cmd, capture_output=True, text=True)
            
            if https_proxy_result.returncode == 0 and https_proxy_result.stdout.strip():
                subprocess.run(['git', 'config', '--global', '--unset', 'https.proxy'], check=True)
                print("Git 全局 https.proxy 已取消。")
            else:
                print("Git 全局 https.proxy 未设置或已取消。")
            
    except subprocess.CalledProcessError as e:
        print(f"设置/取消 Git 代理时出错: {e}. 请确保已安装 Git 并且在 PATH 中。")
    except FileNotFoundError:
        print("错误: 'git' 命令未找到。请确保已安装 Git 并且在 PATH 中。")
    except Exception as e:
        print(f"设置/取消 Git 代理时发生未知错误: {e}")

def main():
    """主函数，处理用户输入并调用相应功能。"""
    while True:
        choice = input("请选择操作: (1) 设置代理 (2) 取消代理 (q) 退出: ").strip().lower()
        if choice == '1':
            ip_address = input("请输入代理 IP 地址: ").strip()
            port_str = input("请输入代理端口号: ").strip()
            if not ip_address or not port_str:
                print("IP 地址和端口号不能为空。")
                continue
            try:
                port = int(port_str) # 确保端口是整数
                if not (0 < port < 65536):
                    print("端口号必须是 1 到 65535 之间的数字。")
                    continue
            except ValueError:
                print("端口号必须是数字。")
                continue

            set_windows_proxy(ip_address, str(port), enable=True)
            set_git_proxy(ip_address, str(port), enable=True)
            print("\n代理设置完成。")
            break
        elif choice == '2':
            set_windows_proxy("", "", enable=False) # IP 和端口在禁用时未使用
            set_git_proxy("", "", enable=False)   # IP 和端口在禁用时未使用
            print("\n代理已取消。")
            break
        elif choice == 'q':
            print("退出脚本。")
            break
        else:
            print("无效的选择，请重新输入。")

if __name__ == "__main__":
    main()