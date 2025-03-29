import os,sys,winreg,re
sys.stdout.reconfigure(encoding='utf-8')
# 当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)
from PySide6.QtCore import QThread, Signal
from util.yaml_util import read_yaml
from config import *



class Worker_shell(QThread):
    result_signal = Signal(str)  # 用于传递输出结果
    error_signal = Signal(str)  # 用于传递错误信息
    message_done = Signal(list)

    def __init__(self, command):
        super().__init__()
        self.command = command
        # 变量保存进程
        self.process = None

    def run(self):
        try:
            exec = self.command['shellCommand']
            if exec == 'set_proxy':
                # 读取获得globalConfig.yaml中的存储字段, 这个字段用来存放对应功能的黑名单、白名单
                globalConfigData = read_yaml(f"{ROOT_DIR}/config/globalConfig.yaml")
                global_proxy = globalConfigData.get('global_proxy')
                global_proxy_port = globalConfigData.get('global_proxy_port')
                if global_proxy != '' and global_proxy != None and \
                        self.is_ip_port_format(f"{global_proxy}:{global_proxy_port}"):
                    setResult = self.set_proxy(f"{global_proxy}:{global_proxy_port}")
                    if '代理已设置为' in setResult :
                        self.result_signal.emit(setResult)
                    else:
                        self.error_signal.emit(setResult)
            elif exec == 'unset_proxy':
                unsetResult = self.disable_proxy()
                if '手动代理已关闭' in unsetResult:
                    self.result_signal.emit(unsetResult)
                else:
                    self.error_signal.emit(unsetResult)
        except Exception as e:
            self.error_signal.emit(f"运行命令时出错: {str(e)}")


    @staticmethod
    def set_proxy(proxy_address):
        try:
            # 打开注册表路径
            reg_key = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_key, 0, winreg.KEY_SET_VALUE) as key:
                # 启用代理
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
                # 设置代理地址
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_address)
                return f"代理已设置为 {proxy_address}"
        except Exception as e:
            return f"设置代理失败: {e}"


    def disable_proxy(self):
        try:
            # 注册表路径
            reg_key = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            # 打开注册表键
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_key, 0, winreg.KEY_SET_VALUE) as key:
                # 设置 ProxyEnable 为 0（关闭代理）
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                return "手动代理已关闭"
        except Exception as e:
            return f"关闭手动代理失败: {e}"

    @staticmethod
    def is_ip_port_format(s):
        # 正则表达式匹配 IPv4 地址和端口号
        pattern = r"^((25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.){3}" \
                  r"(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?):" \
                  r"([1-9][0-9]{0,4})$"

        # 判断是否匹配
        if re.match(pattern, s):
            # 提取端口号并验证范围（1-65535）
            ip, port = s.split(":")
            if 1 <= int(port) <= 65535:
                return True
        return False

    # 关闭进程
    def stop(self):
        """终止子进程"""
        if self.process and self.process.poll() is None:
            self.process.terminate()  # 终止进程
            self.process.wait()  # 等待进程退出




