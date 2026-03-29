"""
LunarCrush社交媒体情绪监控模块 - Python版本
整合LunarCrush API获取社交情绪、Galaxy Score等数据
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
import json
import os
from dataclasses import dataclass
from app.core.config import settings


@dataclass
class LunarCrushSentiment:
    """LunarCrush情绪数据"""
    coin: str
    score: float  # 1-5分
    bullish_percent: float  # 看涨比例
    bearish_percent: float  # 看跌比例
    social_volume: int  # 社交量
    social_score: float  # 社交得分
    galaxy_score: float  # 综合得分
    price: float
    percent_change_24h: float
    trend_score: int  # 转换后的趋势评分 1-10
    timestamp: int


class LunarCrushMonitor:
    """LunarCrush监控器"""
    
    def __init__(self, cache_dir: str = "./data"):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "lunarcrush_cache.json")
        os.makedirs(cache_dir, exist_ok=True)
        
        # LunarCrush 配置
        self.enabled = getattr(settings, 'ENABLE_LUNARCRUSH_MONITOR', False)
        self.api_key = getattr(settings, 'LUNARCRUSH_API_KEY', '')
        self.base_url = 'https://api.lunarcrush.com/v2'
        
        self.cache = {}
        self.CACHE_DURATION = 5 * 60 * 1000  # 5分钟
        
        self._load_cache()
        
        if self.enabled and self.api_key:
            logger.info("✅ LunarCrush 社交情绪监控已启用")
        elif self.enabled and not self.api_key:
            logger.warning("⚠️ LunarCrush 已启用但未配置 API Key")
        else:
            logger.info("ℹ️ LunarCrush 社交情绪监控未启用")
    
    def _load_cache(self):
        """加载缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception as e:
                logger.warning(f"加载LunarCrush缓存失败: {e}")
    
    def _save_cache(self):
        """保存缓存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存LunarCrush缓存失败: {e}")
    
    def _convert_to_trend_score(self, sentiment: Dict[str, Any]) -> int:
        """将LunarCrush情绪转换为趋势评分（1-10分）"""
        score = 5  # 基础分
        
        # 情绪分数 (1-5分) 映射到 (1-10分)
        if sentiment.get('score', 0) > 0:
            score = sentiment['score'] * 2
        
        # 看涨/看跌比例调整
        bullish = sentiment.get('bullish_percent', 0)
        bearish = sentiment.get('bearish_percent', 0)
        if bullish > bearish * 1.5:
            score += 1
        elif bearish > bullish * 1.5:
            score -= 1
        
        # 社交量调整（高社交量增加信心）
        social_volume = sentiment.get('social_volume', 0)
        if social_volume > 1000:
            score += 0.5
        
        # Galaxy Score调整
        galaxy_score = sentiment.get('galaxy_score', 0)
        if galaxy_score > 80:
            score += 1
        elif galaxy_score < 40:
            score -= 1
        
        return max(1, min(10, int(round(score))))
    
    async def get_social_sentiment(self, coin: str) -> Optional[LunarCrushSentiment]:
        """获取币种社交媒体情绪"""
        # 检查是否启用
        if not self.enabled:
            logger.debug(f"LunarCrush 监控未启用，跳过 {coin}")
            return None
        
        # 检查缓存
        if coin in self.cache:
            cache_data = self.cache[coin]
            if (datetime.now().timestamp() * 1000 - cache_data['timestamp']) < self.CACHE_DURATION:
                logger.debug(f"{coin} 使用缓存的LunarCrush数据")
                return LunarCrushSentiment(**cache_data['data'])
        
        if not self.api_key:
            logger.warning("LunarCrush API凭证未配置")
            return None
        
        try:
            params = {
                'data': 'assets',
                'key': self.api_key,
                'symbol': coin
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"LunarCrush API请求失败: {error_text}")
                        return None
                    
                    data = await response.json()
                    
                    if not data.get('data') or len(data['data']) == 0:
                        logger.debug(f"{coin} 无LunarCrush数据")
                        return None
                    
                    asset = data['data'][0]
                    
                    # 提取关键指标
                    sentiment = {
                        'score': asset.get('average_sentiment', 0),
                        'bullish_percent': asset.get('bullish_sentiment', 0),
                        'bearish_percent': asset.get('bearish_sentiment', 0),
                        'social_volume': asset.get('social_volume', 0),
                        'social_score': asset.get('social_score', 0),
                        'galaxy_score': asset.get('galaxy_score', 0),
                        'price': asset.get('price', 0),
                        'percent_change_24h': asset.get('percent_change_24h', 0)
                    }
                    
                    # 转换趋势评分
                    trend_score = self._convert_to_trend_score(sentiment)
                    
                    result = LunarCrushSentiment(
                        coin=coin,
                        score=sentiment['score'],
                        bullish_percent=sentiment['bullish_percent'],
                        bearish_percent=sentiment['bearish_percent'],
                        social_volume=sentiment['social_volume'],
                        social_score=sentiment['social_score'],
                        galaxy_score=sentiment['galaxy_score'],
                        price=sentiment['price'],
                        percent_change_24h=sentiment['percent_change_24h'],
                        trend_score=trend_score,
                        timestamp=int(datetime.now().timestamp() * 1000)
                    )
                    
                    # 更新缓存
                    self.cache[coin] = {
                        'data': result.__dict__,
                        'timestamp': int(datetime.now().timestamp() * 1000)
                    }
                    self._save_cache()
                    
                    return result
        
        except asyncio.TimeoutError:
            logger.error(f"获取{coin} LunarCrush数据超时")
            return None
        except Exception as e:
            logger.error(f"获取{coin}社交媒体情绪失败: {e}")
            return None
    
    async def get_batch_sentiment(self, coins: List[str]) -> Dict[str, LunarCrushSentiment]:
        """批量获取多个币种的情绪"""
        if not self.api_key:
            logger.warning("LunarCrush API凭证未配置")
            return {}
        
        try:
            symbols = ','.join(coins)
            params = {
                'data': 'assets',
                'key': self.api_key,
                'symbol': symbols
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status != 200:
                        logger.error(f"LunarCrush批量请求失败")
                        return {}
                    
                    data = await response.json()
                    
                    results = {}
                    if data.get('data'):
                        for asset in data['data']:
                            coin = asset.get('symbol', '')
                            if not coin:
                                continue
                            
                            sentiment = {
                                'score': asset.get('average_sentiment', 0),
                                'bullish_percent': asset.get('bullish_sentiment', 0),
                                'bearish_percent': asset.get('bearish_sentiment', 0),
                                'social_volume': asset.get('social_volume', 0),
                                'social_score': asset.get('social_score', 0),
                                'galaxy_score': asset.get('galaxy_score', 0),
                                'price': asset.get('price', 0),
                                'percent_change_24h': asset.get('percent_change_24h', 0)
                            }
                            
                            trend_score = self._convert_to_trend_score(sentiment)
                            
                            result = LunarCrushSentiment(
                                coin=coin,
                                score=sentiment['score'],
                                bullish_percent=sentiment['bullish_percent'],
                                bearish_percent=sentiment['bearish_percent'],
                                social_volume=sentiment['social_volume'],
                                social_score=sentiment['social_score'],
                                galaxy_score=sentiment['galaxy_score'],
                                price=sentiment['price'],
                                percent_change_24h=sentiment['percent_change_24h'],
                                trend_score=trend_score,
                                timestamp=int(datetime.now().timestamp() * 1000)
                            )
                            
                            results[coin] = result
                            
                            # 更新缓存
                            self.cache[coin] = {
                                'data': result.__dict__,
                                'timestamp': int(datetime.now().timestamp() * 1000)
                            }
                    
                    self._save_cache()
                    return results
        
        except Exception as e:
            logger.error(f"批量获取LunarCrush数据失败: {e}")
            return {}


# 全局单例
lunarcrush_monitor = LunarCrushMonitor()
