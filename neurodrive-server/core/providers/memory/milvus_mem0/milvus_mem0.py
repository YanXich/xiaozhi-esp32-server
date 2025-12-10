"""
将 Mem0MilvusIntegration 适配到现有的 MemoryProviderBase 接口
实现本地化的智能记忆管理，使用 Milvus 作为向量存储后端
"""

import re
import traceback
import time
import hashlib
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from collections import defaultdict
from difflib import SequenceMatcher

try:
    from ..base import MemoryProviderBase, logger
except ImportError:
    # 如果相对导入失败，尝试直接导入
    try:
        from base import MemoryProviderBase, logger
    except ImportError:
        # 创建一个简单的基类和日志器用于测试
        import logging
        logger = logging.getLogger(__name__)
        
        class MemoryProviderBase:
            def __init__(self, config, summary_memory=None):
                pass
            
            def init_memory(self, role_id, summary_memory):
                """
                初始化用户记忆
                
                Args:
                    role_id: 用户角色ID
                    summary_memory: 摘要记忆
                """
                self.role_id = role_id
                self.summary_memory = summary_memory
                
                if self.use_memory:
                    logger.info(f"[{TAG}] 初始化用户 {role_id} 的记忆")
                    
                    # 异步预加载用户记忆
                    if self.enable_cache:
                        asyncio.create_task(self._preload_user_memories())
            
            async def _preload_user_memories(self):
                """异步预加载用户的常用记忆"""
                try:
                    logger.info(f"[{TAG}] 开始预加载用户 {self.role_id} 的记忆...")
                    
                    # 获取用户的所有记忆
                    all_memories = self.integration.get_all_memories(self.role_id)
                    memories_list = all_memories.get('results', [])
                    
                    if not memories_list:
                        logger.info(f"[{TAG}] 用户 {self.role_id} 暂无记忆数据")
                        return
                    
                    # 构建记忆索引
                    self.memory_index = {
                        'total_count': len(memories_list),
                        'categories': defaultdict(list),
                        'keywords': defaultdict(list),
                        'recent_memories': [],
                        'important_memories': []
                    }
                    
                    # 分析和索引记忆
                    for memory in memories_list:
                        memory_text = memory.get("memory", "")
                        metadata = memory.get("metadata", {})
                        category = metadata.get("category", "general")
                        importance = metadata.get("importance", 5)
                        created_at = metadata.get("created_at", "")
                        
                        # 按类别分组
                        self.memory_index['categories'][category].append(memory)
                        
                        # 提取关键词
                        keywords = self._extract_keywords(memory_text)
                        for keyword in keywords:
                            self.memory_index['keywords'][keyword].append(memory)
                        
                        # 重要记忆
                        if importance >= 8:
                            self.memory_index['important_memories'].append(memory)
                        
                        # 最近记忆（按时间排序）
                        if created_at:
                            self.memory_index['recent_memories'].append((created_at, memory))
                    
                    # 排序最近记忆
                    self.memory_index['recent_memories'].sort(key=lambda x: x[0], reverse=True)
                    self.memory_index['recent_memories'] = [mem for _, mem in self.memory_index['recent_memories'][:20]]
                    
                    self.last_index_update = time.time()
                    
                    logger.info(f"[{TAG}] 预加载完成: {len(memories_list)} 条记忆, "
                               f"{len(self.memory_index['categories'])} 个类别, "
                               f"{len(self.memory_index['important_memories'])} 条重要记忆")
                    
                except Exception as e:
                    logger.error(f"[{TAG}] 预加载记忆失败: {str(e)}")
            
            def _extract_keywords(self, text: str) -> List[str]:
                """从文本中提取关键词"""
                # 简单的关键词提取（可以后续优化为更复杂的NLP方法）
                import jieba
                
                try:
                    # 使用jieba分词
                    words = jieba.lcut(text)
                    
                    # 过滤停用词和短词
                    stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
                    keywords = [word for word in words if len(word) > 1 and word not in stop_words]
                    
                    return keywords[:10]  # 最多返回10个关键词
                    
                except ImportError:
                    # 如果jieba不可用，使用简单的分割方法
                    words = re.findall(r'[\u4e00-\u9fff]+', text)  # 提取中文词汇
                    return [word for word in words if len(word) > 1][:10]
                except Exception as e:
                    logger.warning(f"[{TAG}] 关键词提取失败: {e}")
                    return []
            
            async def query_memory(self, query: str) -> str:
                """
                查询相关记忆（优化版本）
                
                Args:
                    query: 查询字符串
                    
                Returns:
                    格式化的记忆字符串
                """
                if not self.use_memory:
                    return ""
                
                start_time = time.time()
                
                try:
                    # 1. 检查缓存
                    if self.query_cache:
                        cached_result = self.query_cache.get(query, self.role_id)
                        if cached_result is not None:
                            query_time = time.time() - start_time
                            logger.info(f"[{TAG}] 缓存命中，查询耗时: {query_time:.3f}s")
                            return cached_result
                    
                    # 2. 快速本地匹配（如果有预加载的索引）
                    local_results = await self._quick_local_search(query)
                    
                    # 3. 生成查询变体（模糊匹配）
                    query_variants = [query]
                    if self.fuzzy_matcher:
                        query_variants = self.fuzzy_matcher.get_similar_queries(query)
                        logger.debug(f"[{TAG}] 生成查询变体: {query_variants}")
                    
                    # 4. 并行查询多个变体
                    all_results = list(local_results)  # 包含本地快速匹配结果
                    search_tasks = []
                    
                    # 限制向量搜索的查询数量以控制延迟
                    max_vector_queries = 2 if local_results else 3
                    
                    for variant in query_variants[:max_vector_queries]:
                        task = self._search_single_query(variant)
                        search_tasks.append(task)
                    
                    # 等待所有查询完成
                    if search_tasks:
                        results_list = await asyncio.gather(*search_tasks, return_exceptions=True)
                        
                        for results in results_list:
                            if isinstance(results, list):
                                all_results.extend(results)
                    
                    # 5. 去重和排序
                    unique_results = self._deduplicate_results(all_results)
                    
                    # 6. 格式化结果
                    formatted_result = self._format_memory_results(unique_results)
                    
                    # 7. 缓存结果
                    if self.query_cache and formatted_result:
                        self.query_cache.set(query, self.role_id, formatted_result)
                    
                    query_time = time.time() - start_time
                    logger.info(f"[{TAG}] 查询完成，找到 {len(unique_results)} 条记忆，耗时: {query_time:.3f}s")
                    
                    return formatted_result
                    
                except Exception as e:
                    logger.error(f"[{TAG}] 查询记忆失败: {str(e)}")
                    logger.error(f"[{TAG}] 详细错误: {traceback.format_exc()}")
                    return ""
            
            async def _quick_local_search(self, query: str) -> List[Dict[str, Any]]:
                """快速本地搜索，基于预加载的索引"""
                if not self.memory_index or not query:
                    return []
                
                try:
                    local_matches = []
                    query_lower = query.lower()
                    
                    # 1. 关键词匹配
                    query_keywords = self._extract_keywords(query)
                    for keyword in query_keywords:
                        if keyword in self.memory_index['keywords']:
                            local_matches.extend(self.memory_index['keywords'][keyword])
                    
                    # 2. 文本包含匹配
                    for category_memories in self.memory_index['categories'].values():
                        for memory in category_memories:
                            memory_text = memory.get("memory", "").lower()
                            if query_lower in memory_text or any(kw in memory_text for kw in query_keywords):
                                local_matches.append(memory)
                    
                    # 3. 模糊匹配
                    if self.fuzzy_matcher:
                        for category_memories in self.memory_index['categories'].values():
                            for memory in category_memories:
                                memory_text = memory.get("memory", "")
                                similarity = self.fuzzy_matcher.calculate_similarity(query, memory_text)
                                if similarity > self.similarity_threshold:
                                    # 添加相似度分数
                                    memory_copy = memory.copy()
                                    memory_copy['local_similarity'] = similarity
                                    local_matches.append(memory_copy)
                    
                    # 去重并按相似度排序
                    unique_local = self._deduplicate_results(local_matches)
                    
                    logger.debug(f"[{TAG}] 本地快速匹配找到 {len(unique_local)} 条结果")
                    return unique_local[:3]  # 最多返回3条本地匹配结果
                    
                except Exception as e:
                    logger.warning(f"[{TAG}] 本地快速搜索失败: {e}")
                    return []
            
            async def _search_single_query(self, query: str) -> List[Dict[str, Any]]:
                """执行单个查询"""
                try:
                    results = self.integration.search_memories(
                        query=query,
                        user_id=self.role_id,
                        limit=5
                    )
                    return results if results else []
                except Exception as e:
                    logger.warning(f"[{TAG}] 单个查询失败 '{query}': {e}")
                    return []
            
            def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                """去重查询结果"""
                seen_memories = set()
                unique_results = []
                
                for result in results:
                    memory_text = result.get("memory", "")
                    if memory_text and memory_text not in seen_memories:
                        seen_memories.add(memory_text)
                        unique_results.append(result)
                
                # 按相关性排序（优先本地相似度，然后是向量搜索分数）
                def sort_key(x):
                    local_sim = x.get("local_similarity", 0)
                    vector_score = x.get("score", 0)
                    return (local_sim * 0.6 + vector_score * 0.4)  # 加权排序
                unique_results.sort(key=sort_key, reverse=True)
                
                return unique_results[:5]  # 最多返回5条
            
            def _format_memory_results(self, results: List[Dict[str, Any]]) -> str:
                """格式化记忆结果"""
                if not results:
                    return ""
                
                memories = []
                for entry in results:
                    memory_text = entry.get("memory", "")
                    metadata = entry.get("metadata", {})
                    created_at = metadata.get("created_at", "")
                    
                    if memory_text:
                        if created_at:
                            try:
                                # 格式化时间戳
                                formatted_time = created_at.split("T")[0] + " " + created_at.split("T")[1][:5]
                                memories.append(f"[{formatted_time}] {memory_text}")
                            except:
                                memories.append(f"- {memory_text}")
                        else:
                            memories.append(f"- {memory_text}")
                
                return "\n".join(memories)
            
            def get_query_performance_stats(self) -> Dict[str, Any]:
                """获取查询性能统计"""
                stats = {
                    "cache_enabled": self.enable_cache,
                    "fuzzy_matching_enabled": self.enable_fuzzy_matching,
                    "memory_index_loaded": bool(self.memory_index),
                    "last_index_update": self.last_index_update
                }
                
                if self.query_cache:
                    stats.update({
                        "cache_size": len(self.query_cache.cache),
                        "cache_max_size": self.query_cache.max_size,
                        "cache_ttl": self.query_cache.ttl
                    })
                if self.memory_index:
                    stats.update({
                        "indexed_memories": self.memory_index.get('total_count', 0),
                        "categories_count": len(self.memory_index.get('categories', {})),
                        "important_memories_count": len(self.memory_index.get('important_memories', [])),
                        "keywords_count": len(self.memory_index.get('keywords', {}))
                    })
                return stats

# 导入 Mem0MilvusIntegration 和 MemoryManager 类
from .milvus_provider import Mem0MilvusIntegration, MemoryManager

try:
    from core.utils.util import check_model_key
except ImportError:
    # 如果导入失败，创建一个简单的检查函数
    def check_model_key(api_key, api_type="openai"):
        return api_key is not None and len(api_key) > 0

TAG = __name__


class QueryCache:
    """查询缓存类，用于缓存查询结果以提高性能"""
    
    def __init__(self, max_size: int = 100, ttl: int = 300):
        """
        初始化查询缓存
        
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存生存时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_times = {}
        
    def _get_cache_key(self, query: str, user_id: str) -> str:
        """生成缓存键"""
        content = f"{user_id}:{query.lower().strip()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, query: str, user_id: str) -> Optional[str]:
        """获取缓存的查询结果"""
        key = self._get_cache_key(query, user_id)
        
        if key in self.cache:
            cached_time, result = self.cache[key]
            
            # 检查是否过期
            if time.time() - cached_time < self.ttl:
                self.access_times[key] = time.time()
                logger.debug(f"[{TAG}] 缓存命中: {query[:50]}...")
                return result
            else:
                # 过期，删除缓存
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
        
        return None
    
    def set(self, query: str, user_id: str, result: str):
        """设置缓存"""
        key = self._get_cache_key(query, user_id)
        
        # 如果缓存已满，删除最久未访问的条目
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[key] = (time.time(), result)
        self.access_times[key] = time.time()
        logger.debug(f"[{TAG}] 缓存设置: {query[:50]}...")
    
    def _evict_oldest(self):
        """删除最久未访问的缓存条目"""
        if not self.access_times:
            return
            
        oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[oldest_key]
        del self.access_times[oldest_key]
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_times.clear()


class FuzzyMatcher:
    """模糊匹配器，用于处理语音识别误差"""
    
    def __init__(self):
        # 常见的语音识别错误映射
        self.phonetic_mappings = {
            # 同音字映射
            "康回": "康惠",
            "康惠": "康回", 
            "天泉": "天全",
            "天全": "天泉",
            "罗辑": "逻辑",
            "逻辑": "罗辑",
            "洁将军": "杰将军",
            "杰将军": "洁将军",
            "唐闻": "汤文",
            "汤文": "唐闻",
            "战略": "战力",
            "战力": "战略",
            "总规划": "总规化",
            "总规化": "总规划",
            "研究院": "研究员",
            "研究员": "研究院",
            "院长": "员长",
            "员长": "院长",
        }
        
        # 实体别名映射
        self.entity_aliases = {
            "康回天泉": ["康惠天泉", "康回天全", "康惠天全"],
            "康惠天泉": ["康回天泉", "康回天全", "康惠天全"],
            "罗辑洁将军": ["逻辑杰将军", "罗辑杰将军", "逻辑洁将军"],
            "唐闻大叔": ["汤文大叔", "唐文大叔"],
            "技术源头": ["技术原头", "技术缘头"],
            "战略总规划师": ["战力总规划师", "战略总规化师"],
            "技术研究院": ["技术研究员", "技术研究所"],
        }
    
    def normalize_text(self, text: str) -> str:
        """标准化文本，处理常见的语音识别错误"""
        normalized = text
        
        # 应用同音字映射
        for wrong, correct in self.phonetic_mappings.items():
            normalized = normalized.replace(wrong, correct)
        
        return normalized
    
    def get_similar_queries(self, query: str) -> List[str]:
        """生成相似查询列表"""
        queries = [query]
        
        # 添加标准化后的查询
        normalized = self.normalize_text(query)
        if normalized != query:
            queries.append(normalized)
        
        # 添加实体别名查询
        for entity, aliases in self.entity_aliases.items():
            if entity in query:
                for alias in aliases:
                    variant = query.replace(entity, alias)
                    if variant not in queries:
                        queries.append(variant)
            
            # 反向匹配
            for alias in aliases:
                if alias in query:
                    variant = query.replace(alias, entity)
                    if variant not in queries:
                        queries.append(variant)
        
        return queries
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度"""
        # 标准化文本
        norm1 = self.normalize_text(text1.lower())
        norm2 = self.normalize_text(text2.lower())
        
        # 使用序列匹配器计算相似度
        return SequenceMatcher(None, norm1, norm2).ratio()


class MemoryProvider(MemoryProviderBase):
    """
    基于 Mem0 + Milvus 的记忆提供者
    
    特性：
    - 完全本地化，不依赖云服务
    - 使用 Mem0 的智能记忆管理
    - 使用 Milvus 的高性能向量存储
    - 兼容现有的 MemoryProviderBase 接口
    - 智能查询缓存和模糊匹配
    """
    
    def __init__(self, config, summary_memory=None):
        super().__init__(config)
        
        # 从配置中获取参数
        self.milvus_uri = config.get("milvus_uri", "http://8.149.245.150:19530")
        self.collection_name = config.get("collection_name", "xiaozhi_memories")
        self.embedding_model_dims = config.get("embedding_model_dims", 1536)
        self.milvus_token = config.get("milvus_token", None)
        # 修复：从管理后台传递的字段名，支持嵌套键名
        self.openai_api_key = config.get("openai_api_key", "") or config.get("memory.milvus_mem0.openai_api_key", "")
        
        # 新增：支持阿里云百炼API
        self.openai_api_base = config.get("openai_api_base", None) or config.get("api_base", None) or config.get("memory.milvus_mem0.openai_api_base", None)
        self.embedding_model = config.get("embedding_model", "") or config.get("memory.milvus_mem0.embedding_model", "text-embedding-v1")
        
        # 性能优化配置
        self.enable_cache = config.get("enable_query_cache", True)
        self.cache_size = config.get("cache_size", 100)
        self.cache_ttl = config.get("cache_ttl", 300)  # 5分钟
        self.enable_fuzzy_matching = config.get("enable_fuzzy_matching", True)
        self.similarity_threshold = config.get("similarity_threshold", 0.7)
        
        # 调试信息：打印配置内容
        # logger.info(f"[{TAG}] 配置调试信息:")
        # logger.info(f"[{TAG}] - config keys: {list(config.keys())}")
        # logger.info(f"[{TAG}] - api_key: {'***' if self.openai_api_key else 'EMPTY'}")
        # logger.info(f"[{TAG}] - openai_api_base: {self.openai_api_base}")
        # logger.info(f"[{TAG}] - milvus_uri: {self.milvus_uri}")
        # logger.info(f"[{TAG}] - collection_name: {self.collection_name}")
        # logger.info(f"[{TAG}] - embedding_model_dims: {self.embedding_model_dims}")
        # logger.info(f"[{TAG}] - enable_cache: {self.enable_cache}")
        # logger.info(f"[{TAG}] - enable_fuzzy_matching: {self.enable_fuzzy_matching}")
        
        # 检查API配置
        api_provider = "阿里云百炼" if self.openai_api_base else "OpenAI"
        
        if self.openai_api_key:
            # 如果使用阿里云百炼，跳过OpenAI密钥检查
            if not self.openai_api_base:
                model_key_msg = check_model_key("OpenAI", self.openai_api_key)
                if model_key_msg:
                    logger.error(f"[{TAG}] OpenAI API密钥检查失败: {model_key_msg}")
                    self.use_memory = False
                    return
            else:
                logger.info(f"[{TAG}] 使用阿里云百炼API: {self.openai_api_base}")
        
        # 验证必要配置
        self._validate_config()
        
        try:
            # 初始化 Mem0 + Milvus 集成
            self.integration = Mem0MilvusIntegration(
                milvus_uri=self.milvus_uri,
                collection_name=self.collection_name,
                embedding_model_dims=self.embedding_model_dims,
                milvus_token=self.milvus_token,
                openai_api_key=self.openai_api_key,
                openai_api_base=self.openai_api_base,
                embedding_model=self.embedding_model
            )
            
            # 初始化高级记忆管理器
            self.memory_manager = MemoryManager(self.integration)
            
            # 初始化性能优化组件
            self.query_cache = QueryCache(max_size=self.cache_size, ttl=self.cache_ttl) if self.enable_cache else None
            self.fuzzy_matcher = FuzzyMatcher() if self.enable_fuzzy_matching else None
            
            # 预加载用户记忆索引（异步）
            self.memory_index = {}
            self.last_index_update = 0
            self.index_update_interval = 60  # 60秒更新一次索引
            
            self.use_memory = True
            logger.info(f"[{TAG}] 成功初始化 Mem0+Milvus 记忆提供者")
            # logger.info(f"[{TAG}] API提供商: {api_provider}")
            # logger.info(f"[{TAG}] 嵌入模型: {self.embedding_model}")
            # logger.info(f"[{TAG}] Milvus URI: {self.milvus_uri}")
            # logger.info(f"[{TAG}] 集合名称: {self.collection_name}")
            # logger.info(f"[{TAG}] 性能优化: 缓存={self.enable_cache}, 模糊匹配={self.enable_fuzzy_matching}")
            
        except Exception as e:
            logger.error(f"[{TAG}] 初始化 Mem0+Milvus 记忆提供者失败: {str(e)}")
            logger.error(f"[{TAG}] 详细错误: {traceback.format_exc()}")
            self.use_memory = False
    
    async def save_memory(self, msgs):
        """
        保存记忆到 Mem0+Milvus
        
        Args:
            msgs: 消息列表，每个消息包含 role 和 content 属性
            
        Returns:
            保存结果或 None
        """
        logger.info(f"[{TAG}] 开始保存记忆，消息数量: {len(msgs) if msgs else 0}")
        
        if not self.use_memory:
            logger.info(f"[{TAG}] 记忆功能未启用，跳过保存")
            return None
            
        if len(msgs) < 2:
            logger.info(f"[{TAG}] 消息数量不足({len(msgs)})，跳过保存")
            return None
        
        try:
            logger.info(f"[{TAG}] 开始智能处理对话内容...")
            # 智能整理和总结对话内容
            processed_content = await self._process_conversation_for_memory(msgs)
            
            if not processed_content:
                logger.info(f"[{TAG}] 对话内容不适合保存为记忆，跳过")
                return None
            
            logger.info(f"[{TAG}] 处理后的内容长度: {len(processed_content)}")
            logger.info(f"[{TAG}] 开始保存到Milvus，用户ID: {self.role_id}")
            
            # 使用高级记忆管理器保存分类记忆
            result = self.memory_manager.add_categorized_memory(
                content=processed_content,
                user_id=self.role_id,
                category="conversation",
                importance=5  # 默认重要性
            )
            
            # 清空缓存，因为有新的记忆添加
            if self.query_cache:
                self.query_cache.clear()
                logger.debug(f"[{TAG}] 已清空查询缓存")
            
            logger.info(f"[{TAG}] 保存记忆成功，结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[{TAG}] 保存记忆失败: {str(e)}")
            logger.error(f"[{TAG}] 详细错误: {traceback.format_exc()}")
            return None
    
    async def query_memory(self, query: str) -> str:
        """
        查询相关记忆（优化版本）
        
        Args:
            query: 查询字符串
            
        Returns:
            格式化的记忆字符串
        """
        if not self.use_memory:
            return ""
        
        start_time = time.time()
        
        try:
            # 1. 检查缓存
            if self.query_cache:
                cached_result = self.query_cache.get(query, self.role_id)
                if cached_result is not None:
                    query_time = time.time() - start_time
                    logger.info(f"[{TAG}] 缓存命中，查询耗时: {query_time:.3f}s")
                    return cached_result
            
            # 2. 快速本地匹配（如果有预加载的索引）
            local_results = await self._quick_local_search(query)
            
            # 3. 生成查询变体（模糊匹配）
            query_variants = [query]
            if self.fuzzy_matcher:
                query_variants = self.fuzzy_matcher.get_similar_queries(query)
                logger.debug(f"[{TAG}] 生成查询变体: {query_variants}")
            
            # 4. 并行查询多个变体
            all_results = list(local_results)  # 包含本地快速匹配结果
            search_tasks = []
            
            # 限制向量搜索的查询数量以控制延迟
            max_vector_queries = 2 if local_results else 3
            
            for variant in query_variants[:max_vector_queries]:
                task = self._search_single_query(variant)
                search_tasks.append(task)
            
            # 等待所有查询完成
            if search_tasks:
                results_list = await asyncio.gather(*search_tasks, return_exceptions=True)
                
                for results in results_list:
                    if isinstance(results, list):
                        all_results.extend(results)
            
            # 5. 去重和排序
            unique_results = self._deduplicate_results(all_results)
            
            # 6. 格式化结果
            formatted_result = self._format_memory_results(unique_results)
            
            # 7. 缓存结果
            if self.query_cache and formatted_result:
                self.query_cache.set(query, self.role_id, formatted_result)
            
            query_time = time.time() - start_time
            logger.info(f"[{TAG}] 查询完成，找到 {len(unique_results)} 条记忆，耗时: {query_time:.3f}s")
            
            return formatted_result
            
        except Exception as e:
            logger.error(f"[{TAG}] 查询记忆失败: {str(e)}")
            logger.error(f"[{TAG}] 详细错误: {traceback.format_exc()}")
            return ""
    
    async def _quick_local_search(self, query: str) -> List[Dict[str, Any]]:
        """快速本地搜索，基于预加载的索引"""
        if not self.memory_index or not query:
            return []
        
        try:
            local_matches = []
            query_lower = query.lower()
            
            # 1. 关键词匹配
            query_keywords = self._extract_keywords(query)
            for keyword in query_keywords:
                if keyword in self.memory_index['keywords']:
                    local_matches.extend(self.memory_index['keywords'][keyword])
            
            # 2. 文本包含匹配
            for category_memories in self.memory_index['categories'].values():
                for memory in category_memories:
                    memory_text = memory.get("memory", "").lower()
                    if query_lower in memory_text or any(kw in memory_text for kw in query_keywords):
                        local_matches.append(memory)
            
            # 3. 模糊匹配
            if self.fuzzy_matcher:
                for category_memories in self.memory_index['categories'].values():
                    for memory in category_memories:
                        memory_text = memory.get("memory", "")
                        similarity = self.fuzzy_matcher.calculate_similarity(query, memory_text)
                        if similarity > self.similarity_threshold:
                            # 添加相似度分数
                            memory_copy = memory.copy()
                            memory_copy['local_similarity'] = similarity
                            local_matches.append(memory_copy)
            
            # 去重并按相似度排序
            unique_local = self._deduplicate_results(local_matches)
            
            logger.debug(f"[{TAG}] 本地快速匹配找到 {len(unique_local)} 条结果")
            return unique_local[:3]  # 最多返回3条本地匹配结果
            
        except Exception as e:
            logger.warning(f"[{TAG}] 本地快速搜索失败: {e}")
            return []
    
    async def _search_single_query(self, query: str) -> List[Dict[str, Any]]:
        """执行单个查询"""
        try:
            results = self.integration.search_memories(
                query=query,
                user_id=self.role_id,
                limit=5
            )
            return results if results else []
        except Exception as e:
            logger.warning(f"[{TAG}] 单个查询失败 '{query}': {e}")
            return []
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重查询结果"""
        seen_memories = set()
        unique_results = []
        
        for result in results:
            memory_text = result.get("memory", "")
            if memory_text and memory_text not in seen_memories:
                seen_memories.add(memory_text)
                unique_results.append(result)
        
        # 按相关性排序（如果有score字段）
        unique_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return unique_results[:5]  # 最多返回5条
    
    def _format_memory_results(self, results: List[Dict[str, Any]]) -> str:
        """格式化记忆结果"""
        if not results:
            return ""
        
        memories = []
        for entry in results:
            memory_text = entry.get("memory", "")
            metadata = entry.get("metadata", {})
            created_at = metadata.get("created_at", "")
            
            if memory_text:
                if created_at:
                    try:
                        # 格式化时间戳
                        formatted_time = created_at.split("T")[0] + " " + created_at.split("T")[1][:5]
                        memories.append(f"[{formatted_time}] {memory_text}")
                    except:
                        memories.append(f"- {memory_text}")
                else:
                    memories.append(f"- {memory_text}")
        
        return "\n".join(memories)
    
    def get_query_performance_stats(self) -> Dict[str, Any]:
        """获取查询性能统计"""
        stats = {
            "cache_enabled": self.enable_cache,
            "fuzzy_matching_enabled": self.enable_fuzzy_matching,
            "memory_index_loaded": bool(self.memory_index),
            "last_index_update": self.last_index_update
        }
        
        if self.query_cache:
            stats.update({
                "cache_size": len(self.query_cache.cache),
                "cache_max_size": self.query_cache.max_size,
                "cache_ttl": self.query_cache.ttl
            })
        if self.memory_index:
            stats.update({
                "indexed_memories": self.memory_index.get('total_count', 0),
                "categories_count": len(self.memory_index.get('categories', {})),
                "important_memories_count": len(self.memory_index.get('important_memories', [])),
                "keywords_count": len(self.memory_index.get('keywords', {}))
            })
        return stats

    async def _process_conversation_for_memory(self, msgs) -> str:
        """
        智能处理对话内容，提取有价值的记忆信息
        
        Args:
            msgs: 消息列表
            
        Returns:
            处理后的记忆内容，如果不适合保存则返回空字符串
        """
        # 过滤出有效的对话内容
        conversation_messages = []
        for message in msgs:
            if hasattr(message, 'role') and hasattr(message, 'content'):
                if message.role != "system":  # 跳过系统消息
                    conversation_messages.append(message)
        
        if len(conversation_messages) < 2:
            return ""
        
        # 检查对话是否包含有价值的信息
        if not self._is_conversation_worth_remembering(conversation_messages):
            return ""
        
        # 如果对话较短且简单，直接格式化保存
        if len(conversation_messages) <= 4:
            return self._format_simple_conversation(conversation_messages)
        
        # 对于较长的对话，进行智能总结
        return await self._summarize_conversation(conversation_messages)
    
    def _is_conversation_worth_remembering(self, msgs) -> bool:
        """
        判断对话是否值得记忆
        
        Args:
            msgs: 消息列表
            
        Returns:
            是否值得记忆
        """
        # 过滤掉不值得记忆的内容
        trivial_patterns = [
            r'^(你好|hi|hello|嗨)$',  # 简单问候
            r'^(再见|拜拜|bye)$',     # 简单告别
            r'^(谢谢|感谢)$',         # 简单感谢
            r'^(好的|ok|知道了)$',    # 简单确认
            r'^(播放|暂停|停止|音量|退出)',  # 设备控制指令
            r'^(今天天气|现在几点)',   # 简单查询
        ]
        
        user_messages = [msg.content.strip() for msg in msgs if msg.role == "user"]
        
        # 如果所有用户消息都是简单指令，则不值得记忆
        for user_msg in user_messages:
            is_trivial = any(re.match(pattern, user_msg, re.IGNORECASE) for pattern in trivial_patterns)
            if not is_trivial:
                return True  # 至少有一条非简单指令
        
        return False
    
    def _format_simple_conversation(self, msgs) -> str:
        """
        格式化简单对话
        
        Args:
            msgs: 消息列表
            
        Returns:
            格式化的对话字符串
        """
        formatted_messages = []
        
        for message in msgs:
            role_name = "用户" if message.role == "user" else "助手"
            formatted_messages.append(f"{role_name}: {message.content}")
        
        return "\n".join(formatted_messages)
    
    async def _summarize_conversation(self, msgs) -> str:
        """
        使用LLM对长对话进行智能总结
        
        Args:
            msgs: 消息列表
            
        Returns:
            总结后的内容
        """
        try:
            # 构建对话文本
            conversation_text = self._format_simple_conversation(msgs)
            
            # 总结提示词
            summary_prompt = """请对以下对话进行智能总结，提取出值得记忆的关键信息：

1. 用户的个人信息、偏好、需求
2. 重要的事件、决定或计划
3. 有意义的情感表达或观点
4. 需要后续跟进的事项

请忽略：
- 简单的问候和告别
- 设备控制指令
- 无关紧要的闲聊
- 重复的信息

总结要求：
- 保持客观和准确
- 突出重点信息
- 控制在200字以内
- 如果对话没有值得记忆的内容，请回复"无需记忆"

对话内容：
"""
            
            # 如果有可用的LLM，使用LLM进行总结
            if hasattr(self, 'llm') and self.llm is not None:
                try:
                    summary = self.llm.response_no_stream(
                        summary_prompt,
                        conversation_text,
                        max_tokens=300,
                        temperature=0.3
                    )
                    
                    if summary and "无需记忆" not in summary:
                        return summary.strip()
                    else:
                        return ""
                        
                except Exception as e:
                    logger.warning(f"[{TAG}] LLM总结失败，使用简单格式化: {e}")
                    return self._format_simple_conversation(msgs)
            else:
                # 如果没有LLM，使用简单格式化
                return self._format_simple_conversation(msgs)
                
        except Exception as e:
            logger.error(f"[{TAG}] 对话总结失败: {e}")
            return self._format_simple_conversation(msgs)
    
    def _format_messages_for_mem0(self, msgs) -> str:
        """
        将消息列表格式化为适合 Mem0 处理的字符串
        
        Args:
            msgs: 消息列表
            
        Returns:
            格式化的消息字符串
        """
        formatted_messages = []
        
        for message in msgs:
            if hasattr(message, 'role') and hasattr(message, 'content'):
                if message.role != "system":  # 跳过系统消息
                    role_name = "用户" if message.role == "user" else "助手"
                    formatted_messages.append(f"{role_name}: {message.content}")
        
        return "\n".join(formatted_messages)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        获取记忆统计信息
        
        Returns:
            统计信息字典
        """
        if not self.use_memory:
            return {"status": "disabled"}
        
        try:
            stats = self.integration.get_milvus_stats()
            
            # 获取用户的记忆数量
            all_memories = self.integration.get_all_memories(self.role_id)
            memory_count = len(all_memories.get('results', []))
            
            stats.update({
                "user_id": self.role_id,
                "memory_count": memory_count,
                "status": "active"
            })
            
            return stats
            
        except Exception as e:
            logger.error(f"[{TAG}] 获取记忆统计失败: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def reset_user_memories(self, role_id: str) -> bool:
        """
        重置用户记忆
        
        Args:
            role_id: 用户角色ID
            
        Returns:
            bool: 重置是否成功
        """
        try:
            # 使用Mem0的delete方法删除用户的所有记忆
            self.mem0_integration.mem0.delete_all(user_id=role_id)
            logger.info(f"[{TAG}] 用户 {role_id} 的记忆已重置")
            return True
        except Exception as e:
            logger.error(f"[{TAG}] 重置用户 {role_id} 记忆失败: {e}")
            return False
    
    def _validate_config(self) -> None:
        """验证配置参数的完整性"""
        required_configs = {
            'milvus_uri': self.milvus_uri,
            'collection_name': self.collection_name,
            'embedding_model_dims': self.embedding_model_dims,
            'openai_api_key': self.openai_api_key
        }
        
        missing_configs = [key for key, value in required_configs.items() if not value]
        
        if missing_configs:
            raise ValueError(f"缺少必要配置: {', '.join(missing_configs)}")
        
        # 验证维度是否为正整数
        if not isinstance(self.embedding_model_dims, int) or self.embedding_model_dims <= 0:
            raise ValueError(f"embedding_model_dims必须是正整数，当前值: {self.embedding_model_dims}")
        
        logger.info(f"[{TAG}] 配置验证通过")