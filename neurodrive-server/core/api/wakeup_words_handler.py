from typing import Dict, Any
from aiohttp import web
from core.api.base_handler import BaseHandler
from core.utils.user_wakeup_words import user_wakeup_words_manager
from config.logger import setup_logging
import json

TAG = __name__


class WakeupWordsHandler(BaseHandler):
    """车载设备唤醒词API处理器"""
    
    def __init__(self):
        # 传入空配置字典，因为这个处理器不需要特定配置
        super().__init__({})
        self.logger = setup_logging()
    

    
    async def get_effective_wakeup_words(self, request) -> web.Response:
        """获取有效唤醒词（仅车载设备唤醒词）"""
        try:
            device_id = request.match_info.get('device_mac')  # 保持API路径参数名不变
            if not device_id:
                response_data = self.error_response("设备ID不能为空", 400)
                response = web.json_response(response_data, status=400)
                self._add_cors_headers(response)
                return response
            
            # 获取有效唤醒词
            effective_words = await user_wakeup_words_manager.get_effective_wakeup_words(device_id)
            
            response_data = self.success_response({
                "deviceId": device_id,
                "effectiveWakeupWords": effective_words,
                "count": len(effective_words)
            })
            response = web.json_response(response_data)
            self._add_cors_headers(response)
            return response
        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取有效唤醒词失败: {e}")
            response_data = self.error_response(f"获取有效唤醒词失败: {str(e)}", 500)
            response = web.json_response(response_data, status=500)
            self._add_cors_headers(response)
            return response
    
    async def clear_cache(self, request) -> web.Response:
        """清除指定设备的唤醒词缓存"""
        try:
            device_id = request.match_info.get('device_mac')  # 保持API路径参数名不变
            if not device_id:
                response_data = self.error_response("设备ID不能为空", 400)
                response = web.json_response(response_data, status=400)
                self._add_cors_headers(response)
                return response
            
            # 清除缓存
            user_wakeup_words_manager.clear_cache(device_id)
            
            response_data = self.success_response({
                "deviceId": device_id,
                "message": "缓存清除成功"
            })
            response = web.json_response(response_data)
            self._add_cors_headers(response)
            return response
        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"清除缓存失败: {e}")
            response_data = self.error_response(f"清除缓存失败: {str(e)}", 500)
            response = web.json_response(response_data, status=500)
            self._add_cors_headers(response)
            return response
    
    async def get_car_wakeup_word(self, request) -> web.Response:
        """获取车载设备唤醒词（通过设备ID）"""
        try:
            device_id = request.match_info.get('device_mac')  # 保持API路径参数名不变
            if not device_id:
                response_data = self.error_response("设备ID不能为空", 400)
                response = web.json_response(response_data, status=400)
                self._add_cors_headers(response)
                return response
            
            # 获取车载唤醒词
            car_word = await user_wakeup_words_manager.get_car_wakeup_word(device_id)
            
            response_data = self.success_response({
                "deviceId": device_id,
                "carWakeupWord": car_word,
                "hasWakeupWord": car_word is not None
            })
            response = web.json_response(response_data)
            self._add_cors_headers(response)
            return response
        
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"获取车载唤醒词失败: {e}")
            response_data = self.error_response(f"获取车载唤醒词失败: {str(e)}", 500)
            response = web.json_response(response_data, status=500)
            self._add_cors_headers(response)
            return response
    

    
    async def handle_options(self, request) -> web.Response:
        """处理CORS预检请求"""
        response = web.Response()
        self._add_cors_headers(response)
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response
    
    def success_response(self, data: Any) -> Dict[str, Any]:
        """成功响应"""
        return {
            "success": True,
            "data": data
        }
    
    def error_response(self, message: str, code: int = 500) -> Dict[str, Any]:
        """错误响应"""
        return {
            "success": False,
            "message": message
        }