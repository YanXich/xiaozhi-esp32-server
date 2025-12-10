"""
官方文档：https://milvus.io/docs/quickstart_mem0_with_milvus.md
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# 延迟导入，避免在模块加载时就尝试网络连接
Memory = None
connections = None
utility = None

def _import_dependencies():
    """延迟导入依赖，避免在模块加载时就尝试连接"""
    global Memory, connections, utility
    if Memory is None:
        try:
            from mem0 import Memory
            from pymilvus import connections, utility
        except ImportError as e:
            raise ImportError(f"请安装必要的依赖: pip install mem0ai pymilvus") from e


class Mem0MilvusIntegration:
    """
    Mem0 + Milvus 深度集成类
    
    特性：
    - 使用Mem0的智能记忆管理能力
    - 使用Milvus作为高性能向量存储后端
    - 支持本地和远程Milvus部署
    - 完整的记忆生命周期管理
    """
    
    def __init__(self, 
                 milvus_uri: str = "http://8.149.245.150:19530",
                 collection_name: str = "mem0_memories",
                 embedding_model_dims: int = 1536,
                 milvus_token: Optional[str] = None,
                 openai_api_key: Optional[str] = None,
                 openai_api_base: Optional[str] = None,
                 embedding_model: str = "text-embedding-ada-002"):
        """
        初始化Mem0+Milvus集成
        
        Args:
            milvus_uri: Milvus连接URI
                - 本地文件: "./milvus.db" (使用Milvus Lite)
                - 本地服务器: "http://localhost:19530"
                - 远程服务器: "http://8.149.245.150:19530"
            collection_name: Milvus集合名称
            embedding_model_dims: 嵌入向量维度
            milvus_token: Milvus认证令牌（可选）
            openai_api_key: API密钥（OpenAI或阿里云百炼）
            openai_api_base: API基础URL（用于阿里云百炼等兼容服务）
            embedding_model: 嵌入模型名称
        """
        self.milvus_uri = milvus_uri
        self.collection_name = collection_name
        self.embedding_model_dims = embedding_model_dims
        self.milvus_token = milvus_token
        self.embedding_model = embedding_model
        self.openai_api_key = openai_api_key
        self.openai_api_base = openai_api_base
        
        # 设置API配置
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
        
        # 设置自定义API基础URL（用于阿里云百炼等）
        if openai_api_base:
            os.environ["OPENAI_BASE_URL"] = openai_api_base
        
        # 配置日志
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 延迟初始化标志
        self._initialized = False
        self.memory = None
        self.config = None
    
    def _ensure_initialized(self):
        """确保已初始化，如果没有则进行初始化"""
        if not self._initialized:
            try:
                # 导入依赖
                _import_dependencies()
                
                # 初始化Mem0配置
                self._init_mem0_config()
                
                # 初始化Memory实例
                self.memory = Memory.from_config(self.config)
                
                # 确保集合已加载到内存中
                self._ensure_collection_loaded()
                
                self._initialized = True
                self.logger.info(f"Mem0+Milvus集成初始化完成")
                self.logger.info(f"Milvus URI: {self.milvus_uri}")
                self.logger.info(f"集合名称: {self.collection_name}")
                
            except Exception as e:
                self.logger.error(f"初始化Mem0+Milvus集成失败: {str(e)}")
                raise
    
    def _init_mem0_config(self):
        """初始化Mem0配置，使用Milvus作为向量存储后端"""
        self.config = {
            "vector_store": {
                "provider": "milvus",
                "config": {
                    "collection_name": self.collection_name,
                    "embedding_model_dims": str(self.embedding_model_dims),
                    "url": self.milvus_uri,
                }
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": self.embedding_model,
                }
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "qwen-turbo",  # 使用阿里云百炼的模型
                }
            },
            "version": "v1.1",
        }
        
        # 如果有认证令牌，添加到配置中
        if self.milvus_token:
            self.config["vector_store"]["config"]["token"] = self.milvus_token
            
        # 关键修复：直接在Mem0配置中指定API密钥和基础URL
        if self.openai_api_key:
            self.config["embedder"]["config"]["api_key"] = self.openai_api_key
            self.config["llm"]["config"]["api_key"] = self.openai_api_key
            
        if self.openai_api_base:
            self.config["embedder"]["config"]["openai_base_url"] = self.openai_api_base
            self.config["llm"]["config"]["openai_base_url"] = self.openai_api_base
    
    def _ensure_collection_loaded(self):
        """确保Milvus集合已加载到内存中"""
        try:
            # 连接到Milvus
            connections.connect(
                alias="default",
                uri=self.milvus_uri,
                token=self.milvus_token
            )
            
            # 检查集合是否存在
            if not utility.has_collection(self.collection_name):
                self.logger.warning(f"集合 {self.collection_name} 不存在")
                return
            
            # 获取集合对象
            from pymilvus import Collection
            collection = Collection(self.collection_name)
            
            # 检查集合是否已加载 - 修复：在 pymilvus 2.6.2 中使用字符串比较
            try:
                load_state = utility.load_state(self.collection_name)
                # 清理状态字符串，去除可能的空格和换行符
                load_state_clean = str(load_state).strip()
                self.logger.info(f"集合 {self.collection_name} 当前状态: '{load_state_clean}' (原始: {repr(load_state)})")
                
                # 在新版本中，load_state 返回字符串而不是枚举
                # 可能的状态值: "Loaded", "Loading", "NotLoad", "NotExist"
                if load_state_clean.lower() == "loaded":
                    self.logger.info(f"集合 {self.collection_name} 已在内存中，无需重新加载")
                elif load_state_clean.lower() in ["notload", "notexist", "not_load", "not_exist"]:
                    self.logger.info(f"正在加载集合 {self.collection_name} 到内存...")
                    collection.load()
                    
                    # 等待加载完成
                    import time
                    max_wait = 30  # 最多等待30秒
                    wait_time = 0
                    while wait_time < max_wait:
                        current_state = utility.load_state(self.collection_name)
                        current_state_clean = str(current_state).strip()
                        if current_state_clean.lower() == "loaded":
                            self.logger.info(f"集合 {self.collection_name} 已成功加载到内存")
                            break
                        time.sleep(1)
                        wait_time += 1
                    
                    if wait_time >= max_wait:
                        final_state = utility.load_state(self.collection_name)
                        final_state_clean = str(final_state).strip()
                        self.logger.warning(f"集合 {self.collection_name} 加载超时，当前状态: {final_state_clean}")
                elif load_state_clean.lower() == "loading":
                    self.logger.info(f"集合 {self.collection_name} 正在加载中，等待完成...")
                    # 等待正在进行的加载完成
                    import time
                    max_wait = 30
                    wait_time = 0
                    while wait_time < max_wait:
                        current_state = utility.load_state(self.collection_name)
                        current_state_clean = str(current_state).strip()
                        if current_state_clean.lower() == "loaded":
                            self.logger.info(f"集合 {self.collection_name} 加载完成")
                            break
                        time.sleep(1)
                        wait_time += 1
                    
                    if wait_time >= max_wait:
                        final_state = utility.load_state(self.collection_name)
                        final_state_clean = str(final_state).strip()
                        self.logger.warning(f"等待集合 {self.collection_name} 加载超时，当前状态: {final_state_clean}")
                else:
                    self.logger.warning(f"集合 {self.collection_name} 状态未知: '{load_state_clean}' (原始: {repr(load_state)})，尝试加载...")
                    collection.load()
                    
            except AttributeError as ae:
                # 如果 utility.load_state 不存在，尝试使用集合的 load 方法
                self.logger.warning(f"utility.load_state 方法不可用: {ae}")
                self.logger.info(f"尝试直接加载集合 {self.collection_name}")
                collection.load()
                self.logger.info(f"集合 {self.collection_name} 加载完成")
                
        except Exception as e:
            self.logger.error(f"确保集合加载失败: {str(e)}")
            # 不抛出异常，让系统继续运行
    
    def add_memory(self, 
                   messages: str, 
                   user_id: str, 
                   metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        添加记忆
        
        Mem0会智能分析输入内容，决定是否需要存储以及如何存储
        Milvus负责高效的向量存储
        
        Args:
            messages: 要记忆的内容
            user_id: 用户ID
            metadata: 可选的元数据
            
        Returns:
            添加结果，包含记忆ID和处理信息
        """
        self._ensure_initialized()
        
        # 添加重试机制
        max_retries = 3
        retry_delay = 1  # 秒
        
        for attempt in range(max_retries):
            try:
                result = self.memory.add(
                    messages=messages,
                    user_id=user_id,
                    metadata=metadata or {}
                )
                
                self.logger.info(f"为用户 {user_id} 添加记忆成功")
                return result
                
            except Exception as e:
                error_msg = str(e)
                self.logger.warning(f"添加记忆失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
                
                # 检查是否是网络连接错误
                if "Connection error" in error_msg or "Network is unreachable" in error_msg or "ConnectError" in error_msg:
                    if attempt < max_retries - 1:  # 不是最后一次尝试
                        import time
                        self.logger.info(f"网络连接错误，{retry_delay}秒后重试...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                
                # 如果是最后一次尝试或非网络错误，直接抛出异常
                if attempt == max_retries - 1:
                    self.logger.error(f"添加记忆最终失败: {error_msg}")
                    raise
                else:
                    # 其他类型的错误，立即抛出
                    raise
    
    def search_memories(self, 
                       query: str, 
                       user_id: str, 
                       limit: int = 5) -> List[Dict[str, Any]]:
        """
        搜索记忆
        
        基于语义相似度搜索相关记忆
        
        Args:
            query: 搜索查询
            user_id: 用户ID
            limit: 返回结果数量限制
            
        Returns:
            相关记忆列表
        """
        self._ensure_initialized()
        try:
            results = self.memory.search(
                query=query,
                user_id=user_id,
                limit=limit
            )
            
            # Mem0返回的是字典格式 {'results': [...]}
            memories = results.get('results', []) if isinstance(results, dict) else results
            
            self.logger.info(f"为用户 {user_id} 搜索到 {len(memories)} 条相关记忆")
            return memories
            
        except Exception as e:
            self.logger.error(f"搜索记忆失败: {str(e)}")
            return []
    
    def get_all_memories(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户的所有记忆
        
        Args:
            user_id: 用户ID
            
        Returns:
            包含所有记忆的字典
        """
        self._ensure_initialized()
        try:
            memories = self.memory.get_all(user_id=user_id)
            self.logger.info(f"获取用户 {user_id} 的所有记忆: {len(memories.get('results', []))} 条")
            return memories
            
        except Exception as e:
            self.logger.error(f"获取记忆失败: {str(e)}")
            raise
    
    def update_memory(self, 
                     memory_id: str, 
                     data: str) -> Dict[str, Any]:
        """
        更新记忆
        
        Args:
            memory_id: 记忆ID
            data: 新的记忆内容
            
        Returns:
            更新结果
        """
        self._ensure_initialized()
        try:
            result = self.memory.update(memory_id=memory_id, data=data)
            self.logger.info(f"记忆 {memory_id} 更新成功")
            return result
            
        except Exception as e:
            self.logger.error(f"更新记忆失败: {str(e)}")
            raise
    
    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        删除记忆
        
        Args:
            memory_id: 要删除的记忆ID
            
        Returns:
            删除结果
        """
        self._ensure_initialized()
        try:
            result = self.memory.delete(memory_id=memory_id)
            self.logger.info(f"记忆 {memory_id} 删除成功")
            return result
            
        except Exception as e:
            self.logger.error(f"删除记忆失败: {str(e)}")
            raise
    
    def get_memory_history(self, memory_id: str) -> List[Dict[str, Any]]:
        """
        获取记忆历史
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            记忆历史列表
        """
        self._ensure_initialized()
        try:
            history = self.memory.history(memory_id=memory_id)
            self.logger.info(f"获取记忆 {memory_id} 的历史: {len(history)} 条记录")
            return history
            
        except Exception as e:
            self.logger.error(f"获取记忆历史失败: {str(e)}")
            raise
    
    def get_milvus_stats(self) -> Dict[str, Any]:
        """
        获取Milvus统计信息
        
        Returns:
            统计信息字典
        """
        self._ensure_initialized()
        try:
            # 这里可以添加更多Milvus统计信息的获取逻辑
            stats = {
                "milvus_uri": self.milvus_uri,
                "collection_name": self.collection_name,
                "embedding_dims": self.embedding_model_dims,
                "timestamp": datetime.now().isoformat()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取Milvus统计信息失败: {str(e)}")
            raise
    
    def reset_memories(self, user_id: str) -> Dict[str, Any]:
        """
        重置用户记忆
        
        Args:
            user_id: 用户ID
            
        Returns:
            重置结果
        """
        self._ensure_initialized()
        try:
            result = self.memory.reset(user_id=user_id)
            self.logger.info(f"用户 {user_id} 的记忆已重置")
            return result
            
        except Exception as e:
            self.logger.error(f"重置记忆失败: {str(e)}")
            raise


class MemoryManager:
    """
    高级记忆管理器
    
    提供更高级的记忆管理功能，包括：
    - 智能记忆分类
    - 记忆重要性评估
    - 自动记忆清理
    """
    
    def __init__(self, integration: Mem0MilvusIntegration):
        self.integration = integration
        self.logger = logging.getLogger(__name__)
    
    def add_categorized_memory(self, 
                              content: str, 
                              user_id: str, 
                              category: str,
                              importance: int = 5) -> Dict[str, Any]:
        """
        添加分类记忆
        
        Args:
            content: 记忆内容
            user_id: 用户ID
            category: 记忆类别
            importance: 重要性评分 (1-10)
            
        Returns:
            添加结果
        """
        metadata = {
            "category": category,
            "importance": importance,
            "created_at": datetime.now().isoformat()
        }
        
        return self.integration.add_memory(
            messages=content,
            user_id=user_id,
            metadata=metadata
        )
    
    def get_memories_by_category(self, 
                                user_id: str, 
                                category: str) -> List[Dict[str, Any]]:
        """
        按类别获取记忆
        
        Args:
            user_id: 用户ID
            category: 记忆类别
            
        Returns:
            该类别的记忆列表
        """
        all_memories = self.integration.get_all_memories(user_id)
        
        categorized_memories = []
        for memory in all_memories.get('results', []):
            if memory.get('metadata', {}).get('category') == category:
                categorized_memories.append(memory)
        
        return categorized_memories
    
    def get_important_memories(self, 
                              user_id: str, 
                              min_importance: int = 7) -> List[Dict[str, Any]]:
        """
        获取重要记忆
        
        Args:
            user_id: 用户ID
            min_importance: 最小重要性评分
            
        Returns:
            重要记忆列表
        """
        all_memories = self.integration.get_all_memories(user_id)
        
        important_memories = []
        for memory in all_memories.get('results', []):
            importance = memory.get('metadata', {}).get('importance', 0)
            if importance >= min_importance:
                important_memories.append(memory)
        
        return important_memories


# 使用示例和测试函数
def example_usage():
    """使用示例"""
    
    # 方式1: 使用OpenAI API
    # integration = Mem0MilvusIntegration(
    #     milvus_uri="./milvus.db",
    #     collection_name="user_memories", 
    #     embedding_model_dims=1536,
    #     openai_api_key="your-openai-api-key"
    # )
    
    # 方式2: 使用阿里云百炼API（推荐）
    integration = Mem0MilvusIntegration(
        milvus_uri="http://8.149.245.150:19530",  # 你的Milvus服务器
        collection_name="user_memories",
        embedding_model_dims=1536,  # 根据阿里云百炼模型调整
        openai_api_key="sk-4790da8d470049e9be356a6c0179e5b9",  # 阿里云百炼API密钥
        openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 阿里云百炼兼容接口
        embedding_model="text-embedding-v1"  # 阿里云百炼嵌入模型
    )
    
    # 初始化高级管理器
    manager = MemoryManager(integration)
    
    user_id = "alice"
    
    print("=== Mem0 + Milvus 集成示例 ===")
    
    # 1. 添加记忆
    print("\n1. 添加记忆...")
    result1 = manager.add_categorized_memory(
        content="我喜欢在周末打网球，这是我的爱好",
        user_id=user_id,
        category="hobbies",
        importance=8
    )
    print(f"添加结果: {result1}")
    
    result2 = manager.add_categorized_memory(
        content="我在学习线性代数，11月20日有期中考试",
        user_id=user_id,
        category="study",
        importance=9
    )
    print(f"添加结果: {result2}")
    
    # 2. 搜索记忆
    print("\n2. 搜索记忆...")
    search_results = integration.search_memories(
        query="网球运动",
        user_id=user_id,
        limit=3
    )
    print(f"搜索结果: {search_results}")
    
    # 3. 获取所有记忆
    print("\n3. 获取所有记忆...")
    all_memories = integration.get_all_memories(user_id)
    print(f"所有记忆: {all_memories}")
    
    # 4. 按类别获取记忆
    print("\n4. 按类别获取记忆...")
    hobby_memories = manager.get_memories_by_category(user_id, "hobbies")
    print(f"爱好类记忆: {hobby_memories}")
    
    # 5. 获取重要记忆
    print("\n5. 获取重要记忆...")
    important_memories = manager.get_important_memories(user_id, min_importance=8)
    print(f"重要记忆: {important_memories}")
    
    # 6. 获取Milvus统计信息
    print("\n6. Milvus统计信息...")
    stats = integration.get_milvus_stats()
    print(f"统计信息: {stats}")


if __name__ == "__main__":
    example_usage()


# 导入系统需要的 MemoryProvider 类
# from .milvus_provider import MemoryProvider  # 注释掉避免循环导入