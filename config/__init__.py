import os,sys

# 获取当前执行文件所在目录（适用于 .exe 和 Python 脚本）
def get_executable_dir():
    if getattr(sys, 'frozen', False):  # 判断是否为 PyInstaller 打包后的文件
        return os.path.dirname(sys.executable)  # 获取 .exe 所在目录
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))  # 获取 .py 文件所在目录

# 获取主目录路径
ROOT_DIR = get_executable_dir()

init_global_proxy = 'global_proxy'
init_global_proxy_port = 'global_proxy_port'
init_global_config = {init_global_proxy:'127.0.0.1', init_global_proxy_port:'8080' }

















