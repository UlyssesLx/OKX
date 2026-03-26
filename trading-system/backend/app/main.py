from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys
import logging
from datetime import datetime, timezone, timedelta

from app.api import trading_router, websocket_router, services_router, backtest_router
from app.api.websocket import manager
from app.core.config import settings
from app.services.coordinator import set_ws_broadcast_callback

BEIJING_TZ = timezone(timedelta(hours=8))

logging.getLogger("uvicorn.access").disabled = True

def format_with_beijing_time(record):
    beijing_now = datetime.now(BEIJING_TZ)
    record["extra"]["beijing_time"] = beijing_now.strftime("%Y-%m-%d %H:%M:%S")
    return True

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{extra[beijing_time]}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL,
    filter=format_with_beijing_time
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from app.api import websocket
    if websocket._okx_client and websocket._okx_client._client:
        await websocket._okx_client._client.aclose()
        websocket._okx_client = None

app = FastAPI(
    title="加密货币自动交易系统 API",
    description="基于币市麻雀战法的自动化交易系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trading_router)
app.include_router(websocket_router)
app.include_router(services_router)
app.include_router(backtest_router)

set_ws_broadcast_callback(manager.broadcast)


@app.get("/")
async def root():
    return {
        "name": "加密货币自动交易系统",
        "version": "1.0.0",
        "status": "running",
        "trading_mode": settings.TRADING_MODE
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="warning",
        access_log=False
    )
