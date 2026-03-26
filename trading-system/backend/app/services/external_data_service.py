"""
统一外部数据服务
整合RSS、Twitter、LunarCrush等外部数据源，提供统一的API接口
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
import asyncio
from dataclasses import dataclass

from .external_data_sources import (
    RSSMonitor, rss_monitor,
    TwitterMonitor, twitter_monitor,
    LunarCrushMonitor, lunarcrush_monitor
)


@dataclass
class CoinSentimentReport:
    """币种综合情绪报告"""
    coin: str
    rss_sentiment: Optional[Dict[str, Any]] = None
    twitter_sentiment: Optional[Dict[str, Any]] = None
    lunarcrush_sentiment: Optional[Dict[str, Any]] = None
    overall_score: int = 5
    timestamp: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'coin': self.coin,
            'rss_sentiment': self.rss_sentiment,
            'twitter_sentiment': self.twitter_sentiment,
            'lunarcrush_sentiment': self.lunarcrush_sentiment,
            'overall_score': self.overall_score,
            'timestamp': self.timestamp
        }


class ExternalDataService:
    """外部数据服务管理器"""
    
    def __init__(self):
        self.rss_monitor = rss_monitor
        self.twitter_monitor = twitter_monitor
        self.lunarcrush_monitor = lunarcrush_monitor
    
    async def get_coin_sentiment(self, coin: str, username: Optional[str] = None) -> CoinSentimentReport:
        """
        获取币种综合情绪报告
        
        Args:
            coin: 币种符号（如BTC、ETH）
            username: Twitter用户名（可选）
        
        Returns:
            CoinSentimentReport: 综合情绪报告
        """
        logger.info(f"获取 {coin} 外部数据...")
        
        # 并行获取多个数据源
        tasks = []
        
        # RSS新闻情绪
        tasks.append(self._get_rss_sentiment(coin))
        
        # Twitter情绪（如果提供了用户名）
        if username:
            tasks.append(self._get_twitter_sentiment(username))
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0)))
        
        # LunarCrush社交媒体情绪
        tasks.append(self._get_lunarcrush_sentiment(coin))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        rss_sentiment = results[0] if not isinstance(results[0], Exception) else None
        twitter_sentiment = results[1] if not isinstance(results[1], Exception) and username else None
        lunarcrush_sentiment = results[2] if not isinstance(results[2], Exception) else None
        
        # 计算综合评分
        overall_score = self._calculate_overall_score(
            rss_sentiment, twitter_sentiment, lunarcrush_sentiment
        )
        
        report = CoinSentimentReport(
            coin=coin,
            rss_sentiment=rss_sentiment,
            twitter_sentiment=twitter_sentiment,
            lunarcrush_sentiment=lunarcrush_sentiment,
            overall_score=overall_score,
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        
        logger.info(f"{coin} 综合情绪评分: {overall_score}/10")
        
        return report
    
    async def _get_rss_sentiment(self, coin: str) -> Optional[Dict[str, Any]]:
        """获取RSS新闻情绪"""
        try:
            sentiment = await self.rss_monitor.get_coin_news_sentiment(coin)
            if sentiment:
                return {
                    'score': sentiment.score,
                    'news_count': sentiment.news_count,
                    'bullish_count': sentiment.bullish_count,
                    'bearish_count': sentiment.bearish_count,
                    'recent_news': sentiment.recent_news
                }
        except Exception as e:
            logger.error(f"获取{coin} RSS情绪失败: {e}")
        return None
    
    async def _get_twitter_sentiment(self, username: str) -> Optional[Dict[str, Any]]:
        """获取Twitter情绪"""
        try:
            sentiment = await self.twitter_monitor.get_user_sentiment(username)
            if sentiment:
                return {
                    'username': sentiment.user.username,
                    'sentiment_score': sentiment.sentiment_score,
                    'bullish_count': sentiment.bullish_count,
                    'bearish_count': sentiment.bearish_count,
                    'tweet_count': len(sentiment.tweets),
                    'followers_count': sentiment.user.followers_count
                }
        except Exception as e:
            logger.error(f"获取Twitter情绪失败: {e}")
        return None
    
    async def _get_lunarcrush_sentiment(self, coin: str) -> Optional[Dict[str, Any]]:
        """获取LunarCrush情绪"""
        try:
            sentiment = await self.lunarcrush_monitor.get_social_sentiment(coin)
            if sentiment:
                return {
                    'score': sentiment.score,
                    'trend_score': sentiment.trend_score,
                    'bullish_percent': sentiment.bullish_percent,
                    'bearish_percent': sentiment.bearish_percent,
                    'social_volume': sentiment.social_volume,
                    'social_score': sentiment.social_score,
                    'galaxy_score': sentiment.galaxy_score
                }
        except Exception as e:
            logger.error(f"获取{coin} LunarCrush情绪失败: {e}")
        return None
    
    def _calculate_overall_score(
        self,
        rss_sentiment: Optional[Dict[str, Any]],
        twitter_sentiment: Optional[Dict[str, Any]],
        lunarcrush_sentiment: Optional[Dict[str, Any]]
    ) -> int:
        """
        计算综合评分
        
        权重分配：
        - RSS新闻: 40%
        - Twitter: 20% (如果有)
        - LunarCrush: 40%
        """
        scores = []
        weights = []
        
        # RSS新闻情绪
        if rss_sentiment and rss_sentiment.get('score'):
            scores.append(rss_sentiment['score'])
            weights.append(0.4)
        
        # Twitter情绪
        if twitter_sentiment and twitter_sentiment.get('sentiment_score'):
            scores.append(twitter_sentiment['sentiment_score'])
            weights.append(0.2)
        
        # LunarCrush情绪
        if lunarcrush_sentiment and lunarcrush_sentiment.get('trend_score'):
            scores.append(lunarcrush_sentiment['trend_score'])
            weights.append(0.4)
        
        if not scores:
            return 5  # 无数据时返回中性
        
        # 计算加权平均
        total_weight = sum(weights)
        weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
        overall_score = round(weighted_sum / total_weight)
        
        # 限制范围 1-10
        return max(1, min(10, overall_score))
    
    async def get_overall_market_sentiment(self) -> Dict[str, Any]:
        """获取整体市场情绪"""
        try:
            rss_sentiment = await self.rss_monitor.get_overall_market_sentiment()
            
            logger.info(f"整体市场情绪: {rss_sentiment.get('score', 5)}/10")
            
            return {
                'score': rss_sentiment.get('score', 5),
                'news_count': rss_sentiment.get('news_count', 0),
                'bullish_count': rss_sentiment.get('bullish_count', 0),
                'bearish_count': rss_sentiment.get('bearish_count', 0),
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
        except Exception as e:
            logger.error(f"获取整体市场情绪失败: {e}")
            return {
                'score': 5,
                'news_count': 0,
                'bullish_count': 0,
                'bearish_count': 0,
                'timestamp': int(datetime.now().timestamp() * 1000)
            }
    
    async def get_latest_news(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取最新新闻"""
        try:
            news = await self.rss_monitor.get_all_news()
            return news[:limit]
        except Exception as e:
            logger.error(f"获取最新新闻失败: {e}")
            return []
    
    async def batch_get_sentiment(
        self,
        coins: List[str],
        usernames: Optional[Dict[str, str]] = None
    ) -> Dict[str, CoinSentimentReport]:
        """
        批量获取多个币种的情绪报告
        
        Args:
            coins: 币种列表
            usernames: 币种到Twitter用户名的映射（可选）
        
        Returns:
            Dict[str, CoinSentimentReport]: 币种到情绪报告的映射
        """
        if usernames is None:
            usernames = {}
        
        # 批量获取LunarCrush数据
        lunarcrush_data = await self.lunarcrush_monitor.get_batch_sentiment(coins)
        
        # 逐个获取其他数据源
        reports = {}
        for coin in coins:
            username = usernames.get(coin)
            report = await self.get_coin_sentiment(coin, username)
            reports[coin] = report
        
        return reports


# 全局单例
external_data_service = ExternalDataService()
