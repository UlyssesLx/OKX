"""
Twitter搜索模块 - Python版本
使用Twitter API v2搜索用户推文，获取市场情绪
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
import json
import os
from dataclasses import dataclass
from app.core.config import settings


@dataclass
class TwitterUser:
    """Twitter用户信息"""
    id: str
    username: str
    name: str
    description: str
    followers_count: int
    following_count: int
    tweet_count: int
    created_at: str


@dataclass
class TwitterTweet:
    """Twitter推文"""
    id: str
    text: str
    created_at: str
    like_count: int
    retweet_count: int
    reply_count: int
    quote_count: int


@dataclass
class TwitterSentiment:
    """Twitter情绪分析结果"""
    user: TwitterUser
    tweets: List[TwitterTweet]
    sentiment_score: int
    bullish_count: int
    bearish_count: int
    timestamp: int


class TwitterMonitor:
    """Twitter监控器"""
    
    def __init__(self, cache_dir: str = "./data"):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "twitter_cache.json")
        os.makedirs(cache_dir, exist_ok=True)
        
        # Twitter API凭证
        self.consumer_key = getattr(settings, 'TWITTER_CONSUMER_KEY', '')
        self.consumer_secret = getattr(settings, 'TWITTER_CONSUMER_SECRET', '')
        self.access_token = getattr(settings, 'TWITTER_ACCESS_TOKEN', '')
        self.access_token_secret = getattr(settings, 'TWITTER_ACCESS_TOKEN_SECRET', '')
        
        self.bearer_token = None
        self.token_expiry = None
        
        self.cache = {}
        self.CACHE_DURATION = 5 * 60 * 1000  # 5分钟
        
        self._load_cache()
    
    def _load_cache(self):
        """加载缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception as e:
                logger.warning(f"加载Twitter缓存失败: {e}")
    
    def _save_cache(self):
        """保存缓存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存Twitter缓存失败: {e}")
    
    async def _get_bearer_token(self) -> Optional[str]:
        """获取Bearer Token"""
        # 检查token是否仍然有效
        if self.bearer_token and self.token_expiry:
            if datetime.now().timestamp() * 1000 < self.token_expiry:
                return self.bearer_token
        
        if not self.consumer_key or not self.consumer_secret:
            logger.warning("Twitter API凭证未配置")
            return None
        
        try:
            import base64
            credentials = base64.b64encode(
                f"{self.consumer_key}:{self.consumer_secret}".encode()
            ).decode()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.twitter.com/oauth2/token',
                    headers={
                        'Authorization': f'Basic {credentials}',
                        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
                    },
                    data='grant_type=client_credentials'
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"获取Twitter Token失败: {error_text}")
                        return None
                    
                    data = await response.json()
                    self.bearer_token = data.get('access_token')
                    # Token有效期2小时
                    self.token_expiry = int((datetime.now() + timedelta(hours=2)).timestamp() * 1000)
                    
                    return self.bearer_token
        
        except Exception as e:
            logger.error(f"获取Twitter Token异常: {e}")
            return None
    
    async def _search_user(self, username: str, bearer_token: str) -> Optional[TwitterUser]:
        """搜索用户"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'https://api.twitter.com/2/users/by/username/{username}',
                    params={
                        'user.fields': 'description,public_metrics,created_at'
                    },
                    headers={
                        'Authorization': f'Bearer {bearer_token}'
                    }
                ) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    
                    if 'data' not in data:
                        return None
                    
                    user_data = data['data']
                    metrics = user_data.get('public_metrics', {})
                    
                    return TwitterUser(
                        id=user_data['id'],
                        username=user_data['username'],
                        name=user_data['name'],
                        description=user_data.get('description', ''),
                        followers_count=metrics.get('followers_count', 0),
                        following_count=metrics.get('following_count', 0),
                        tweet_count=metrics.get('tweet_count', 0),
                        created_at=user_data.get('created_at', '')
                    )
        
        except Exception as e:
            logger.error(f"搜索Twitter用户失败: {e}")
            return None
    
    async def _get_user_tweets(self, user_id: str, bearer_token: str, max_results: int = 10) -> List[TwitterTweet]:
        """获取用户推文"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'https://api.twitter.com/2/users/{user_id}/tweets',
                    params={
                        'max_results': max_results,
                        'tweet.fields': 'created_at,public_metrics'
                    },
                    headers={
                        'Authorization': f'Bearer {bearer_token}'
                    }
                ) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    
                    if 'data' not in data:
                        return []
                    
                    tweets = []
                    for tweet_data in data['data']:
                        metrics = tweet_data.get('public_metrics', {})
                        tweets.append(TwitterTweet(
                            id=tweet_data['id'],
                            text=tweet_data['text'],
                            created_at=tweet_data.get('created_at', ''),
                            like_count=metrics.get('like_count', 0),
                            retweet_count=metrics.get('retweet_count', 0),
                            reply_count=metrics.get('reply_count', 0),
                            quote_count=metrics.get('quote_count', 0)
                        ))
                    
                    return tweets
        
        except Exception as e:
            logger.error(f"获取用户推文失败: {e}")
            return []
    
    def _analyze_sentiment(self, text: str) -> int:
        """分析推文情绪"""
        text_lower = text.lower()
        
        positive_keywords = [
            'bullish', 'buy', 'long', 'pump', 'moon', 'rally', 'surge',
            'up', 'high', 'good', 'great', 'excellent', 'profit', 'gain',
            '看涨', '买入', '上涨', '好', '盈利'
        ]
        
        negative_keywords = [
            'bearish', 'sell', 'short', 'dump', 'crash', 'plunge', 'fall',
            'down', 'low', 'bad', 'terrible', 'loss', 'risk', 'danger',
            '看跌', '卖出', '下跌', '坏', '亏损', '风险'
        ]
        
        positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in text_lower)
        
        # 计算情绪分数 (1-10)
        score = 5
        if positive_count > negative_count:
            score = min(10, 5 + (positive_count - negative_count))
        elif negative_count > positive_count:
            score = max(1, 5 - (negative_count - positive_count))
        
        return score
    
    async def get_user_sentiment(self, username: str) -> Optional[TwitterSentiment]:
        """获取用户情绪分析"""
        # 检查缓存
        cache_key = f"user_{username}"
        if cache_key in self.cache:
            cache_data = self.cache[cache_key]
            if (datetime.now().timestamp() * 1000 - cache_data['timestamp']) < self.CACHE_DURATION:
                logger.debug(f"使用缓存的Twitter用户数据: {username}")
                return TwitterSentiment(**cache_data['data'])
        
        bearer_token = await self._get_bearer_token()
        if not bearer_token:
            return None
        
        user = await self._search_user(username, bearer_token)
        if not user:
            return None
        
        tweets = await self._get_user_tweets(user.id, bearer_token)
        
        # 分析推文情绪
        bullish_count = 0
        bearish_count = 0
        total_score = 0
        
        for tweet in tweets:
            score = self._analyze_sentiment(tweet.text)
            total_score += score
            if score >= 6:
                bullish_count += 1
            elif score <= 4:
                bearish_count += 1
        
        avg_score = round(total_score / len(tweets)) if tweets else 5
        
        result = TwitterSentiment(
            user=user,
            tweets=tweets,
            sentiment_score=avg_score,
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            timestamp=int(datetime.now().timestamp() * 1000)
        )
        
        # 更新缓存
        self.cache[cache_key] = {
            'data': {
                'user': result.user.__dict__,
                'tweets': [t.__dict__ for t in result.tweets],
                'sentiment_score': result.sentiment_score,
                'bullish_count': result.bullish_count,
                'bearish_count': result.bearish_count,
                'timestamp': result.timestamp
            },
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        self._save_cache()
        
        return result
    
    async def search_coin_mentions(self, coin: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """搜索币种相关推文（需要Twitter API Premium）"""
        # 基础API不支持搜索，需要Premium API
        # 这里提供接口定义，实际使用需要升级API
        logger.warning("Twitter搜索功能需要Premium API，当前仅支持用户推文分析")
        return []


# 全局单例
twitter_monitor = TwitterMonitor()
