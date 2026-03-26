"""
Sub-Agent独立HTTP服务
提供外部数据源API的独立微服务
端口: 3456
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
from datetime import datetime
from loguru import logger
import asyncio

from app.services.external_data_service import external_data_service

app = FastAPI(
    title="市场情绪数据服务",
    description="Sub-Agent模式 - 独立进程运行的外部数据源服务",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# 健康检查
# ============================================
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "MarketSentimentService"
    }


# ============================================
# RSS新闻情绪
# ============================================
@app.get("/rss")
async def get_rss_sentiment(coin: Optional[str] = None):
    """获取RSS新闻情绪"""
    try:
        if coin:
            # 获取特定币种的新闻情绪
            result = await external_data_service.get_rss_sentiment(coin)
            if result is None:
                raise HTTPException(status_code=404, detail=f"未找到{coin}的相关新闻")
            return {
                "coin": coin,
                "sentiment": result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # 获取整体市场新闻情绪
            result = await external_data_service.get_market_news()
            return {
                "newsCount": len(result),
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"RSS服务错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Twitter情绪
# ============================================
@app.get("/twitter")
async def get_twitter_sentiment(username: Optional[str] = None):
    """获取Twitter情绪"""
    try:
        if not username:
            raise HTTPException(status_code=400, detail="缺少username参数")
        
        result = await external_data_service.get_twitter_sentiment(username)
        if result is None:
            raise HTTPException(status_code=404, detail=f"未找到用户{username}的推文")
        
        return {
            "username": username,
            "sentiment": result,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Twitter服务错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# LunarCrush情绪
# ============================================
@app.get("/lunarcrush")
async def get_lunarcrush_sentiment(coin: str):
    """获取LunarCrush社交媒体情绪"""
    try:
        if not coin:
            raise HTTPException(status_code=400, detail="缺少coin参数")
        
        result = await external_data_service.get_lunarcrush_sentiment(coin)
        if result is None:
            raise HTTPException(status_code=404, detail=f"未找到{coin}的LunarCrush数据")
        
        return {
            "coin": coin,
            "sentiment": result,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LunarCrush服务错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 综合情绪数据
# ============================================
@app.get("/sentiment")
async def get_combined_sentiment(coin: str):
    """获取综合情绪数据（整合所有数据源）"""
    try:
        if not coin:
            raise HTTPException(status_code=400, detail="缺少coin参数")
        
        result = await external_data_service.get_combined_sentiment(coin)
        
        return {
            "coin": coin,
            "rss": result["rss"],
            "twitter": result["twitter"],
            "lunarcrush": result["lunarcrush"],
            "combined": result["combined"],
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"综合情绪服务错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 批量查询
# ============================================
@app.get("/sentiment/batch")
async def get_batch_sentiment(coins: str):
    """批量查询多个币种的情绪"""
    try:
        coin_list = coins.split(',')
        result = await external_data_service.get_batch_sentiment(coin_list)
        
        return {
            "coins": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"批量查询服务错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 整体市场情绪
# ============================================
@app.get("/market-sentiment")
async def get_market_sentiment():
    """获取整体市场情绪"""
    try:
        result = await external_data_service.get_overall_market_sentiment()
        
        return {
            "sentiment": result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"整体市场情绪服务错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 数据源状态
# ============================================
@app.get("/sources/status")
async def get_sources_status():
    """获取数据源状态"""
    try:
        status = external_data_service.get_sources_status()
        
        return {
            "sources": status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"数据源状态服务错误: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 定期预热缓存
# ============================================
async def warmup_cache():
    """定期预热缓存"""
    while True:
        try:
            logger.info("🔄 预热RSS缓存...")
            await external_data_service.get_market_news()
            await asyncio.sleep(600)  # 每10分钟
        except Exception as e:
            logger.error(f"预热缓存失败: {str(e)}")
            await asyncio.sleep(60)


# ============================================
# 启动服务
# ============================================
def start_service(host: str = "0.0.0.0", port: int = 3456):
    """启动Sub-Agent服务"""
    logger.info("🚀 市场情绪数据服务启动")
    logger.info(f"📡 端口: {port}")
    logger.info("📊 API端点:")
    logger.info("   GET /health - 健康检查")
    logger.info("   GET /rss?coin=XRP - RSS新闻情绪")
    logger.info("   GET /twitter?username=elonmusk - Twitter情绪")
    logger.info("   GET /lunarcrush?coin=XRP - LunarCrush情绪")
    logger.info("   GET /sentiment?coin=XRP - 综合情绪数据")
    logger.info("   GET /sentiment/batch?coins=BTC,ETH,XRP - 批量情绪查询")
    logger.info("   GET /market-sentiment - 整体市场情绪")
    logger.info("   GET /sources/status - 数据源状态")
    logger.info("")
    logger.info("💡 主交易程序可以通过HTTP API访问此服务")
    
    # 启动缓存预热任务
    asyncio.create_task(warmup_cache())
    
    # 启动FastAPI服务器
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    start_service()
