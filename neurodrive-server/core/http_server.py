import asyncio
from aiohttp import web
from config.logger import setup_logging
from core.api.ota_handler import OTAHandler
from core.api.vision_handler import VisionHandler
from core.api.device_control_handler import DeviceControlHandler
from core.api.device_status_handler import DeviceStatusHandler
from core.api.group_handler import GroupHandler  # 添加导入
from core.api.connection_handler import ConnectionHandler  # 添加连接管理导入
from core.api.wakeup_words_handler import WakeupWordsHandler  # 添加唤醒词管理导入
from core.api.ogg_download_handler import OggDownloadHandler # OGG文件下载
from core.api.text_message_handler import TextMessageHandler  # 添加文字消息处理导入
from core.api.peripheral_control_handler import PeripheralControlHandler  # 添加外设控制处理导入
from core.api.system_control_handler import SystemControlHandler  # 添加系统控制处理导入


TAG = __name__


class SimpleHttpServer:
    def __init__(self, config: dict, websocket_server=None):
        self.config = config
        self.logger = setup_logging()
        self.ota_handler = OTAHandler(config)
        self.vision_handler = VisionHandler(config)
        self.device_control_handler = DeviceControlHandler(config, websocket_server)
        self.device_status_handler = DeviceStatusHandler(config, websocket_server)
        self.group_handler = GroupHandler(config, websocket_server)  # 添加处理器实例
        self.connection_handler = ConnectionHandler(config, websocket_server)  # 添加连接管理处理器
        self.wakeup_words_handler = WakeupWordsHandler()  # 添加唤醒词管理处理器
        self.ogg_download_handler = OggDownloadHandler(config, websocket_server) # OGG文件下载
        self.text_message_handler = TextMessageHandler(config, websocket_server)  # 添加文字消息处理器
        self.peripheral_control_handler = PeripheralControlHandler(config, websocket_server)  # 添加外设控制处理器
        self.system_control_handler = SystemControlHandler(config, websocket_server)  # 添加系统控制处理器

    def _get_websocket_url(self, local_ip: str, port: int) -> str:
        """获取websocket地址

        Args:
            local_ip: 本地IP地址
            port: 端口号

        Returns:
            str: websocket地址
        """
        server_config = self.config["server"]
        websocket_config = server_config.get("websocket")

        if websocket_config and "你" not in websocket_config:
            return websocket_config
        else:
            return f"ws://{local_ip}:{port}/xiaozhi/v1/"

    async def start(self):
        server_config = self.config["server"]
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("http_port", 18003))

        if port:
            app = web.Application()

            read_config_from_api = server_config.get("read_config_from_api", False)
            print("ota task: ....", read_config_from_api, host, port)

            if not read_config_from_api:
                # 如果没有开启智控台，只是单模块运行，就需要再添加简单OTA接口，用于下发websocket接口
                app.add_routes(
                    [
                        web.get("/xiaozhi/ota/", self.ota_handler.handle_get),
                        web.post("/xiaozhi/ota/", self.ota_handler.handle_post),
                        web.options("/xiaozhi/ota/", self.ota_handler.handle_post),
                    ]
                )
            # 添加路由
            app.add_routes(
                [
                    web.get("/mcp/vision/explain", self.vision_handler.handle_get),
                    web.post("/mcp/vision/explain", self.vision_handler.handle_post),
                    web.options("/mcp/vision/explain", self.vision_handler.handle_post),
                    # 添加设备控制路由
                    web.post("/xiaozhi/device/control", self.device_control_handler.handle_post),
                    web.options("/xiaozhi/device/control", self.device_control_handler.handle_options),
                    # 添加设备状态路由
                    web.get("/xiaozhi/device/status", self.device_status_handler.handle_get),
                    web.post("/xiaozhi/device/status", self.device_status_handler.handle_post),
                    web.options("/xiaozhi/device/status", self.device_status_handler.handle_options),
                    # 添加群聊管理路由
                    web.post("/xiaozhi/group/create", self.group_handler.handle_post),
                    web.options("/xiaozhi/group/create", self.group_handler.handle_options),
                    web.post("/xiaozhi/group/join", self.group_handler.handle_post),
                    web.options("/xiaozhi/group/join", self.group_handler.handle_options),
                    web.post("/xiaozhi/group/leave", self.group_handler.handle_post),
                    web.options("/xiaozhi/group/leave", self.group_handler.handle_options),
                    web.get("/xiaozhi/group/list", self.group_handler.handle_get),
                    web.options("/xiaozhi/group/list", self.group_handler.handle_options),
                    # 添加连接管理路由
                    web.post("/xiaozhi/connection/manage", self.connection_handler.handle_post),
                    web.options("/xiaozhi/connection/manage", self.connection_handler.handle_options),
                    # 添加车载设备唤醒词路由
                    web.get("/xiaozhi/wakeup-words/effective/{device_mac}", self.wakeup_words_handler.get_effective_wakeup_words),
                    web.get("/xiaozhi/wakeup-words/car/{device_mac}", self.wakeup_words_handler.get_car_wakeup_word),
                    web.post("/xiaozhi/wakeup-words/cache/clear/{device_mac}", self.wakeup_words_handler.clear_cache),
                    web.options("/xiaozhi/wakeup-words/{path:.*}", self.wakeup_words_handler.handle_options),
                    # ogg音频文件预下载
                    web.get("/xiaozhi/voice_files", self.ogg_download_handler.handle_get),
                    # 添加文字消息接收路由
                    web.post("/xiaozhi/message/text", self.text_message_handler.handle_post),
                    web.get("/xiaozhi/message/text", self.text_message_handler.handle_get),
                    web.options("/xiaozhi/message/text", self.text_message_handler.handle_options),
                    # 添加外设控制路由
                    web.post("/xiaozhi/peripheral/control", self.peripheral_control_handler.handle_post),
                    web.get("/xiaozhi/peripheral/status", self.peripheral_control_handler.handle_get),
                    web.options("/xiaozhi/peripheral/control", self.peripheral_control_handler.handle_options),
                    web.options("/xiaozhi/peripheral/status", self.peripheral_control_handler.handle_options),
                    # 添加系统控制路由
                    web.post("/xiaozhi/system/control", self.system_control_handler.handle_post),
                    web.get("/xiaozhi/system/control", self.system_control_handler.handle_get),
                    web.options("/xiaozhi/system/control", self.system_control_handler.handle_options),
                ]
            )

            # 运行服务
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()

            # 保持服务运行
            while True:
                await asyncio.sleep(3600)  # 每隔 1 小时检查一次
