import mitmproxy.http
import redis,json
from mitmproxy.http import Headers
import time
from queue import Queue



class interceptAddon:
    def __init__(self, redis_port):
        self.pending_flows = {}  # 存储被拦截的请求 / 响应
        self.buffered_flows = Queue()  # 临时存储无法写入到redis中的报文
        self.finish_resume = False
        self.redis_port = redis_port
        self.redis_mitmproxy = redis.StrictRedis(host='127.0.0.1', port=self.redis_port, db=0, decode_responses=True)
        # 监听 PySide6 修改的报文
        self.pubsub = self.redis_mitmproxy.pubsub()
        self.pubsub.subscribe('pyside_channel')
        self.monitor_need_status()
        self.listen_for_modifications()


    def listen_for_modifications(self):
        """ 监听 PySide6 存入的修改报文 """

        def run():
            for message in self.pubsub.listen():
                if message['type'] == 'message':
                    # modified_packet = self.redis_mitmproxy.get("pyside_channel")
                    # if modified_packet:
                    modified_packet = json.loads(message['data'])
                    self.handle_modified_message(modified_packet)

        import threading
        t = threading.Thread(target=run, daemon=True)
        t.start()


    def monitor_need_status(self):
        """ 监听 PySide6 存入的修改报文 """

        def run():
            while True:
                need_status = self.redis_mitmproxy.get("need")
                if need_status == "True" and  not self.buffered_flows.empty() :
                    data = self.buffered_flows.get()
                    self.redis_mitmproxy.publish("mitmproxy_channel", json.dumps(data))
                    self.redis_mitmproxy.set("need", "False")  # 确保 mitmproxy 可以读取
                    print('redis中need为True,从queue中取出第一个元素写入redis中')
                time.sleep(1)  # 轮询间隔

        import threading
        s = threading.Thread(target=run, daemon=True)
        s.start()


    def request(self, flow: mitmproxy.http.HTTPFlow):
        """
            拦截请求报文
            """
        # 暂停 mitmproxy，等待 PySide6 处理
        flow.intercept()
        print(f"🚦 请求报文已存入 Redis，抓包暂停")
        isBase64 = False
        try:
            body = flow.request.content.decode("utf-8")
        except Exception as e:
            print(e)
            try:
                body = flow.request.content.decode("gbk")
            except Exception as e:
                print(e)
                import base64
                body = base64.b64encode(flow.request.content).decode("utf-8")
                isBase64 = True
        # 通过唯一标识符,存入到dict中
        self.pending_flows[flow.id] = flow
        # 提取请求信息
        request_info = {
            'mitm_requst_response': 'request',          # 自定义一个类型, 是请求还是响应
            'mitm_isBase64': isBase64,    # 自定义一个类型, 请求体是否被进行Base64处理, 那边前端显示后需要再转会bytes给mitmproxy
            'method': flow.request.method,          # 请求方式
            'url': flow.request.url,                # 请求地址
            'url_path': flow.request.path,          # 请求路径
            "http_version": flow.request.http_version,  # 协议版本
            'headers': dict(flow.request.headers),  # 请求头, 改成dict类型
            'body': body,                           # 请求体
            'flow_id': flow.id                           # mitmproxy每个报文(区分请求响应)都有唯一id
        }
        self.buffered_flows.put(request_info)


    def response(self, flow: mitmproxy.http.HTTPFlow):
        """
            拦截响应报文
            """
        # 暂停 mitmproxy，等待 PySide6 处理
        flow.intercept()
        isBase64 = False
        try:
            body = flow.response.content.decode("utf-8")
        except Exception as e:
            print(e)
            try:
                body = flow.response.content.decode("gbk")
            except Exception as e:
                print(e)
                import base64
                body = base64.b64encode(flow.response.content).decode("utf-8")
                isBase64 = True
        # 通过唯一标识符,存入到dict中
        self.pending_flows[flow.id] = flow
        # 提取响应信息
        response_info = {
            'mitm_requst_response': 'response',          # 自定义一个类型, 是请求还是响应
            'mitm_isBase64': isBase64,
            "status_code": flow.response.status_code,
            "reason": flow.response.reason,
            "http_version": flow.response.http_version,
            "headers": dict(flow.response.headers),
            "body": body,
            "flow_id": flow.id
        }
        self.buffered_flows.put(response_info)




    def handle_modified_message(self, modified_packet):
        """
        监听修改后的报文队列
        """
        # 从redis中获得pyside6存入的flow_id
        flow_id = modified_packet.get('flow_id')
        if flow_id != None :
            # 在插件拦截到报文的时候会存入到pending_flows中, 格式: {'flow_id': flow}
            origin_flow = self.pending_flows.pop(flow_id)
            # origin_flow.resume()
            # 从redis中获得pyside6存入的mitm_isBase64, 标识是否进行了base64编码
            mitm_isBase64 = modified_packet.get('mitm_isBase64')
            if origin_flow.request:  # 如果是请求报文
                origin_flow.request.method = modified_packet.get('method')
                origin_flow.request.path = modified_packet.get('url_path')
                origin_flow.request.http_version = modified_packet.get('http_version')
                origin_flow.request.headers = self.mitmHeader(modified_packet.get('headers'))
                if mitm_isBase64:
                    # origin_flow.request.content = base64.b64decode(modified_packet.get('body'))
                    pass
                else:
                    origin_flow.request.text = modified_packet.get('body')
            elif origin_flow.response:  # 如果是响应报文
                # flow.response.status_code = int(201)
                origin_flow.response.headers = self.mitmHeader(modified_packet.get('headers'))
                if mitm_isBase64:
                    # origin_flow.response.content = base64.b64decode(modified_packet.get('body'))
                    pass
                else:
                    origin_flow.response.text = modified_packet.get('body')
            origin_flow.resume()


    # 将可能是str、dict、list类型转成mitmproxya识别的bytes类型
    def mitmHeader(self, headers_data):
        # 处理 headers
        if isinstance(headers_data, str):
            try:
                headers_data = json.loads(headers_data)  # 解析 JSON 字符串
            except json.JSONDecodeError:
                print("Error: headers is not a valid JSON string")
                headers_data = {}

        if isinstance(headers_data, dict):
            headers_data = [(k.encode('utf-8'), v.encode('utf-8')) for k, v in headers_data.items()]
        elif isinstance(headers_data, list):
            headers_data = [
                (k.encode('utf-8'), v.encode('utf-8')) if isinstance(k, str) and isinstance(v, str) else (k, v) for k, v
                in headers_data]
        return Headers(headers_data)



    # 生成一个监听插件写入到queue报文的线程, 线程通过信号槽。这个方法就是更新启动线程中的正常信息
    def listtener_queue_traffic(self, msg):
        print(f'{msg}')

    # 生成一个监听插件写入到queue报文的线程, 线程通过信号槽。这个方法就是更新启动线程中的错误信息
    def listtener_queue_traffic_error(self, error_msg):
        """处理 Redis 启动失败"""
        print(f'抓包功能无法正常启动!!!{error_msg}')





