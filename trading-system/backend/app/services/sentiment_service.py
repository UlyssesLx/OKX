"""
市场情绪数据服务
整合 CoinGecko 数据和 RSS 新闻情绪分析
"""
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger


class SentimentService:
    def __init__(self):
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.news_api_base = "https://cryptopanic.com/api/v1"
        self._cache: Dict[str, Dict] = {}
        self._cache_duration = 300  # 5分钟缓存
    
    async def get_coingecko_data(self, coin: str) -> Optional[Dict[str, Any]]:
        try:
            coin_id = self._get_coingecko_id(coin)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.coingecko_base}/coins/{coin_id}",
                    params={
                        "localization": "false",
                        "tickers": "false",
                        "market_data": "true",
                        "community_data": "true",
                        "developer_data": "false"
                    }
                )
                
                if response.status_code != 200:
                    logger.warning(f"CoinGecko API error for {coin}: {response.status_code}")
                    return None
                
                data = response.json()
                market_data = data.get("market_data", {})
                community_data = data.get("community_data", {})
                
                price = market_data.get("current_price", {}).get("usd", 0)
                price_change_24h = market_data.get("price_change_percentage_24h", 0)
                price_change_7d = market_data.get("price_change_percentage_7d", 0)
                
                market_cap_rank = market_data.get("market_cap_rank", 999)
                total_volume = market_data.get("total_volume", {}).get("usd", 0)
                
                sentiment_up = community_data.get("sentiment_votes_up_percentage", 50)
                sentiment_down = community_data.get("sentiment_votes_down_percentage", 50)
                
                trend_score = self._calculate_trend_score(
                    price_change_24h, price_change_7d, sentiment_up, market_cap_rank
                )
                
                return {
                    "coin": coin,
                    "price": price,
                    "price_change_24h": price_change_24h or 0,
                    "price_change_7d": price_change_7d or 0,
                    "market_cap_rank": market_cap_rank,
                    "total_volume": total_volume,
                    "sentiment_up": sentiment_up,
                    "sentiment_down": sentiment_down,
                    "trend_score": trend_score,
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"CoinGecko data fetch error for {coin}: {e}")
            return None
    
    def _get_coingecko_id(self, coin: str) -> str:
        coin_map = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin",
            "LINK": "chainlink",
            "LTC": "litecoin",
            "BNB": "binancecoin",
            "SUI": "sui",
            "AVAX": "avalanche-2",
            "DOT": "polkadot",
            "MATIC": "matic-network",
            "ARB": "arbitrum",
            "OP": "optimism"
        }
        return coin_map.get(coin.upper(), coin.lower())
    
    def _calculate_trend_score(
        self, 
        price_change_24h: float, 
        price_change_7d: float,
        sentiment_up: float,
        market_cap_rank: int
    ) -> int:
        score = 5
        
        if price_change_24h > 10:
            score += 2
        elif price_change_24h > 5:
            score += 1.5
        elif price_change_24h > 0:
            score += 0.5
        elif price_change_24h < -10:
            score -= 2
        elif price_change_24h < -5:
            score -= 1.5
        elif price_change_24h < 0:
            score -= 0.5
        
        if price_change_7d > 20:
            score += 1
        elif price_change_7d > 10:
            score += 0.5
        elif price_change_7d < -20:
            score -= 1
        elif price_change_7d < -10:
            score -= 0.5
        
        if sentiment_up > 70:
            score += 1
        elif sentiment_up > 60:
            score += 0.5
        elif sentiment_up < 30:
            score -= 1
        elif sentiment_up < 40:
            score -= 0.5
        
        if market_cap_rank <= 10:
            score += 0.5
        
        return max(1, min(10, round(score)))
    
    async def get_news_sentiment(self, coin: str) -> Optional[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.coingecko.com/api/v3/status_updates",
                    params={
                        "project_type": "coin",
                        "per_page": 10
                    }
                )
                
                if response.status_code != 200:
                    return self._get_default_sentiment(coin)
                
                data = response.json()
                updates = data.get("status_updates", [])
                
                relevant_updates = [
                    u for u in updates 
                    if coin.lower() in u.get("project", {}).get("symbol", "").lower()
                    or coin.lower() in u.get("project", {}).get("name", "").lower()
                ][:5]
                
                if not relevant_updates:
                    return self._get_default_sentiment(coin)
                
                bullish_keywords = ["bullish", "surge", "rally", "gain", "positive", "growth", "adoption", "partnership"]
                bearish_keywords = ["bearish", "drop", "crash", "decline", "negative", "loss", "concern", "regulation"]
                
                bullish_count = 0
                bearish_count = 0
                
                for update in relevant_updates:
                    description = update.get("description", "").lower()
                    if any(kw in description for kw in bullish_keywords):
                        bullish_count += 1
                    if any(kw in description for kw in bearish_keywords):
                        bearish_count += 1
                
                total = bullish_count + bearish_count
                if total > 0:
                    sentiment_score = 5 + (bullish_count - bearish_count) * 1.5
                else:
                    sentiment_score = 5
                
                return {
                    "coin": coin,
                    "news_count": len(relevant_updates),
                    "bullish_count": bullish_count,
                    "bearish_count": bearish_count,
                    "score": max(1, min(10, round(sentiment_score))),
                    "recent_news": [
                        {
                            "title": u.get("project", {}).get("name", ""),
                            "description": u.get("description", "")[:100] + "...",
                            "created_at": u.get("created_at", "")
                        }
                        for u in relevant_updates[:3]
                    ],
                    "timestamp": datetime.utcnow().isoformat()
                }
        except Exception as e:
            logger.error(f"News sentiment fetch error for {coin}: {e}")
            return self._get_default_sentiment(coin)
    
    def _get_default_sentiment(self, coin: str) -> Dict[str, Any]:
        return {
            "coin": coin,
            "news_count": 0,
            "bullish_count": 0,
            "bearish_count": 0,
            "score": 5,
            "recent_news": [],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_combined_sentiment(self, coin: str) -> Dict[str, Any]:
        coingecko_data = await self.get_coingecko_data(coin)
        news_sentiment = await self.get_news_sentiment(coin)
        
        coingecko_score = coingecko_data.get("trend_score", 5) if coingecko_data else 5
        news_score = news_sentiment.get("score", 5) if news_sentiment else 5
        
        combined_score = round(coingecko_score * 0.6 + news_score * 0.4)
        
        return {
            "coin": coin,
            "coingecko": coingecko_data,
            "news": news_sentiment,
            "combined_score": max(1, min(10, combined_score)),
            "timestamp": datetime.utcnow().isoformat()
        }


sentiment_service = SentimentService()
