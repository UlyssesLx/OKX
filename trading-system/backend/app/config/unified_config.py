"""
统一交易配置管理
整合所有交易策略和风控配置
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime


# ============================================
# 风险管理配置
# ============================================
class RiskManagementConfig(BaseModel):
    """风险管理配置"""
    max_per_trade: float = Field(default=10, description="单笔交易最大金额(USDT)")
    max_per_day: float = Field(default=30, description="每日最大交易金额(USDT)")
    stop_loss: float = Field(default=-5.0, description="止损百分比(%)")
    take_profit: float = Field(default=10.0, description="止盈百分比(%)")
    max_position_per_coin: float = Field(default=30.0, description="单币种最大持仓(USDT)")
    min_cash_reserve: float = Field(default=20.0, description="最小现金保留(USDT)")


# ============================================
# 网格交易配置
# ============================================
class GridConfig(BaseModel):
    """网格交易配置"""
    name: str
    inst_id: str
    investment: float
    min_price: float
    max_price: float
    grid_count: int
    status: str = "active"


class GridTradingConfig(BaseModel):
    """网格交易策略配置"""
    enabled: bool = True
    grids: List[GridConfig] = []


# ============================================
# 手动交易配置
# ============================================
class ManualTradingConfig(BaseModel):
    """手动交易配置"""
    enabled: bool = True
    approach: str = "自主寻找机会，不限制币种"
    analysis: Dict[str, float] = {
        "sentimentWeight": 40,
        "technicalWeight": 40,
        "marketSentimentWeight": 20
    }
    evaluation_interval: str = "每小时"
    watchlist: List[str] = ["BTC", "ETH", "XRP", "SOL", "DOGE", "ADA", "LINK", "UNI", "AVAX", "SUI"]


# ============================================
# 自动执行规则
# ============================================
class AutoExecutionRule(BaseModel):
    """自动执行规则"""
    condition: str
    action: str


class AutoExecutionConfig(BaseModel):
    """自动执行配置"""
    enabled: bool = True
    rules: List[str] = [
        "重大利好舆情 → 加仓",
        "重大利空舆情 → 减仓/止损",
        "突破关键阻力 → 追涨",
        "跌破关键支撑 → 止损/观望",
        "马斯克提及币种 → 立即评估",
        "特朗普政策新闻 → 30分钟内分析"
    ]


# ============================================
# 回调加仓配置
# ============================================
class PullbackConfig(BaseModel):
    """回调加仓配置"""
    enabled: bool = True
    pullback_threshold: float = 0.97  # 回调阈值97%
    max_rebuy_amount: float = 15.0  # 最大重新买入金额(USDT)
    cooldown_minutes: int = 60  # 冷却时间(分钟)


# ============================================
# 高级配置
# ============================================
class AdvancedTradingConfig(BaseModel):
    """高级交易配置"""
    # 风险管理
    risk_management: RiskManagementConfig = RiskManagementConfig()
    
    # 网格交易
    grid_trading: GridTradingConfig = GridTradingConfig()
    
    # 手动交易
    manual_trading: ManualTradingConfig = ManualTradingConfig()
    
    # 自动执行
    auto_execution: AutoExecutionConfig = AutoExecutionConfig()
    
    # 回调加仓
    pullback: PullbackConfig = PullbackConfig()


# ============================================
# 交易授权配置
# ============================================
class TradingAuthorization(BaseModel):
    """交易授权配置"""
    user: str = "黄玮康"
    confirmed_at: str = datetime.now().isoformat()
    scope: str = "完全自主决策和执行"


class UnifiedTradingConfig(BaseModel):
    """统一交易配置"""
    version: str = "2.0"
    updated_at: str = datetime.now().isoformat()
    mode: str = "完全自主交易"
    authorization: TradingAuthorization = TradingAuthorization()
    
    # 核心配置
    trading_config: AdvancedTradingConfig = AdvancedTradingConfig()
    
    # 报告配置
    reporting_interval: str = "每30分钟"
    reporting_format: str = "7部分表格"
    reporting_delivery: str = "当前对话直接显示"


# ============================================
# 默认配置
# ============================================
def get_default_unified_config() -> UnifiedTradingConfig:
    """获取默认统一配置"""
    return UnifiedTradingConfig(
        trading_config=AdvancedTradingConfig(
            grid_trading=GridTradingConfig(
                enabled=True,
                grids=[
                    GridConfig(
                        name="ETH-USDT-积极",
                        inst_id="ETH-USDT",
                        investment=40,
                        min_price=1800,
                        max_price=2200,
                        grid_count=15,
                        status="active"
                    ),
                    GridConfig(
                        name="DOGE-USDT-积极",
                        inst_id="DOGE-USDT",
                        investment=10,
                        min_price=0.09,
                        max_price=0.11,
                        grid_count=10,
                        status="active"
                    )
                ]
            ),
            pullback=PullbackConfig(
                enabled=True,
                pullback_threshold=0.97,
                max_rebuy_amount=15.0,
                cooldown_minutes=60
            )
        )
    )


# 创建全局配置实例
unified_config = get_default_unified_config()


# ============================================
# 配置管理函数
# ============================================
def save_config_to_file(config: UnifiedTradingConfig, file_path: str):
    """保存配置到文件"""
    import json
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(config.model_dump(), f, ensure_ascii=False, indent=2)
    logger.info(f"配置已保存到: {file_path}")


def load_config_from_file(file_path: str) -> Optional[UnifiedTradingConfig]:
    """从文件加载配置"""
    import json
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return UnifiedTradingConfig(**data)
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        return None


def update_grid_config(
    grid_name: str,
    investment: Optional[float] = None,
    status: Optional[str] = None
):
    """更新网格配置"""
    for grid in unified_config.trading_config.grid_trading.grids:
        if grid.name == grid_name:
            if investment is not None:
                grid.investment = investment
            if status is not None:
                grid.status = status
            logger.info(f"更新网格配置: {grid_name}")
            return True
    logger.warning(f"未找到网格: {grid_name}")
    return False


def add_grid_config(grid: GridConfig):
    """添加网格配置"""
    unified_config.trading_config.grid_trading.grids.append(grid)
    logger.info(f"添加网格配置: {grid.name}")


def remove_grid_config(grid_name: str):
    """移除网格配置"""
    grids = unified_config.trading_config.grid_trading.grids
    unified_config.trading_config.grid_trading.grids = [
        g for g in grids if g.name != grid_name
    ]
    logger.info(f"移除网格配置: {grid_name}")


def update_pullback_config(
    enabled: Optional[bool] = None,
    pullback_threshold: Optional[float] = None
):
    """更新回调加仓配置"""
    if enabled is not None:
        unified_config.trading_config.pullback.enabled = enabled
    if pullback_threshold is not None:
        unified_config.trading_config.pullback.pullback_threshold = pullback_threshold
    logger.info("更新回调加仓配置")


def get_active_grids() -> List[GridConfig]:
    """获取活跃的网格列表"""
    return [
        grid
        for grid in unified_config.trading_config.grid_trading.grids
        if grid.status == "active"
    ]


def get_watchlist() -> List[str]:
    """获取观察列表"""
    return unified_config.trading_config.manual_trading.watchlist
