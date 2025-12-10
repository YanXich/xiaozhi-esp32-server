import time
import asyncio
from typing import List, Optional, Dict
from config.manage_api_client import get_car_wakeup_word
from core.utils.cache.manager import cache_manager, CacheType

TAG = __name__


class UserWakeupWordsManager:
    """车载设备唤醒词管理器"""
    
    def __init__(self):
        self._cache_ttl = 300  # 缓存5分钟
    
    def _get_cache_key(self, device_id: str, cache_type: str) -> str:
        """生成缓存键"""
        return f"wakeup_words_{cache_type}_{device_id}"
    

    
    async def get_car_wakeup_word(self, device_id: str) -> Optional[str]:
        """获取车载设备唤醒词（通过设备ID）"""
        if not device_id:
            return None
        
        cache_key = self._get_cache_key(device_id, "car")
        
        # 尝试从缓存获取
        cached_word = cache_manager.get(CacheType.WAKEUP_WORDS, cache_key)
        if cached_word is not None:
            return cached_word
        
        try:
            # 从车载设备API获取唤醒词
            car_name = await asyncio.to_thread(get_car_wakeup_word, device_id)
            if car_name:
                # 缓存结果
                cache_manager.set(CacheType.WAKEUP_WORDS, cache_key, car_name, ttl=self._cache_ttl)
                return car_name
        except Exception as e:
            print(f"获取车载唤醒词失败: {e}")
        
        # 失败时缓存None，避免频繁请求
        cache_manager.set(CacheType.WAKEUP_WORDS, cache_key, None, ttl=60)
        return None
    

    
    async def get_effective_wakeup_words(self, device_id: str = None) -> List[str]:
        """获取有效唤醒词（仅车载设备唤醒词）"""
        if not device_id:
            # 没有设备ID时返回默认唤醒词
            return self.validate_wakeup_words(["小柚"])
        
        car_word = await self.get_car_wakeup_word(device_id)
        if car_word:
            return self.validate_wakeup_words([car_word])
        
        # 设备ID查找失败时返回默认唤醒词
        print(f"设备ID {device_id} 查找失败，使用默认唤醒词: 小柚")
        return self.validate_wakeup_words(["小柚"])
    
    def clear_cache(self, device_id: str):
        """清除指定设备的唤醒词缓存"""
        if not device_id:
            return
        
        car_key = self._get_cache_key(device_id, "car")
        cache_manager.delete(CacheType.WAKEUP_WORDS, car_key)
    
    def validate_wakeup_words(self, words: List[str]) -> List[str]:
        """验证和过滤唤醒词"""
        if not words:
            return []
        
        valid_words = []
        for word in words:
            word = word.strip()
            # 基本验证：长度在1-20字符之间，支持中文、英文、数字
            if 1 <= len(word) <= 20 and word:
                # 检查是否包含有效字符（中文、英文、数字、空格）
                cleaned_word = word.replace(" ", "")
                if cleaned_word and all(c.isalnum() or '\u4e00' <= c <= '\u9fff' for c in cleaned_word):
                    valid_words.append(word)
        
        return valid_words


# 创建全局实例
user_wakeup_words_manager = UserWakeupWordsManager()