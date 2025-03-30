import os,sys,platform,win32api,re,traceback
sys.stdout.reconfigure(encoding='utf-8')
# 当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取上级目录
parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(parent_dir)
from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QComboBox, QLabel, QMessageBox, QLineEdit, QDialog, QFormLayout, QDialogButtonBox
from ui.woker import *
import socket
import json
from ruamel.yaml import YAML
from PySide6.QtGui import QAction

def global_exception_handler(exctype, value, tb):
    # 打印异常类型和信息
    print(f"捕获异常: {exctype.__name__}")
    print(f"捕获异常信息: {value}")

    # 提取并打印异常发生的具体行号和代码内容
    tb_details = traceback.extract_tb(tb)
    for tb_item in tb_details:
        filename = tb_item.filename
        lineno = tb_item.lineno
        funcname = tb_item.name
        code_line = tb_item.line
        print(f"异常发生于文件: {filename}, 行号: {lineno}, 函数: {funcname}")
        print(f"代码内容: {code_line}")

    # 打印完整的堆栈信息
    print("完整堆栈信息:")
    traceback.print_tb(tb)

# 设置全局异常钩子
sys.excepthook = global_exception_handler



class ProxyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("代理设置")

        layout = QFormLayout()

        # 第一行: 代理地址 (下拉框)
        self.proxy_label = QLabel("代理地址:")
        self.proxy_combobox = QComboBox()
        self.proxy_combobox.addItems(self.get_local_ips())
        self.proxy_combobox.currentIndexChanged.connect(self.toggle_custom_proxy)

        # 第二行: 自定义代理地址 (输入框)
        self.custom_proxy_label = QLabel("自定义代理地址:")
        self.custom_proxy_input = QLineEdit()

        # 第三行: 端口 (输入框)
        self.port_label = QLabel("端口:")
        self.port_input = QLineEdit()

        # 按钮
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.confirm_before_accept)
        self.button_box.rejected.connect(self.reject)

        # 添加到布局
        layout.addRow(self.proxy_label, self.proxy_combobox)
        layout.addRow(self.custom_proxy_label, self.custom_proxy_input)
        layout.addRow(self.port_label, self.port_input)
        layout.addWidget(self.button_box)

        self.setLayout(layout)
        self.toggle_custom_proxy()  # 初始化隐藏或显示自定义地址

    def toggle_custom_proxy(self):
        """根据选中的代理类型显示或隐藏自定义输入框"""
        if self.proxy_combobox.currentText() == "自定义代理地址":
            self.custom_proxy_label.show()
            self.custom_proxy_input.show()
        else:
            self.custom_proxy_label.hide()
            self.custom_proxy_input.hide()
            self.custom_proxy_input.setText("")

    def confirm_before_accept(self):
        """弹出确认框，用户确认后才执行提交"""
        reply = QMessageBox.question(
            self, "确认操作", "确定要提交代理设置吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.accept()  # 继续执行提交操作
        else:
            pass  # 用户点击“否”，窗口保持打开

    def get_inputs(self):
        return {
            "proxy": self.proxy_combobox.currentText(),
            "customizeProxy": self.custom_proxy_input.text(),
            "port": self.port_input.text(),
        }

    def get_local_ips(self):
        """获取本机所有IP地址（包括回环地址127.0.0.1）"""
        ip_list = ["自定义代理地址", "127.0.0.1"]
        hostname = socket.gethostname()
        try:
            # 获取本机IP地址
            ip_list.extend(socket.gethostbyname_ex(hostname)[2])
        except socket.gaierror:
            pass
        return list(set(ip_list))  # 去重



class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, token=None):
        super().__init__()
        self.token = token
        self.initUI()
        # 单独的展示拦截抓包功能, 使用的启动redist线程和对应的redis端口   redisListenerThread
        self.intercept_redis_thread = None
        self.intercept_redis_port = None
        # pyside6 启动监听 redis 写入的消息
        self.intercept_redis_listener_thread = None
        # 抓包功能,将报文显示在UI界面
        self.capture_traffic_thread = None
        # 安装证书启动线程
        self.install_certificate_thread = None


    def initUI(self):
        self.setWindowTitle("操作界面")
        screenSize = self.get_screen_size()
        self.setGeometry(100, 60, int(screenSize[0]*0.7), int(screenSize[1]*0.7))  # 占屏幕约70%
        self.setStyleSheet("""
            QMainWindow { background-color: #f8f9fa; }
            QPushButton {
                background-color: #007BFF; color: white; font-size: 14px;
                padding: 8px 15px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #0056b3; }
            QStatusBar { font-size: 14px; color: #333; }
        """)

        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(main_widget)

        # 添加顶部按钮触发下拉框的效果
        dropdown_button = QtWidgets.QPushButton("选项")
        dropdown_menu = QtWidgets.QMenu()
        # dropdown_menu.addAction("新建系统", self.option1_method)
        dropdown_menu.addAction("编辑代理", self.option2_method)
        dropdown_button.setMenu(dropdown_menu)
        # 绑定点击事件，使点击时弹出菜单
        dropdown_button.clicked.connect(
            lambda: dropdown_menu.popup(dropdown_button.mapToGlobal(QtCore.QPoint(0, dropdown_button.height()))))
        main_layout.addWidget(dropdown_button, alignment=QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.tab_widget = QtWidgets.QTabWidget()

        # **窗口右上角按钮**
        pin_action = QAction("📌", self)
        pin_action.triggered.connect(self.toggle_pin)
        self.menuBar().addAction(pin_action)

        # "请求响应拦截" 布局
        sheet_capture_single = QtWidgets.QWidget()
        capture_single_layout = QtWidgets.QVBoxLayout(sheet_capture_single)
        # 当前报文信息显示
        self.current_label = QLabel()
        self.current_label.setStyleSheet("font-size: 16px;")
        self.max_lines = 10000  # 限制最大行数
        # 拦截和放过按钮
        self.intercept_button = QtWidgets.QPushButton("开始拦截")
        self.intercept_button.setFixedWidth(200)
        self.intercept_button.setFixedHeight(40)
        self.intercept_button.clicked.connect(self.toggle_intercept)

        self.allow_button = QtWidgets.QPushButton("发送拦截报文")
        self.allow_button.setFixedWidth(200)
        self.allow_button.setFixedHeight(40)
        self.allow_button.clicked.connect(self.pass_packet)

        self.intercept_set_proxy_button = QtWidgets.QPushButton("快捷设置代理端口")
        self.intercept_set_proxy_button.setFixedWidth(200)
        self.intercept_set_proxy_button.setFixedHeight(40)
        self.intercept_set_proxy_button.clicked.connect(lambda: self.show_toast_and_dialog(
            toast_message="按键已经点击,请勿频繁操作",
            dialog_title="提示信息",
            dialog_message="请确定操作",
            confirm_callback=self.run_shell_command_set_proxy
        ))

        self.intercept_unset_proxy_button = QtWidgets.QPushButton("关闭代理端口")
        self.intercept_unset_proxy_button.setFixedWidth(200)
        self.intercept_unset_proxy_button.setFixedHeight(40)
        self.intercept_unset_proxy_button.clicked.connect(lambda: self.show_toast_and_dialog(
            toast_message="按键已经点击,请勿频繁操作",
            dialog_title="提示信息",
            dialog_message="请确定操作",
            confirm_callback=self.run_shell_command_unset_proxy
        ))

        # 预先设置代理, 目的为了安装mitmproxy证书
        self.intercept_install_certificate_button = QtWidgets.QPushButton("请设置代理安装证书")
        self.intercept_install_certificate_button.setFixedWidth(200)
        self.intercept_install_certificate_button.setFixedHeight(40)
        self.intercept_install_certificate_button.clicked.connect(self.install_certificate)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(self.intercept_button)
        buttons_layout.addWidget(self.allow_button)
        buttons_layout.addWidget(self.intercept_set_proxy_button)
        buttons_layout.addWidget(self.intercept_unset_proxy_button)
        buttons_layout.addWidget(self.intercept_install_certificate_button)
        buttons_layout.setAlignment(QtCore.Qt.AlignLeft)  # 靠左对齐
        capture_single_layout.addWidget(self.current_label)
        capture_single_layout.addLayout(buttons_layout)

        # 添加报文显示区域
        self.message_display = QtWidgets.QTextEdit()
        self.message_display.setReadOnly(False)
        # 设置 QTextEdit 的边框和自动换行
        self.message_display.setStyleSheet("border: 1px solid gray;")  # 确保右侧有边框
        self.message_display.setMaximumWidth(int(screenSize[0]))  # 限制最大宽度
        # 从mitmproxy插件存入消息队列中, 发送给pyside6中的所有消息, 默认为None, 在pyside6端, 存储到一个变量中, 方便发送给
        # mitmproxy插件, 需要携带原始数据使用
        self.current_flow = None  # 保存当前的 flow 对象 , 这样帮助插件脚本识别请求响应, 对应的返回给服务端或者客户端
        self.flowId_url = {}  # 保存flowId和url关系, 因为flowId是请求响应报文唯一标识, 这样可以通过flowId找到响应报文的url
        capture_single_layout.addWidget(self.message_display)
        self.tab_widget.addTab(sheet_capture_single, "请求响应拦截")
        main_layout.addWidget(self.tab_widget)
        self.setCentralWidget(main_widget)


    # 选项, 下拉按键, 设置代理 选项, 调用方法
    def option2_method(self):
        """显示代理配置窗口"""
        dialog = ProxyDialog(self)
        if dialog.exec():
            inputs = dialog.get_inputs()
            print("用户输入:", inputs)
            # 测试用全局配置表globalConfig.yaml
            customizeProxy = inputs.get('customizeProxy')
            proxy = inputs.get('proxy')
            port = inputs.get('port')
            if not os.path.exists(f"{ROOT_DIR}/config/globalConfig.yaml"):
                if customizeProxy == '' or customizeProxy == None:
                    if proxy == '' or proxy == None :
                        self.show_toast('代理设置不能为空!!!')
                    else:
                        init_global_config[init_global_proxy] = proxy
                else:
                    init_global_config[init_global_proxy] = customizeProxy
                init_global_config[init_global_proxy_port] = port
                yaml = YAML()
                # yaml表是list，这样为了防止，字段中的值和系统中特殊标记的值重复，[1]中的才是存储字段和对应值的dict
                with open(f"{ROOT_DIR}/config/globalConfig.yaml", 'w', encoding='utf-8') as f:
                    yaml.dump(init_global_config, f)
            else:
                globalConfigData = read_yaml(f"{ROOT_DIR}/config/globalConfig.yaml")
                if customizeProxy == '' or customizeProxy == None:
                    if proxy == '' or proxy == None:
                        self.show_toast('代理设置不能为空!!!')
                    else:
                        globalConfigData[init_global_proxy] = proxy
                else:
                    globalConfigData[init_global_proxy] = customizeProxy
                globalConfigData[init_global_proxy_port] = port
                yaml = YAML()
                # yaml表是list，这样为了防止，字段中的值和系统中特殊标记的值重复，[1]中的才是存储字段和对应值的dict
                with open(f"{ROOT_DIR}/config/globalConfig.yaml", 'w', encoding='utf-8') as f:
                    yaml.dump(globalConfigData, f)
            # 读取一边, 校验值是否存入
            globalConfigData_again = read_yaml(f"{ROOT_DIR}/config/globalConfig.yaml")
            if customizeProxy == '' or customizeProxy == None:
                if proxy != '' and proxy != None:
                    if globalConfigData_again.get('global_proxy') == proxy and \
                            globalConfigData_again.get('global_proxy_port') == port:
                        self.show_toast('代理设置成功!!!')
                    else:
                        self.show_toast('代理设置失败!!!')
            else:
                if globalConfigData_again.get('global_proxy') == customizeProxy and \
                        globalConfigData_again.get('global_proxy_port') == port:
                    self.show_toast('代理设置成功!!!')
                else:
                    self.show_toast('代理设置失败!!!')
        else:
            print("点击取消")


    # 置顶窗口功能
    def toggle_pin(self):
        """ 置顶窗口 """
        self.setWindowFlag(Qt.WindowStaysOnTopHint, not self.windowFlags() & Qt.WindowStaysOnTopHint)
        self.show()


    def show_toast_and_dialog(self, toast_message, dialog_title, dialog_message, confirm_callback):
        """显示吐司和提示框

        Args:
            dialog_title (str): 提示框标题
            dialog_message (str): 提示框内容
            confirm_callback (callable): 确定按钮回调函数
        """
        # 显示吐司
        # self.show_toast(toast_message)
        # 显示提示框
        reply = QMessageBox.question(
            self,
            dialog_title,
            dialog_message,
            QMessageBox.Ok | QMessageBox.Cancel
        )

        # 点击确定时调用回调函数
        if reply == QMessageBox.Ok and confirm_callback:
            confirm_callback()

    def show_toast(self, message):
        """显示吐司消息

        Args:
            message (str): 吐司消息内容
        """
        toast = QLabel(message, self)
        toast.setStyleSheet(
            "background-color: black; color: white; padding: 5px; border-radius: 100px;")
        toast.setAlignment(Qt.AlignCenter)
        toast.setWindowFlags(Qt.ToolTip)
        toast.setGeometry(self.width() // 2 - 100, self.height() // 2 - 20, 400, 80)
        toast.show()

        # 设置自动关闭
        QTimer.singleShot(3000, toast.close)  # 2秒后自动关闭


    # 点击拦截启动功能
    # port: 启动redis使用的端口号
    def intercept_redis_ready(self, port):
        """Redis 启动成功"""
        self.intercept_redis_port = port
        # 判断是否启动redis成功, 并且给redis存入了一个初始值
        if self.intercept_redis_port != None :
            self.on_run_capture_traffic(f'redis启动,端口 {self.intercept_redis_port} !!!')

            # 连接 Redis
            import redis
            self.redisPyside = redis.StrictRedis(host='127.0.0.1', port=self.intercept_redis_port, db=0, decode_responses=True)
            self.redisPyside.set("need", "True")  # 确保 mitmproxy 可以读取
            # 启动redis线程,监听redis
            from traffic.all_process_thread import redisListenerThread
            self.intercept_redis_listener_thread = redisListenerThread(self.intercept_redis_port)
            self.intercept_redis_listener_thread.normal_signal.connect(self.on_run_capture_traffic)
            self.intercept_redis_listener_thread.data_received.connect(self.display_redis_packets)
            self.intercept_redis_listener_thread.start()

            # 启动抓包线程
            from traffic.all_process_thread import captureTrafficThread
            self.capture_traffic_thread = captureTrafficThread(self.intercept_redis_port)
            self.capture_traffic_thread.normal_signal.connect(self.on_run_capture_traffic)
            self.capture_traffic_thread.error_signal.connect(self.on_run_capture_traffic_error)
            self.capture_traffic_thread.start()

        else:
            self.on_run_capture_traffic('redis未正常启动,未获得端口!!!')



    def run_shell_command_set_proxy(self):
        # 获取输入框的内容
        data = {'shellCommand': 'set_proxy'}
        self.woker_shell = Worker_shell(data)
        self.woker_shell.result_signal.connect(self.listtener_queue_traffic)
        self.woker_shell.error_signal.connect(self.listtener_queue_traffic)
        self.woker_shell.start()


    def run_shell_command_unset_proxy(self):
        data = {'shellCommand': 'unset_proxy'}
        self.woker_shell = Worker_shell(data)
        self.woker_shell.result_signal.connect(self.listtener_queue_traffic)
        self.woker_shell.error_signal.connect(self.listtener_queue_traffic)
        self.woker_shell.start()


    # 获得流量,单独抓包功能启动
    def toggle_intercept(self):
        print(self.intercept_button.text())
        """开始拦截/恢复按钮逻辑"""
        if self.intercept_button.text() == "开始拦截":
            self.init_globalConfig()
            try:
                # 启动 Redis 线程
                from traffic.all_process_thread import redisProcessThread
                self.intercept_redis_thread = redisProcessThread()
                self.intercept_redis_thread.port_ready.connect(self.intercept_redis_ready)
                self.intercept_redis_thread.normal_signal.connect(self.listtener_queue_traffic)
                self.intercept_redis_thread.error_signal.connect(self.listtener_queue_traffic_error)
                self.intercept_redis_thread.start()
                # 修改按键文字
                self.intercept_button.setText("取消拦截")
                # self.intercept_button.setStyleSheet("background-color: gray;")
            except Exception as e:
                print("执行过程中出错:", e)
                self.message_display.append(f'启动抓包功能出错 : {e}')
        else:
            self.message_display.clear()
            if self.capture_traffic_thread:
                self.capture_traffic_thread.stop()  # 调用自定义线程的 stop 方法
                self.capture_traffic_thread.quit()  # 停止线程的事件循环
                QTimer.singleShot(5000, self.capture_traffic_thread.wait)  # 5 秒后检查线程状态
                self.capture_traffic_thread = None
                self.append_output_capture("抓包功能已经停止")
            if self.intercept_redis_listener_thread:
                self.intercept_redis_listener_thread.stop()  # 调用自定义线程的 stop 方法
                self.intercept_redis_listener_thread.quit()  # 停止线程的事件循环
                QTimer.singleShot(5000, self.intercept_redis_listener_thread.wait)  # 避免 UI 卡死
                self.intercept_redis_listener_thread = None
                self.append_output_capture("监听插件写入 redis 线程停止")
            if self.intercept_redis_thread :
                self.intercept_redis_thread.stop()  # 调用自定义线程的 stop 方法
                self.intercept_redis_thread.quit()  # 停止线程的事件循环
                self.intercept_redis_thread.wait()  # 等待线程退出
                self.intercept_redis_thread = None
                self.intercept_redis_port = None
                self.append_output_capture("Redis 服务已停止")
            else:
                self.message_display.append("没有抓包功能启动!!!")
            self.intercept_button.setText("开始拦截")


    # 获得流量,单独抓包功能启动
    def install_certificate(self):
        """开始拦截/恢复按钮逻辑"""
        if self.intercept_install_certificate_button.text() == "请设置代理安装证书":
            self.init_globalConfig()
            try:
                self.intercept_button.hide()
                self.allow_button.hide()
                # 启动抓包线程
                from traffic.all_process_thread import installCertificateThread
                self.install_certificate_thread = installCertificateThread(self.intercept_redis_port)
                self.install_certificate_thread.normal_signal.connect(self.on_run_capture_traffic)
                self.install_certificate_thread.error_signal.connect(self.on_run_capture_traffic_error)
                self.install_certificate_thread.start()
                # 修改按键文字
                self.intercept_install_certificate_button.setText("取消证书安装")
                # self.intercept_button.setStyleSheet("background-color: gray;")
            except Exception as e:
                print("执行过程中出错:", e)
                self.message_display.append(f'启动抓包功能出错 : {e}')
        else:
            self.message_display.clear()
            if self.install_certificate_thread:
                self.install_certificate_thread.stop()  # 调用自定义线程的 stop 方法
                self.install_certificate_thread.quit()  # 停止线程的事件循环
                QTimer.singleShot(5000, self.install_certificate_thread.wait)  # 5 秒后检查线程状态
                self.install_certificate_thread = None
                self.append_output_capture("证书安装功能已经停止")
            else:
                self.message_display.append("没有证书安装功能启动!!!")
            self.intercept_install_certificate_button.setText("请设置代理安装证书")
            self.intercept_button.show()
            self.allow_button.show()


    # 点击单独的抓包功能, 生成一个线程, 线程通过信号槽, 启动一个抓包进程。这个方法就是更新启动进程中的正常信息
    def on_run_capture_traffic(self, msg):
        self.message_display.append(f'{msg}')

    # 点击单独的抓包功能, 生成一个线程, 线程通过信号槽, 启动一个抓包进程。这个方法就是更新启动进程中的错误信息
    def on_run_capture_traffic_error(self, error_msg):
        """处理 Redis 启动失败"""
        self.message_display.append(f'抓包功能无法正常启动!!!{error_msg}')


    # 生成一个监听插件写入到queue报文的线程, 线程通过信号槽。这个方法就是更新启动线程中的正常信息
    def listtener_queue_traffic(self, msg):
        self.message_display.append(f'{msg}')

    # 生成一个监听插件写入到queue报文的线程, 线程通过信号槽。这个方法就是更新启动线程中的错误信息
    def listtener_queue_traffic_error(self, error_msg):
        """处理 Redis 启动失败"""
        self.message_display.append(f'抓包功能无法正常启动!!!{error_msg}')

    # 监听来自抓包插件写入队列的报文
    def display_redis_packets(self, packet):
        """监听脚本插件写入到queue中的报文, """
        packet = json.loads(packet)
        self.message_display.clear()
        # 记录从mitmproxy插件发送的原始值   self.current_label
        self.current_flow = packet
        # 是请求还是响应
        mitm_requst_response = packet.get('mitm_requst_response')
        if mitm_requst_response == 'request' :
            # 通过self.flowId_url保存flowId和url 关系, 这样响应报文可以拿到这个值并跟新Qlabel
            full_url = packet.get('url')
            self.flowId_url[packet.get('flow_id')] = full_url
            if full_url != None :
                self.current_label.setText(f'请求地址: {full_url}')
            # 解析redis种存储的报文信息, 组成http报文格式
            request_line = f"{packet.get('method')} {packet.get('url_path')} {packet.get('http_version')}"
            request_headers = "\n".join([f"{k}: {v}" for k, v in packet.get('headers').items()])
            request_body = packet.get('body')
            if request_body == '' :
                self.message_display.setPlainText(f"{request_line}\n{request_headers}")
            else:
                self.message_display.setPlainText(f"{request_line}\n{request_headers}\n\n{request_body}")
        elif mitm_requst_response == 'response' :
            # 获得存储的url
            full_url = self.flowId_url.pop(packet.get('flow_id'), None)
            if full_url != None :
                self.current_label.setText(f'请求地址: {full_url}')
            # 组合成完整的响应行字符串
            response_line = f"{packet.get('http_version')} {packet.get('status_code')} {packet.get('reason')}"
            # response_headers = [(k.encode("utf-8"), v.encode("utf-8")) for k, v in packet.get('headers').items()]
            response_headers = "\n".join([f"{k}: {v}" for k, v in packet.get('headers').items()])
            response_body = packet.get('body')
            self.message_display.setPlainText(f"{response_line}\n{response_headers}\n\n{response_body}")



    # 点击放过,将修改过的或者未修改的报文,返回给插件,插件更新以后,发送给服务器或者客户端
    def pass_packet(self):
        toast = QLabel('发送当前报文!!!', self)
        toast.setStyleSheet(
            "background-color: black; color: white; padding: 5px; border-radius: 100px;")
        toast.setAlignment(Qt.AlignCenter)
        toast.setWindowFlags(Qt.ToolTip)
        toast.setGeometry(self.width() // 2 - 100, self.height() // 2 - 20, 100, 80)
        toast.show()
        # 设置自动关闭
        QTimer.singleShot(500, toast.close)  # 2秒后自动关闭
        """放过按钮逻辑"""
        modified_data = self.message_display.toPlainText()
        if modified_data != '' :
            # 在display_redis_packets方法中, 存储了一个原值的全局变量, dict类型, 里边存储了mitmproxy唯一标识flow_id
            # 取出flow_id, 和解析成dict中的数据存储到一块, 写入到redis中, mitmproxy插件拿出flow_id找出原值进行修改, 再恢复抓包
            flow_id = self.current_flow.get('flow_id')
            parse_http_message_dict = self.parse_http_message(modified_data, self.current_flow.get('mitm_requst_response'))
            parse_http_message_dict['flow_id'] = flow_id
            # 同样获得原始值, 是否进行了base64处理, 说明是二进制
            mitm_isBase64 = self.current_flow.get('mitm_isBase64')
            parse_http_message_dict['mitm_isBase64'] = mitm_isBase64
            self.redisPyside.publish('pyside_channel', json.dumps(parse_http_message_dict))  # 通知 mitmproxy 读取, 解析出http报文转str
            self.redisPyside.set("need", "True")  # 确保 mitmproxy 可以读取
            print("已存入 Redis，等待 mitmproxy 读取")
            self.message_display.clear()
            self.current_label.clear()


    def parse_http_request(self, http_text):
        lines = http_text.split("\n")
        request_line = lines[0].split(" ")  # 第一行为请求行
        method, url_path, http_version = request_line[0], request_line[1], request_line[2]

        # 查找空行，分隔请求头和请求体
        empty_line_index = lines.index("") if "" in lines else len(lines)

        # 解析请求头
        headers = {}
        for line in lines[1:empty_line_index]:
            key, value = line.split(": ", 1)
            headers[key] = value

        # 解析请求体（如果有）
        body = "\n".join(lines[empty_line_index + 1:]) if empty_line_index + 1 < len(lines) else ""

        return {
            "method": method,
            "url_path": url_path,
            "http_version": http_version,
            "headers": headers,
            "body": body
        }


    def parse_http_response(self, http_text):
        lines = http_text.split("\n")
        response_line = lines[0].split(" ", 2)  # 第一行为响应行
        http_version, status_code, reason = response_line[0], response_line[1], response_line[2]

        # 查找空行，分隔响应头和响应体
        empty_line_index = lines.index("") if "" in lines else len(lines)

        # 解析响应头
        headers = {}
        for line in lines[1:empty_line_index]:
            key, value = line.split(": ", 1)
            headers[key] = value

        # 解析响应体（如果有）
        body = "\n".join(lines[empty_line_index + 1:]) if empty_line_index + 1 < len(lines) else ""

        return {
            "http_version": http_version,
            "status_code": status_code,
            "reason": reason,
            "headers": headers,
            "body": body
        }


    def parse_http_message(self, http_message: str, reqRes: str):
        """
        解析 HTTP 报文（请求 + 响应），返回请求和响应的字典
        """
        if reqRes == 'request' :
            request_dict = self.parse_http_request(http_message)
            # return request_dict
            return request_dict
        elif reqRes == 'response' :
            response_dict = self.parse_http_response(http_message)
            # return response_dict
            return response_dict




    def append_output_capture(self, text):
        self.message_display.append(text)
        # 限制行数为 max_lines
        lines = self.message_display.toPlainText().split("\n")
        if len(lines) > self.max_lines:
            # 删除多余的行
            self.message_display.setPlainText("\n".join(lines[-self.max_lines:]))
            # 将光标移动到文本末尾
            self.message_display.moveCursor(self.message_display.textCursor().End)




    def get_screen_size(self):
        if platform.system() == 'Windows':
            width, height = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
            return width, height
        else:
            width, height = (1200, 720)
            return width, height
            raise NotImplementedError("Unsupported platform")


    def init_globalConfig(self):
        # 测试用全局配置表globalConfig.yaml
        if not os.path.exists(ROOT_DIR + '/config/' + 'globalConfig.yaml'):

            yaml = YAML()
            # yaml表是list，这样为了防止，字段中的值和系统中特殊标记的值重复，[1]中的才是存储字段和对应值的dict
            # init_dataConfig 存储在config/__init__.py中
            with open(ROOT_DIR + '/config/' + 'globalConfig.yaml', 'w', encoding='utf-8') as f:
                # f.write(yaml.dump(init_global_config, Dumper=yaml.RoundTripDumper, allow_unicode=True))
                yaml.dump(init_global_config, f)
            self.message_display.append('当前测试系统,dataConfig.yaml生成完成!!!')


    def closeEvent(self, event):
        from datetime import datetime
        """捕获关闭事件并记录时间"""
        close_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # with open("close_time.log", "a") as log_file:
        #     log_file.write(f"Application closed at: {close_time}\n")
        self.run_shell_command_unset_proxy()
        print(f"Application closed at: {close_time}")
        super().closeEvent(event)

