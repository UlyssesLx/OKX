"""
RSS新闻监控模块 - Python版本
监控加密货币新闻，提取情绪信号
"""
import asyncio
import aiohttp
import feedparser
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
import json
import os
from dataclasses import dataclass, asdict


# RSS源配置
RSS_SOURCES = [
    {
        'name': 'CoinDesk',
        'url': 'https://feeds.feedburner.com/CoinDesk',
        'priority': 1
    },
    {
        'name': 'Cointelegraph',
        'url': 'https://cointelegraph.com/rss',
        'priority': 1
    },
    {
        'name': 'Decrypt',
        'url': 'https://decrypt.co/feed',
        'priority': 2
    }
]


# 关键词库
KEYWORDS = {
    'positive': [
        'bullish', 'surge', 'rally', 'breakout', 'moon', 'ath', 'all-time high',
        'adoption', 'partnership', 'listing', 'institutional', 'etf', 'approve',
        'upgrade', 'mainnet', 'launch', 'growth', 'profit', 'gain', 'pump',
        '突破', '上涨', '利好', '合作', '采用', '升级', '启动', '盈利'
    ],
    'negative': [
        'bearish', 'crash', 'dump', 'plunge', 'drop', 'fall', 'decline',
        'hack', 'exploit', 'scam', 'fraud', 'ban', 'regulation', 'sec',
        'lawsuit', 'investigation', 'delist', 'suspend', 'risk', 'warning',
        '下跌', '暴跌', '黑客', '诈骗', '禁止', '监管', '诉讼', '风险', '警告'
    ],
    'coins': {
        'BTC': ['bitcoin', 'btc', '比特币'],
        'ETH': ['ethereum', 'eth', 'ether', '以太坊'],
        'XRP': ['ripple', 'xrp', '瑞波'],
        'SOL': ['solana', 'sol'],
        'ADA': ['cardano', 'ada'],
        'DOT': ['polkadot', 'dot'],
        'DOGE': ['dogecoin', 'doge'],
        'AVAX': ['avalanche', 'avax'],
        'LINK': ['chainlink', 'link'],
        'MATIC': ['polygon', 'matic'],
        'LTC': ['litecoin', 'ltc'],
        'BCH': ['bitcoin cash', 'bch'],
        'XLM': ['stellar', 'xlm'],
        'TRX': ['tron', 'trx', '波场'],
        'FIL': ['filecoin', 'fil'],
        'ETC': ['ethereum classic', 'etc'],
        'XMR': ['monero', 'xmr'],
        'ALGO': ['algorand', 'algo'],
        'VET': ['vechain', 'vet'],
        'ICP': ['internet computer', 'icp'],
        'NEAR': ['near protocol', 'near'],
        'ATOM': ['cosmos', 'atom'],
        'APT': ['aptos', 'apt'],
        'OP': ['optimism', 'op'],
        'ARB': ['arbitrum', 'arb'],
        'SUI': ['sui'],
        'SEI': ['sei'],
        'TON': ['toncoin', 'ton'],
        'BNB': ['binance coin', 'bnb', 'binance']
    }
}


@dataclass
class NewsItem:
    """新闻条目"""
    title: str
    description: str
    link: str
    pub_date: str
    timestamp: int
    source: str
    sentiment_score: int
    positive_count: int
    negative_count: int
    mentioned_coins: List[str]
    is_bullish: bool
    is_bearish: bool


@dataclass
class CoinNewsSentiment:
    """币种新闻情绪"""
    score: int
    news_count: int
    bullish_count: int
    bearish_count: int
    recent_news: List[Dict[str, Any]]
    timestamp: int


class RSSMonitor:
    """RSS新闻监控器"""
    
    def __init__(self, cache_dir: str = "./data"):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "rss_cache.json")
        os.makedirs(cache_dir, exist_ok=True)
        
        self.news_cache = {
            'items': [],
            'timestamp': 0
        }
        self.CACHE_DURATION = 15 * 60 * 1000  # 15分钟
        
        self._load_cache()
    
    def _load_cache(self):
        """加载缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.news_cache = json.load(f)
            except Exception as e:
                logger.warning(f"加载RSS缓存失败: {e}")
    
    def _save_cache(self):
        """保存缓存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.news_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存RSS缓存失败: {e}")
    
    def _analyze_sentiment(self, title: str, description: str) -> Dict[str, Any]:
        """分析新闻情绪"""
        text = (title + ' ' + description).lower()
        
        positive_count = 0
        negative_count = 0
        
        for word in KEYWORDS['positive']:
            if word.lower() in text:
                positive_count += 1
        
        for word in KEYWORDS['negative']:
            if word.lower() in text:
                negative_count += 1
        
        # 检测提到的币种
        mentioned_coins = []
        for coin, aliases in KEYWORDS['coins'].items():
            for alias in aliases:
                if alias.lower() in text:
                    mentioned_coins.append(coin)
                    break
        
        # 计算情绪得分
        score = 5  # 中性
        if positive_count > negative_count:
            score = min(10, 5 + (positive_count - negative_count) * 2)
        elif negative_count > positive_count:
            score = max(1, 5 - (negative_count - positive_count) * 2)
        
        return {
            'score': score,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'mentioned_coins': list(set(mentioned_coins)),
            'is_bullish': positive_count > negative_count,
            'is_bearish': negative_count > positive_count
        }
    
    async def _fetch_rss_feed(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """获取RSS源"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    source['url'],
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={
                        'User-Agent': 'Mozilla/5.0 (TradingBot/1.0)',
                        'Accept': 'application/rss+xml, application/xml, text/xml'
                    }
                ) as response:
                    if response.status != 200:
                        logger.warning(f"{source['name']} HTTP {response.status}")
                        return []
                    
                    content = await response.text()
                    
                    # 使用feedparser解析
                    feed = feedparser.parse(content)
                    
                    items = []
                    for entry in feed.entries[:20]:  # 限制每个源最多20条
                        title = entry.get('title', '')
                        description = entry.get('description', entry.get('summary', ''))
                        link = entry.get('link', '')
                        pub_date = entry.get('published', '')
                        
                        # 解析时间戳
                        try:
                            if pub_date:
                                timestamp = int(datetime.strptime(
                                    pub_date, 
                                    '%a, %d %b %Y %H:%M:%S %z'
                                ).timestamp() * 1000)
                            else:
                                timestamp = int(datetime.now().timestamp() * 1000)
                        except:
                            timestamp = int(datetime.now().timestamp() * 1000)
                        
                        # 分析情绪
                        sentiment = self._analyze_sentiment(title, description)
                        
                        items.append({
                            'title': title,
                            'description': description,
                            'link': link,
                            'pub_date': pub_date,
                            'timestamp': timestamp,
                            'source': source['name'],
                            'sentiment': sentiment,
                            'relevance': 'high' if sentiment['mentioned_coins'] else 'low'
                        })
                    
                    return items
        
        except asyncio.TimeoutError:
            logger.warning(f"{source['name']} 请求超时")
            return []
        except Exception as e:
            logger.error(f"{source['name']} 获取失败: {e}")
            return []
    
    async def get_all_news(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """获取所有新闻（带缓存）"""
        # 检查缓存
        if not force_refresh and self.news_cache['items'] and \
           (datetime.now().timestamp() * 1000 - self.news_cache['timestamp']) < self.CACHE_DURATION:
            logger.debug("使用缓存的新闻数据")
            return self.news_cache['items']
        
        logger.info("获取RSS新闻...")
        all_news = []
        
        for source in RSS_SOURCES:
            items = await self._fetch_rss_feed(source)
            all_news.extend(items)
            
            # 延迟避免频率限制
            await asyncio.sleep(0.5)
        
        # 按时间排序
        all_news.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # 更新缓存（只保留最新50条）
        self.news_cache = {
            'items': all_news[:50],
            'timestamp': int(datetime.now().timestamp() * 1000)
        }
        self._save_cache()
        
        return self.news_cache['items']
    
    async def get_coin_news_sentiment(self, coin: str) -> Optional[CoinNewsSentiment]:
        """获取特定币种的新闻情绪"""
        news = await self.get_all_news()
        coin_aliases = KEYWORDS['coins'].get(coin, [coin.lower()])
        
        # 筛选相关新闻（24小时内）
        one_day_ago = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        relevant_news = []
        
        for item in news:
            if item['timestamp'] < one_day_ago:
                continue
            
            text = (item['title'] + ' ' + item['description']).lower()
            if any(alias.lower() in text for alias in coin_aliases):
                relevant_news.append(item)
        
        if not relevant_news:
            return None
        
        # 计算平均情绪
        avg_score = sum(item['sentiment']['score'] for item in relevant_news) / len(relevant_news)
        bullish_count = sum(1 for item in relevant_news if item['sentiment']['is_bullish'])
        bearish_count = sum(1 for item in relevant_news if item['sentiment']['is_bearish'])
        
        return CoinNewsSentiment(
            score=round(avg_score),
            news_count=len(relevant_news),
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            recent_news=[{
                'title': item['title'],
                'source': item['source'],
                'timestamp': item['timestamp'],
                'sentiment_score': item['sentiment']['score']
            } for item in relevant_news[:3]],
            timestamp=int(datetime.now().timestamp() * 1000)
        )
    
    async def get_overall_market_sentiment(self) -> Dict[str, Any]:
        """获取整体市场情绪"""
        news = await self.get_all_news()
        one_day_ago = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
        recent_news = [item for item in news if item['timestamp'] >= one_day_ago]
        
        if not recent_news:
            return {'score': 5, 'news_count': 0, 'bullish_count': 0, 'bearish_count': 0}
        
        avg_score = sum(item['sentiment']['score'] for item in recent_news) / len(recent_news)
        bullish_count = sum(1 for item in recent_news if item['sentiment']['is_bullish'])
        bearish_count = sum(1 for item in recent_news if item['sentiment']['is_bearish'])
        
        return {
            'score': round(avg_score),
            'news_count': len(recent_news),
            'bullish_count': bullish_count,
            'bearish_count': bearish_count
        }


# 全局单例
rss_monitor = RSSMonitor()
