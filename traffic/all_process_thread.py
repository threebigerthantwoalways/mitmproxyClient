import os
import sys
# 当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)
from PySide6.QtCore import QThread , Signal
from multiprocessing import Process, Pipe
import threading


class redisProcessThread(QThread):
    port_ready = Signal(int)  # 信号，传递 Redis 端口
    normal_signal = Signal(str)  # 信号，传递 Redis 端口
    error_signal = Signal(str)  # 信号，用于传递错误信息

    def __init__(self):
        super().__init__()
        self.parent_conn, self.child_conn = Pipe()
        self.redis_process = None  # 存储 Redis 进程对象
        self.port = None

    def run(self):
        try:
            # 启动 Redis 服务子进程
            self.redis_process = Process(target=self.run_redis, args=(self.child_conn,))
            self.redis_process.start()

            # 等待管道中的端口号
            if self.parent_conn.poll(timeout=120):  # 使用较长的超时时间
                self.port = self.parent_conn.recv()
                if self.port:
                    self.port_ready.emit(self.port)  # 发送成功信号
                else:
                    self.error_signal.emit("Redis 启动失败，端口未返回")
            else:
                self.error_signal.emit("Redis 启动超时")
        except Exception as e:
            self.error_signal.emit(f"Redis 进程出错: {e}")

    @staticmethod
    def run_redis(conn):
        """运行 Redis 服务，并返回启动的端口号"""
        from traffic.redis_autta import start_redis
        try:
            port, redis_process = start_redis()  # 假设返回端口号和进程对象
            conn.send(port)  # 发送端口号
            print('staticmethod打印端口', port)
        except Exception as e:
            conn.send(None)  # 出错时返回 None
        finally:
            if not conn.closed:
                conn.close()

    def stop(self):
        """停止 Redis 进程"""
        if self.redis_process:
            try:
                import redis
                # 使用 SHUTDOWN 命令优雅关闭
                r = redis.StrictRedis(host="127.0.0.1", port=self.port, decode_responses=True)
                r.shutdown()  # 如果 Redis 支持 SHUTDOWN
                print("Redis 服务已优雅关闭")
                self.normal_signal.emit('Redis 服务已优雅关闭')
            except Exception as e:
                print(f"无法使用 SHUTDOWN 关闭 Redis 服务: {e}")
                self.error_signal.emit(f"无法使用 SHUTDOWN 关闭 Redis 服务: {e}")
            finally:
                # 确保进程终止
                try:
                    if self.redis_process.is_alive() :
                        import psutil
                        parent = psutil.Process(self.redis_process.pid)
                        for child in parent.children(recursive=True):
                            child.terminate()
                        parent.terminate()
                        parent.wait()
                        # print("Redis 进程及其子进程已全部关闭")
                        self.normal_signal.emit('Redis 进程及其子进程已全部关闭')
                except Exception as e:
                    self.error_signal.emit(f"关闭 Redis 进程时出错: {e}")
                finally:
                    self.redis_process = None



class captureTrafficThread(QThread):
    normal_signal = Signal(str)  # 信号，传递 Redis 端口
    error_signal = Signal(str)  # 信号，用于传递错误信息

    def __init__(self, redis_port):
        super().__init__()
        self.parent_conn, self.child_conn = Pipe()
        self.listener_traffic_process = None  # 存储
        self.redis_port = redis_port


    def run(self):
        try:
            from traffic.capture_traffic import start_traffic
            self.normal_signal.emit("启动抓包功能!!!")
            # 启动 mitmproxy 子进程
            self.listener_traffic_process = Process(target=start_traffic, args=(self.redis_port,))
            self.listener_traffic_process.start()
            # 检查进程是否正常启动
            if not self.listener_traffic_process.is_alive():
                print("抓包功能进程启动失败")
                self.error_signal.emit("抓包功能进程启动失败")
        except Exception as e:
            self.error_signal.emit(f"抓包功能启动出错: {e}")
            print(f"抓包功能启动出错: {e}")

    # 关闭抓包进程
    def stop(self):
        """停止抓包进程"""
        if self.listener_traffic_process and self.listener_traffic_process.is_alive():
            try:
                import psutil
                parent = psutil.Process(self.listener_traffic_process.pid)
                for child in parent.children(recursive=True):
                    child.terminate()  # 先尝试终止子进程
                parent.terminate()  # 终止主进程

                # 等待最多 3 秒
                parent.wait(timeout=3)

                # 如果还没退出，强制 kill
                if parent.is_running():
                    print("进程未退出，尝试 kill")
                    for child in parent.children(recursive=True):
                        child.kill()
                    parent.kill()

                self.normal_signal.emit("抓包功能进程及其子进程已全部关闭")
            except psutil.NoSuchProcess:
                self.error_signal.emit(f"进程 PID {self.listener_traffic_process.pid} 不存在，可能已经终止")
            except Exception as e:
                self.error_signal.emit(f"关闭抓包功能进程出错: {e}")
            finally:
                self.listener_traffic_process = None





class redisListenerThread(QThread):
    """ 监听 Redis 频道的线程 """
    data_received = Signal(str)  # 发送信号到 UI
    stop_event = threading.Event()  # ✅ 使用 threading.Event 控制退出
    normal_signal = Signal(str)  # 信号 , 正确信息
    error_signal = Signal(str)  # 信号，用于传递错误信息

    def __init__(self, redis_port):
        super().__init__()
        self.redis_port = redis_port  # 存储 Redis 进程对象

    def run(self):
        self.normal_signal.emit("监听redis中 mitmproxy_channel 开始")
        import redis
        try:
            r = redis.StrictRedis(host="127.0.0.1", port=self.redis_port, decode_responses=True)
            pubsub = r.pubsub()
            pubsub.subscribe('mitmproxy_channel')  # 监听 mitmproxy 发送的报文

            while not self.stop_event.is_set():
                message = pubsub.get_message(timeout=1)  # 这里用 timeout=1，避免一直阻塞
                if message and message['type'] == 'message':
                    self.data_received.emit(message['data'])  # 发送数据给 UI 显示

            pubsub.unsubscribe('mitmproxy_channel')
            pubsub.close()
        except Exception as e:
            self.error_signal.emit(f"Redis 监听线程出错: {e}")

        self.normal_signal.emit("❌ Redis 监听线程已停止")

    def stop(self):
        """ 停止 Redis 监听线程 """
        self.normal_signal.emit('开始关闭监听 mitmproxy 写入 redis')
        self.stop_event.set()
        self.stop_event.clear()  # 清除标志，确保下次可以重新监听













