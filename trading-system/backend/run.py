"""
启动脚本 - 确保日志配置正确加载
"""
import sys
import logging
from datetime import datetime, timezone, timedelta
from loguru import logger

BEIJING_TZ = timezone(timedelta(hours=8))

# 禁用 uvicorn 的默认日志
logging.getLogger("uvicorn").handlers = []
logging.getLogger("uvicorn.access").disabled = True
logging.getLogger("uvicorn.error").handlers = []

def format_with_beijing_time(record):
    """格式化日志，使用北京时间"""
    beijing_now = datetime.now(BEIJING_TZ)
    record["extra"]["beijing_time"] = beijing_now.strftime("%Y-%m-%d %H:%M:%S")
    return True

# 配置 loguru 日志
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{extra[beijing_time]}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    filter=format_with_beijing_time
)

# 导入并运行 uvicorn
import uvicorn

if __name__ == "__main__":
    logger.info("🚀 正在启动服务器...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="warning",
        access_log=False,
        # 使用自定义日志配置
        log_config=None
    )
