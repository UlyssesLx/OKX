"""
外部数据API端点
提供RSS、Twitter、LunarCrush等外部数据的访问接口
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, List
from datetime import datetime
from loguru import logger

from app.services.external_data_service import external_data_service

router = APIRouter(prefix="/api/v1/external", tags=["external-data"])


@router.get("/sentiment/{coin}")
async def get_coin_sentiment(
    coin: str,
    twitter_username: Optional[str] = Query(None, description="Twitter用户名")
):
    """
    获取币种综合情绪报告
    
    Args:
        coin: 币种符号（如BTC、ETH）
        twitter_username: Twitter用户名（可选）
    
    Returns:
        综合情绪报告，包含RSS、Twitter、LunarCrush等多源数据
    """
    try:
        report = await external_data_service.get_coin_sentiment(coin, twitter_username)
        return {
            "success": True,
            "data": report.to_dict()
        }
    except Exception as e:
        logger.error(f"获取{coin}情绪报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment/batch")
async def get_batch_sentiment(
    coins: str = Query(..., description="币种列表，逗号分隔，如BTC,ETH,SOL"),
    usernames: Optional[str] = Query(None, description="Twitter用户名映射，JSON格式")
):
    """
    批量获取多个币种的情绪报告
    
    Args:
        coins: 币种列表，逗号分隔
        usernames: Twitter用户名映射，JSON格式（可选）
    
    Returns:
        币种到情绪报告的映射
    """
    try:
        coin_list = [c.strip().upper() for c in coins.split(',')]
        
        user_map = {}
        if usernames:
            import json
            try:
                user_map = json.loads(usernames)
            except json.JSONDecodeError:
                pass
        
        reports = await external_data_service.batch_get_sentiment(coin_list, user_map)
        
        return {
            "success": True,
            "data": {
                coin: report.to_dict() for coin, report in reports.items()
            }
        }
    except Exception as e:
        logger.error(f"批量获取情绪报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-sentiment")
async def get_market_sentiment():
    """
    获取整体市场情绪
    
    Returns:
        整体市场情绪数据
    """
    try:
        sentiment = await external_data_service.get_overall_market_sentiment()
        return {
            "success": True,
            "data": sentiment
        }
    except Exception as e:
        logger.error(f"获取市场情绪失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news")
async def get_latest_news(
    limit: int = Query(20, ge=1, le=100, description="返回新闻数量")
):
    """
    获取最新新闻
    
    Args:
        limit: 返回新闻数量，最多100条
    
    Returns:
        最新新闻列表
    """
    try:
        news = await external_data_service.get_latest_news(limit)
        return {
            "success": True,
            "data": news[:limit]
        }
    except Exception as e:
        logger.error(f"获取最新新闻失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rss/{coin}")
async def get_rss_sentiment(coin: str):
    """
    获取币种RSS新闻情绪
    
    Args:
        coin: 币种符号
    
    Returns:
        RSS新闻情绪数据
    """
    try:
        from app.services.external_data_sources import rss_monitor
        sentiment = await rss_monitor.get_coin_news_sentiment(coin)
        
        if sentiment:
            return {
                "success": True,
                "data": {
                    "score": sentiment.score,
                    "news_count": sentiment.news_count,
                    "bullish_count": sentiment.bullish_count,
                    "bearish_count": sentiment.bearish_count,
                    "recent_news": sentiment.recent_news,
                    "timestamp": sentiment.timestamp
                }
            }
        else:
            return {
                "success": True,
                "data": None,
                "message": f"{coin} 24小时内无相关新闻"
            }
    except Exception as e:
        logger.error(f"获取{coin} RSS情绪失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/twitter/{username}")
async def get_twitter_sentiment(username: str):
    """
    获取Twitter用户情绪分析
    
    Args:
        username: Twitter用户名
    
    Returns:
        Twitter情绪分析数据
    """
    try:
        from app.services.external_data_sources import twitter_monitor
        sentiment = await twitter_monitor.get_user_sentiment(username)
        
        if sentiment:
            return {
                "success": True,
                "data": {
                    "user": {
                        "username": sentiment.user.username,
                        "name": sentiment.user.name,
                        "followers_count": sentiment.user.followers_count,
                        "tweet_count": sentiment.user.tweet_count
                    },
                    "sentiment_score": sentiment.sentiment_score,
                    "bullish_count": sentiment.bullish_count,
                    "bearish_count": sentiment.bearish_count,
                    "tweet_count": len(sentiment.tweets),
                    "recent_tweets": [
                        {
                            "text": tweet.text,
                            "created_at": tweet.created_at,
                            "like_count": tweet.like_count,
                            "retweet_count": tweet.retweet_count
                        }
                        for tweet in sentiment.tweets[:5]
                    ],
                    "timestamp": sentiment.timestamp
                }
            }
        else:
            return {
                "success": False,
                "message": f"无法获取用户 @{username} 的数据"
            }
    except Exception as e:
        logger.error(f"获取Twitter情绪失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lunarcrush/{coin}")
async def get_lunarcrush_sentiment(coin: str):
    """
    获取币种LunarCrush社交媒体情绪
    
    Args:
        coin: 币种符号
    
    Returns:
        LunarCrush社交媒体情绪数据
    """
    try:
        from app.services.external_data_sources import lunarcrush_monitor
        sentiment = await lunarcrush_monitor.get_social_sentiment(coin)
        
        if sentiment:
            return {
                "success": True,
                "data": {
                    "coin": sentiment.coin,
                    "score": sentiment.score,
                    "trend_score": sentiment.trend_score,
                    "bullish_percent": sentiment.bullish_percent,
                    "bearish_percent": sentiment.bearish_percent,
                    "social_volume": sentiment.social_volume,
                    "social_score": sentiment.social_score,
                    "galaxy_score": sentiment.galaxy_score,
                    "price": sentiment.price,
                    "percent_change_24h": sentiment.percent_change_24h,
                    "timestamp": sentiment.timestamp
                }
            }
        else:
            return {
                "success": True,
                "data": None,
                "message": f"{coin} 无LunarCrush数据"
            }
    except Exception as e:
        logger.error(f"获取{coin} LunarCrush情绪失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources/status")
async def get_data_sources_status():
    """
    获取外部数据源状态
    
    Returns:
        各数据源的状态信息
    """
    try:
        from app.core.config import settings
        
        return {
            "success": True,
            "data": {
                "rss": {
                    "enabled": settings.ENABLE_RSS_MONITOR,
                    "sources": [
                        {"name": "CoinDesk", "url": "https://feeds.feedburner.com/CoinDesk"},
                        {"name": "Cointelegraph", "url": "https://cointelegraph.com/rss"},
                        {"name": "Decrypt", "url": "https://decrypt.co/feed"}
                    ]
                },
                "twitter": {
                    "enabled": settings.ENABLE_TWITTER_MONITOR,
                    "configured": bool(settings.TWITTER_CONSUMER_KEY),
                    "api_type": "Twitter API v2"
                },
                "lunarcrush": {
                    "enabled": settings.ENABLE_LUNARCRUSH_MONITOR,
                    "configured": bool(settings.LUNARCRUSH_API_KEY),
                    "api_type": "LunarCrush API v2"
                }
            }
        }
    except Exception as e:
        logger.error(f"获取数据源状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
