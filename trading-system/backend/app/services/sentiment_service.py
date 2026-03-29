"""
市场情绪数据服务
整合 CoinGecko 数据和 RSS 新闻情绪分析
支持缓存和失败降级机制
"""
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger


class SentimentService:
    def __init__(self, cache_duration: int = 300):
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.news_api_base = "https://cryptopanic.com/api/v1"
        self._cache: Dict[str, Dict] = {}
        self._cache_duration = cache_duration  # 缓存时间（秒）

    def _is_cache_valid(self, coin: str, data_type: str) -> bool:
        """检查缓存是否有效"""
        key = f"{coin}_{data_type}"
        if key not in self._cache:
            return False
        cached = self._cache[key]
        elapsed = (datetime.now() - cached.get("cached_at", datetime.min)).total_seconds()
        return elapsed < self._cache_duration

    def _get_from_cache(self, coin: str, data_type: str) -> Optional[Dict]:
        """从缓存获取数据"""
        key = f"{coin}_{data_type}"
        if self._is_cache_valid(coin, data_type):
            return self._cache[key].get("data")
        return None

    def _set_cache(self, coin: str, data_type: str, data: Dict) -> None:
        """设置缓存"""
        key = f"{coin}_{data_type}"
        self._cache[key] = {
            "data": data,
            "cached_at": datetime.now()
        }

    async def get_coingecko_data(
        self,
        coin: str,
        use_cache: bool = True,
        timeout: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """获取 CoinGecko 情绪数据（带缓存和超时）"""
        # 尝试从缓存获取
        if use_cache:
            cached = self._get_from_cache(coin, "coingecko")
            if cached:
                logger.debug(f"CoinGecko {coin}: 使用缓存数据")
                return cached

        try:
            coin_id = self._get_coingecko_id(coin)
            async with httpx.AsyncClient(timeout=timeout) as client:
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

                result = {
                    "coin": coin,
                    "price": price,
                    "price_change_24h": price_change_24h or 0,
                    "price_change_7d": price_change_7d or 0,
                    "market_cap_rank": market_cap_rank,
                    "total_volume": total_volume,
                    "sentiment_up": sentiment_up,
                    "sentiment_down": sentiment_down,
                    "trend_score": trend_score,
                    "timestamp": datetime.now().isoformat()
                }

                # 缓存结果
                if use_cache:
                    self._set_cache(coin, "coingecko", result)

                return result
        except httpx.TimeoutException:
            logger.warning(f"CoinGecko API timeout for {coin}")
            return None
        except Exception as e:
            logger.error(f"CoinGecko data fetch error for {coin}: {e}")
            return None

    def _get_coingecko_id(self, coin: str) -> str:
        """获取 CoinGecko 币种 ID"""
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
        """计算趋势评分"""
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

    async def get_news_sentiment(
        self,
        coin: str,
        use_cache: bool = True,
        timeout: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """获取新闻情绪数据（带缓存和超时）"""
        # 尝试从缓存获取
        if use_cache:
            cached = self._get_from_cache(coin, "news")
            if cached:
                logger.debug(f"News sentiment {coin}: 使用缓存数据")
                return cached

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
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
                    result = self._get_default_sentiment(coin)
                    if use_cache:
                        self._set_cache(coin, "news", result)
                    return result

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

                result = {
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
                    "timestamp": datetime.now().isoformat()
                }

                # 缓存结果
                if use_cache:
                    self._set_cache(coin, "news", result)

                return result
        except httpx.TimeoutException:
            logger.warning(f"News sentiment API timeout for {coin}")
            return None
        except Exception as e:
            logger.error(f"News sentiment fetch error for {coin}: {e}")
            return None

    def _get_default_sentiment(self, coin: str) -> Dict[str, Any]:
        """获取默认情绪数据"""
        return {
            "coin": coin,
            "news_count": 0,
            "bullish_count": 0,
            "bearish_count": 0,
            "score": 5,
            "recent_news": [],
            "timestamp": datetime.now().isoformat()
        }

    async def get_combined_sentiment(
        self,
        coin: str,
        use_cache: bool = True,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """获取融合后的综合情绪数据"""
        coingecko_data = await self.get_coingecko_data(coin, use_cache=use_cache, timeout=timeout)
        news_sentiment = await self.get_news_sentiment(coin, use_cache=use_cache, timeout=timeout)

        coingecko_score = coingecko_data.get("trend_score", 5) if coingecko_data else 5
        news_score = news_sentiment.get("score", 5) if news_sentiment else 5

        # 加权平均：CoinGecko 60% + 新闻 40%
        combined_score = round(coingecko_score * 0.6 + news_score * 0.4)

        return {
            "coin": coin,
            "coingecko": coingecko_data,
            "news": news_sentiment,
            "combined_score": max(1, min(10, combined_score)),
            "coingecko_available": coingecko_data is not None,
            "news_available": news_sentiment is not None,
            "timestamp": datetime.now().isoformat()
        }

    async def fuse_with_technical_score(
        self,
        coin: str,
        technical_score: int,
        coingecko_weight: float = 0.4,
        news_weight: float = 0.2,
        technical_weight: float = 0.4,
        use_cache: bool = True,
        timeout: float = 5.0,
        bearish_alert_threshold: int = 3
    ) -> Dict[str, Any]:
        """
        将情绪数据与技术面评分融合（对齐 ai_trading_bot.js）

        权重分配:
        - 技术面: 40%
        - CoinGecko: 40%
        - 新闻: 20%

        Args:
            coin: 币种
            technical_score: 技术面评分
            coingecko_weight: CoinGecko权重
            news_weight: 新闻权重
            technical_weight: 技术面权重
            use_cache: 是否使用缓存
            timeout: 超时时间
            bearish_alert_threshold: 极度看跌阈值

        Returns:
            融合后的评分和详细信息
        """
        # 获取 CoinGecko 数据
        cg_data = await self.get_coingecko_data(coin, use_cache=use_cache, timeout=timeout)
        cg_score = cg_data.get("trend_score", 5) if cg_data else 5

        # 获取新闻情绪
        news_data = await self.get_news_sentiment(coin, use_cache=use_cache, timeout=timeout)
        news_score = news_data.get("score", 5) if news_data else 5

        # 原始技术面评分
        original_score = technical_score

        # 融合评分: 技术面 * 权重 + CoinGecko * 权重 + 新闻 * 权重
        fused_score = round(
            original_score * technical_weight +
            cg_score * coingecko_weight +
            news_score * news_weight
        )
        fused_score = max(1, min(10, fused_score))

        # 极度看跌警告（对齐 ai_trading_bot.js）
        warning = None
        if cg_score <= bearish_alert_threshold and original_score >= 6:
            warning = f"⚠️ 技术面看涨但CoinGecko情绪极度看跌({cg_score}分)，谨慎操作！"
            fused_score = min(fused_score, 5)

        return {
            "coin": coin,
            "original_technical_score": original_score,
            "coingecko_score": cg_score,
            "news_score": news_score,
            "fused_score": fused_score,
            "weights": {
                "technical": technical_weight,
                "coingecko": coingecko_weight,
                "news": news_weight
            },
            "warning": warning,
            "coingecko_available": cg_data is not None,
            "news_available": news_data is not None,
            "timestamp": datetime.now().isoformat()
        }

    def clear_cache(self, coin: str = None):
        """清空缓存"""
        if coin:
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{coin}_")]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()

    async def get_fear_greed_index(
        self,
        use_cache: bool = True,
        timeout: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """
        获取加密货币恐慌贪婪指数（免费API）
        来源: Alternative.me Crypto Fear & Greed Index
        无需API Key，完全免费
        """
        cache_key = "fear_greed_index"
        
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached and (datetime.now() - cached.get("cached_at", datetime.min)).total_seconds() < self._cache_duration:
                logger.debug("Fear & Greed Index: 使用缓存数据")
                return cached.get("data")
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get("https://api.alternative.me/fng/?limit=1")
                
                if response.status_code != 200:
                    logger.warning(f"Fear & Greed API error: {response.status_code}")
                    return None
                
                data = response.json()
                fng_data = data.get("data", [])[0] if data.get("data") else None
                
                if not fng_data:
                    return None
                
                value = int(fng_data.get("value", 50))
                classification = fng_data.get("value_classification", "Neutral")
                timestamp = fng_data.get("timestamp", "")
                
                # 转换为 1-10 评分
                # 0-25: Extreme Fear (1-2分)
                # 25-50: Fear (3-4分)
                # 50-75: Greed (6-7分)
                # 75-100: Extreme Greed (8-10分)
                if value <= 25:
                    score = 1 + (value / 25)
                elif value <= 50:
                    score = 3 + ((value - 25) / 25)
                elif value <= 75:
                    score = 6 + ((value - 50) / 25)
                else:
                    score = 8 + ((value - 75) / 25)
                
                score = max(1, min(10, round(score)))
                
                result = {
                    "value": value,
                    "classification": classification,
                    "score": score,
                    "timestamp": timestamp,
                    "fetched_at": datetime.now().isoformat()
                }
                
                if use_cache:
                    self._cache[cache_key] = {
                        "data": result,
                        "cached_at": datetime.now()
                    }
                
                logger.info(f"📊 Fear & Greed Index: {value} ({classification}) → {score}分")
                return result
                
        except httpx.TimeoutException:
            logger.warning("Fear & Greed API timeout")
            return None
        except Exception as e:
            logger.error(f"Fear & Greed fetch error: {e}")
            return None

    async def fuse_with_technical_score_v2(
        self,
        coin: str,
        technical_score: int,
        coingecko_weight: float = 0.3,
        fear_greed_weight: float = 0.3,
        technical_weight: float = 0.4,
        use_cache: bool = True,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """
        融合技术面评分与免费情绪数据（推荐使用）
        
        数据源（全部免费）:
        - CoinGecko: 币种情绪数据（30%）
        - Fear & Greed Index: 市场整体情绪（30%）
        - 技术面: 本地技术分析（40%）
        
        优势:
        - 完全免费，无需 API Key
        - 数据源稳定可靠
        - 覆盖币种情绪和市场整体情绪
        """
        cg_data = await self.get_coingecko_data(coin, use_cache=use_cache, timeout=timeout)
        cg_score = cg_data.get("trend_score", 5) if cg_data else 5
        
        fg_data = await self.get_fear_greed_index(use_cache=use_cache, timeout=timeout)
        fg_score = fg_data.get("score", 5) if fg_data else 5
        
        original_score = technical_score
        
        fused_score = round(
            original_score * technical_weight +
            cg_score * coingecko_weight +
            fg_score * fear_greed_weight
        )
        fused_score = max(1, min(10, fused_score))
        
        warning = None
        if fg_score <= 2 and original_score >= 6:
            warning = f"⚠️ 技术面看涨但市场极度恐慌(Fear & Greed: {fg_data.get('value', 50)})，谨慎操作！"
            fused_score = min(fused_score, 5)
        
        return {
            "coin": coin,
            "original_technical_score": original_score,
            "coingecko_score": cg_score,
            "fear_greed_score": fg_score,
            "fused_score": fused_score,
            "weights": {
                "technical": technical_weight,
                "coingecko": coingecko_weight,
                "fear_greed": fear_greed_weight
            },
            "warning": warning,
            "coingecko_available": cg_data is not None,
            "fear_greed_available": fg_data is not None,
            "fear_greed_data": fg_data,
            "timestamp": datetime.now().isoformat()
        }


sentiment_service = SentimentService()
