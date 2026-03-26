"""
Sub-Agent服务客户端
通过HTTP API访问Sub-Agent服务
"""
import aiohttp
from typing import Optional, Dict, List, Any
from datetime import datetime
from loguru import logger


class SubAgentClient:
    """Sub-Agent服务客户端"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 3456,
        timeout: int = 3,
        max_failures: int = 5
    ):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self.max_failures = max_failures
        self.failure_count = 0
        self.service_disabled = False
        self.restart_attempted = False
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """发送HTTP请求"""
        if self.service_disabled:
            logger.debug("Sub-Agent服务已禁用，跳过请求")
            return None
        
        try:
            url = f"{self.base_url}{endpoint}"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.failure_count = 0  # 重置失败计数
                        self.restart_attempted = False
                        return data
                    elif response.status == 404:
                        logger.debug(f"Sub-Agent服务返回404: {endpoint}")
                        return None
                    else:
                        raise Exception(f"HTTP {response.status}")
        except asyncio.TimeoutError:
            logger.warning(f"Sub-Agent服务请求超时: {endpoint}")
            return None
        except aiohttp.ClientError as e:
            logger.warning(f"Sub-Agent服务连接失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Sub-Agent服务请求错误: {str(e)}")
            return None
    
    def handle_failure(self):
        """处理失败情况"""
        self.failure_count += 1
        if self.failure_count >= self.max_failures:
            self.service_disabled = True
            logger.warning(f"🚫 Sub-Agent服务连续{self.max_failures}次失败，已禁用")
    
    async def health_check(self) -> bool:
        """检查服务是否可用"""
        try:
            result = await self._make_request("/health")
            return result is not None and result.get("status") == "ok"
        except Exception:
            return False
    
    async def get_rss_sentiment(self, coin: str) -> Optional[Dict]:
        """获取RSS新闻情绪"""
        result = await self._make_request("/rss", params={"coin": coin})
        if result is None:
            self.handle_failure()
        return result.get("sentiment") if result else None
    
    async def get_market_news_count(self) -> Optional[int]:
        """获取市场新闻数量"""
        result = await self._make_request("/rss")
        if result is None:
            self.handle_failure()
        return result.get("newsCount") if result else None
    
    async def get_twitter_sentiment(self, username: str) -> Optional[Dict]:
        """获取Twitter情绪"""
        result = await self._make_request("/twitter", params={"username": username})
        if result is None:
            self.handle_failure()
        return result.get("sentiment") if result else None
    
    async def get_lunarcrush_sentiment(self, coin: str) -> Optional[Dict]:
        """获取LunarCrush情绪"""
        result = await self._make_request("/lunarcrush", params={"coin": coin})
        if result is None:
            self.handle_failure()
        return result.get("sentiment") if result else None
    
    async def get_combined_sentiment(self, coin: str) -> Optional[Dict]:
        """获取综合情绪数据"""
        result = await self._make_request("/sentiment", params={"coin": coin})
        if result is None:
            self.handle_failure()
            return None
        return {
            "rss": result.get("rss"),
            "twitter": result.get("twitter"),
            "lunarcrush": result.get("lunarcrush"),
            "combined": result.get("combined")
        }
    
    async def get_batch_sentiment(self, coins: List[str]) -> Optional[Dict[str, Any]]:
        """批量查询情绪数据"""
        coins_str = ",".join(coins)
        result = await self._make_request("/sentiment/batch", params={"coins": coins_str})
        if result is None:
            self.handle_failure()
        return result.get("coins") if result else None
    
    async def get_market_sentiment(self) -> Optional[Dict]:
        """获取整体市场情绪"""
        result = await self._make_request("/market-sentiment")
        if result is None:
            self.handle_failure()
        return result.get("sentiment") if result else None
    
    async def get_sources_status(self) -> Optional[Dict[str, Any]]:
        """获取数据源状态"""
        result = await self._make_request("/sources/status")
        if result is None:
            self.handle_failure()
        return result.get("sources") if result else None
    
    def reset_restart_flag(self):
        """重置重启标志"""
        self.restart_attempted = False
    
    def is_enabled(self) -> bool:
        """检查服务是否启用"""
        return not self.service_disabled
    
    def disable(self):
        """禁用服务"""
        self.service_disabled = True
        logger.info("Sub-Agent服务已手动禁用")
    
    def enable(self):
        """启用服务"""
        self.service_disabled = False
        self.failure_count = 0
        self.restart_attempted = False
        logger.info("Sub-Agent服务已启用")


# 创建全局客户端实例
sub_agent_client = SubAgentClient()
