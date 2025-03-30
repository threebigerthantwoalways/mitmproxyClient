import os, sys
# 当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)
from util.yaml_util import read_yaml
import asyncio
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster
# from traffic.capture_traffic_addon import interceptAddon
from config import *

async def start_mitmproxy_async():
    # 读取获得globalConfig.yaml中的存储字段, 这个字段用来存放对应功能的黑名单、白名单
    globalConfigData = read_yaml(f"{ROOT_DIR}/config/globalConfig.yaml")
    global_proxy = globalConfigData.get('global_proxy')
    global_proxy_port = globalConfigData.get('global_proxy_port')
    # 配置 mitmproxy
    options = Options(
        listen_host=global_proxy,
        listen_port=int(global_proxy_port),
        ssl_insecure=True
    )
    mitm = DumpMaster(options)
    # mitm.addons.add(interceptAddon(redis_port))
    try:
        await mitm.run()
    except KeyboardInterrupt:
        # print("抓包停止")
        await mitm.shutdown()


# 只启动抓包功能
# redisPort: 启动redis端口
def start_traffic():
    asyncio.run(start_mitmproxy_async())









