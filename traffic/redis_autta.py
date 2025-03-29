import os,sys
# 当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)
import subprocess
# import psutil
import redis
from config import *

'''
redis 启动、关闭, 对端口是否占用, 生成新端口等方法
'''

# def is_port_in_use(port):
#     """检查指定端口是否被占用"""
#     for conn in psutil.net_connections(kind="inet"):
#         if conn.laddr.port == port:
#             return True
#     return False

import socket

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def start_redis(base_port=6379):
    """
    启动 Redis 服务，检测默认端口是否被占用，若占用则动态调整端口。
    :param redis_executable_path: Redis 可执行文件路径
    :param redis_config_path: Redis 配置文件路径
    :param base_port: 默认 Redis 端口号
    :return: 实际启动的端口号，Redis 进程对象
    """
    redis_executable_path = os.path.join(ROOT_DIR, 'redis', 'redis-server.exe')
    redis_config_path = os.path.join(ROOT_DIR, 'redis', 'redis.windows.conf')
    port = base_port
    while is_port_in_use(port):
        port += 1
    print(f"启动 Redis 服务，使用端口: {port}")

    # 修改 Redis 配置文件中的端口
    with open(redis_config_path, "r") as file:
        config_lines = file.readlines()

    with open(redis_config_path, "w") as file:
        for line in config_lines:
            if line.strip().startswith("port"):
                file.write(f"port {port}\n")
            else:
                file.write(line)


    # 启动 Redis 服务
    redis_process = subprocess.Popen(
        [redis_executable_path, redis_config_path],
        cwd=os.path.join(ROOT_DIR, "redis"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    write_to_redis(port, 'timestamp', '2024-06-29 21:10:35.796266')
    if read_from_redis(port, 'timestamp') == '2024-06-29 21:10:35.796266' :
        return port , redis_process
    else:
        return None, redis_process


def stop_redis(redis_process):
    """关闭 Redis 服务"""
    if redis_process:
        redis_process.terminate()
        print("Redis 服务已关闭")


def write_to_redis(port, key, value):
    """向 Redis 写入键值对"""
    try:
        r = redis.StrictRedis(host="127.0.0.1", port=port, decode_responses=True)
        r.set(key, value)
        print(f"已写入 Redis: {key} -> {value}")
    except redis.exceptions.ConnectionError as e:
        print(f"无法连接到 Redis: {e}")


def read_from_redis(port, key):
    """从 Redis 读取指定键的值"""
    try:
        r = redis.StrictRedis(host="127.0.0.1", port=port, decode_responses=True)
        value = r.get(key)
        print(f"从 Redis 读取: {key} -> {value}")
        return value
    except redis.exceptions.ConnectionError as e:
        print(f"无法连接到 Redis: {e}")
        return None


# if __name__ == "__main__":
#     s = ""
#     hex_str = s.encode("utf-8").hex()  # 输出 "e4bda0e5a5bd"
#     print(hex_str)
    # Redis 可执行文件路径和配置文件路径
    # redis_executable = r"C:\path\to\redis-server.exe"  # 修改为实际路径
    # redis_config = r"C:\path\to\redis.conf"  # 修改为实际路径

    # 启动 Redis 服务
    # port, redis_process = start_redis()

    # 写入和读取 Redis 数据
    # write_to_redis(port, "timestamp", "Hello, Redis!")
    # read_from_redis(port, "timestamp")

    # 停止 Redis 服务
    # stop_redis(redis_process)












