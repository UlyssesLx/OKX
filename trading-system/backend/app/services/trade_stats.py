"""
交易统计模块
分析交易表现、生成报告
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from loguru import logger

BEIJING_TZ = timezone(timedelta(hours=8))

# 获取数据目录
def get_data_dir() -> Path:
    possible_paths = [
        Path("./data"),
        Path(__file__).parent.parent.parent / "data",
        Path(os.getcwd()) / "data",
    ]
    for path in possible_paths:
        if path.exists():
            return path
    backend_data = Path(__file__).parent.parent.parent / "data"
    backend_data.mkdir(parents=True, exist_ok=True)
    return backend_data


class TradeRecord(BaseModel):
    time: str
    coin: str
    action: str
    price: float
    amount: float
    reason: str = ""
    pnl: float = 0.0
    side: str = "long"
    is_simulation: bool = True  # 默认为模拟盘
    is_swap: bool = False  # 是否为合约交易
    leverage: float = 1.0  # 杠杆倍数


class TradeLog(BaseModel):
    trades: List[TradeRecord] = []
    daily_volume: float = 0.0
    daily_trade_count: int = 0
    last_buy_time: Dict[str, str] = {}


class SummaryStats(BaseModel):
    total_trades: int = 0
    buy_count: int = 0
    sell_count: int = 0
    take_profit_sells: int = 0
    stop_loss_sells: int = 0
    win_rate: float = 0.0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    profit_loss_ratio: float = 0.0
    total_profit: float = 0.0
    total_loss: float = 0.0
    net_profit: float = 0.0


class TodayStats(BaseModel):
    date: str = ""
    trades: int = 0
    buys: int = 0
    sells: int = 0
    volume: float = 0.0


class TradeStats:
    def __init__(self, data_dir: str = "."):
        self.data_dir = Path(data_dir)
        self.trade_log_file = self.data_dir / "trade_log.json"
        self.stats_file = self.data_dir / "trade_stats.json"
        self.history_file = self.data_dir / "trade_history.json"
        self._load_trade_log()
    
    def _load_trade_log(self):
        if self.trade_log_file.exists():
            try:
                with open(self.trade_log_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.trade_log = TradeLog(**data)
            except Exception as e:
                logger.error(f"Failed to load trade log: {e}")
                self.trade_log = TradeLog()
        else:
            self.trade_log = TradeLog()
    
    def _save_trade_log(self):
        try:
            with open(self.trade_log_file, "w", encoding="utf-8") as f:
                json.dump(self.trade_log.model_dump(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save trade log: {e}")
    
    def record_trade(self, trade: TradeRecord):
        self.trade_log.trades.append(trade)

        if trade.action == "buy":
            self.trade_log.last_buy_time[trade.coin] = trade.time
            # amount 已经是 USDT 价值，不需要再乘以 price
            self.trade_log.daily_volume += trade.amount

        self.trade_log.daily_trade_count += 1
        self._save_trade_log()
    
    def get_today_trades_for_coin(self, coin: str) -> List[TradeRecord]:
        """获取今日指定币种的交易记录"""
        today = datetime.now().strftime("%Y-%m-%d")
        return [
            t for t in self.trade_log.trades
            if t.coin == coin and t.time.startswith(today)
        ]
    
    def calculate_stats(self, is_simulation: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        trades = self.trade_log.trades
        
        if is_simulation is not None:
            trades = [t for t in trades if t.is_simulation == is_simulation]
        
        if not trades:
            return None
        
        open_long_trades = [t for t in trades if t.action == "buy"]
        close_long_trades = [t for t in trades if t.action == "sell"]
        open_short_trades = [t for t in trades if t.action == "sell_short"]
        close_short_trades = [t for t in trades if t.action == "buy_short"]
        
        all_close_trades = close_long_trades + close_short_trades
        
        total_profit = 0.0
        total_loss = 0.0
        profit_count = 0
        loss_count = 0
        take_profit_sells = 0
        stop_loss_sells = 0
        
        long_profit = 0.0
        long_loss = 0.0
        long_win = 0
        long_loss_count = 0
        short_profit = 0.0
        short_loss = 0.0
        short_win = 0
        short_loss_count = 0
        
        for t in close_long_trades:
            pnl = t.pnl
            
            if "止盈" in t.reason or "盈利" in t.reason:
                take_profit_sells += 1
                if pnl > 0:
                    total_profit += pnl
                    profit_count += 1
                    long_profit += pnl
                    long_win += 1
                else:
                    total_loss += abs(pnl)
                    loss_count += 1
                    long_loss += abs(pnl)
                    long_loss_count += 1
            elif "止损" in t.reason or "亏损" in t.reason:
                stop_loss_sells += 1
                if pnl < 0:
                    total_loss += abs(pnl)
                    loss_count += 1
                    long_loss += abs(pnl)
                    long_loss_count += 1
            elif pnl > 0:
                total_profit += pnl
                profit_count += 1
                long_profit += pnl
                long_win += 1
            elif pnl < 0:
                total_loss += abs(pnl)
                loss_count += 1
                long_loss += abs(pnl)
                long_loss_count += 1
        
        for t in close_short_trades:
            pnl = t.pnl
            
            if pnl > 0:
                total_profit += pnl
                profit_count += 1
                short_profit += pnl
                short_win += 1
            elif pnl < 0:
                total_loss += abs(pnl)
                loss_count += 1
                short_loss += abs(pnl)
                short_loss_count += 1
        
        win_rate = (profit_count / len(all_close_trades) * 100) if all_close_trades else 0
        avg_profit = total_profit / profit_count if profit_count else 0
        avg_loss = total_loss / loss_count if loss_count else 0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss else 0
        
        coin_stats: Dict[str, Dict] = {}
        for t in trades:
            if t.coin not in coin_stats:
                coin_stats[t.coin] = {
                    "buys": 0, "sells": 0, "profit": 0, "loss": 0,
                    "open_long": 0, "close_long": 0,
                    "open_short": 0, "close_short": 0,
                    "long_profit": 0.0, "long_loss": 0.0,
                    "short_profit": 0.0, "short_loss": 0.0,
                    "long_win": 0, "long_loss_count": 0,
                    "short_win": 0, "short_loss_count": 0
                }
            
            if t.action == "buy":
                coin_stats[t.coin]["buys"] += 1
                coin_stats[t.coin]["open_long"] += 1
            elif t.action == "sell":
                coin_stats[t.coin]["sells"] += 1
                coin_stats[t.coin]["close_long"] += 1
                if t.pnl > 0:
                    coin_stats[t.coin]["profit"] += 1
                    coin_stats[t.coin]["long_win"] += 1
                    coin_stats[t.coin]["long_profit"] += t.pnl
                elif t.pnl < 0:
                    coin_stats[t.coin]["loss"] += 1
                    coin_stats[t.coin]["long_loss_count"] += 1
                    coin_stats[t.coin]["long_loss"] += abs(t.pnl)
            elif t.action == "sell_short":
                coin_stats[t.coin]["sells"] += 1
                coin_stats[t.coin]["open_short"] += 1
            elif t.action == "buy_short":
                coin_stats[t.coin]["buys"] += 1
                coin_stats[t.coin]["close_short"] += 1
                if t.pnl > 0:
                    coin_stats[t.coin]["profit"] += 1
                    coin_stats[t.coin]["short_win"] += 1
                    coin_stats[t.coin]["short_profit"] += t.pnl
                elif t.pnl < 0:
                    coin_stats[t.coin]["loss"] += 1
                    coin_stats[t.coin]["short_loss_count"] += 1
                    coin_stats[t.coin]["short_loss"] += abs(t.pnl)
        
        today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
        today_trades = [t for t in trades if t.time.startswith(today)]
        today_open_long = len([t for t in today_trades if t.action == "buy"])
        today_close_long = len([t for t in today_trades if t.action == "sell"])
        today_open_short = len([t for t in today_trades if t.action == "sell_short"])
        today_close_short = len([t for t in today_trades if t.action == "buy_short"])
        today_volume = sum(t.amount for t in today_trades if t.action in ["buy", "sell_short"])
        
        return {
            "summary": {
                "total_trades": len(trades),
                "open_count": len(open_long_trades) + len(open_short_trades),
                "close_count": len(close_long_trades) + len(close_short_trades),
                "open_long": len(open_long_trades),
                "close_long": len(close_long_trades),
                "open_short": len(open_short_trades),
                "close_short": len(close_short_trades),
                "buy_count": len(open_long_trades) + len(close_short_trades),
                "sell_count": len(close_long_trades) + len(open_short_trades),
                "take_profit_sells": take_profit_sells,
                "stop_loss_sells": stop_loss_sells,
                "win_rate": round(win_rate, 2),
                "avg_profit": round(avg_profit, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_loss_ratio": round(profit_loss_ratio, 2),
                "total_profit": round(total_profit, 2),
                "total_loss": round(total_loss, 2),
                "net_profit": round(total_profit - total_loss, 2),
                "long_profit": round(long_profit, 2),
                "long_loss": round(long_loss, 2),
                "short_profit": round(short_profit, 2),
                "short_loss": round(short_loss, 2)
            },
            "coin_stats": coin_stats,
            "today": {
                "date": today,
                "trades": len(today_trades),
                "opens": today_open_long + today_open_short,
                "closes": today_close_long + today_close_short,
                "open_long": today_open_long,
                "close_long": today_close_long,
                "open_short": today_open_short,
                "close_short": today_close_short,
                "buys": today_open_long + today_close_short,
                "sells": today_close_long + today_open_short,
                "volume": round(today_volume, 2)
            },
            "last_updated": datetime.now(BEIJING_TZ).isoformat()
        }
    
    def generate_report(self) -> str:
        stats = self.calculate_stats()
        
        if not stats:
            return "暂无交易数据"
        
        summary = stats["summary"]
        coin_stats = stats["coin_stats"]
        today = stats["today"]
        
        report = "\n📊 交易统计报告\n"
        report += "==================\n\n"
        
        report += "📈 总体表现\n"
        report += f"  总交易次数: {summary['total_trades']}\n"
        report += f"  买入次数: {summary['buy_count']}\n"
        report += f"  卖出次数: {summary['sell_count']} (止盈{summary['take_profit_sells']}/止损{summary['stop_loss_sells']})\n"
        report += f"  胜率: {summary['win_rate']}%\n"
        report += f"  平均盈利: +{summary['avg_profit']}%\n"
        report += f"  平均亏损: -{summary['avg_loss']}%\n"
        report += f"  盈亏比: {summary['profit_loss_ratio']}\n"
        report += f"  总盈利: +{summary['total_profit']}%\n"
        report += f"  总亏损: -{summary['total_loss']}%\n"
        report += f"  净盈亏: {'+' if summary['net_profit'] > 0 else ''}{summary['net_profit']}%\n\n"
        
        report += "📅 今日交易\n"
        report += f"  日期: {today['date']}\n"
        report += f"  交易次数: {today['trades']}\n"
        report += f"  买入: {today['buys']} 次\n"
        report += f"  卖出: {today['sells']} 次\n"
        report += f"  买入金额: ${today['volume']}\n\n"
        
        report += "💰 币种表现\n"
        for coin, stat in coin_stats.items():
            coin_win_rate = (stat["profit"] / stat["sells"] * 100) if stat["sells"] else 0
            report += f"  {coin}: 买{stat['buys']}/卖{stat['sells']}, 胜{stat['profit']}/负{stat['loss']} ({coin_win_rate:.1f}%)\n"
        
        report += "\n==================\n"
        
        self._save_stats(stats)
        
        return report
    
    def _save_stats(self, stats: Dict):
        try:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")
    
    def get_recent_trades(self, limit: int = 20) -> List[TradeRecord]:
        return self.trade_log.trades[-limit:]
    
    def get_coin_trades(self, coin: str) -> List[TradeRecord]:
        return [t for t in self.trade_log.trades if t.coin == coin]
    
    def get_today_trades(self) -> List[TradeRecord]:
        """获取今日交易记录"""
        today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
        trades = [t for t in self.trade_log.trades if t.time.startswith(today)]
        
        # 如果没有找到交易记录，尝试从模拟交易数据加载
        if not trades:
            try:
                from app.services.simulation_manager import simulation_manager
                sim_trades = simulation_manager.get_recent_trades(limit=100)
                today_trades = []
                for t in sim_trades:
                    if t.get("timestamp", "").startswith(today):
                        today_trades.append(TradeRecord(
                            time=t.get("timestamp", ""),
                            coin=t.get("coin", ""),
                            action=t.get("action", ""),
                            price=t.get("price", 0.0),
                            amount=t.get("amount", 0.0),
                            reason=t.get("reason", ""),
                            pnl=t.get("pnl_percent", 0.0),
                            side=t.get("side", "long")
                        ))
                return today_trades
            except Exception as e:
                logger.debug(f"从模拟交易加载今日交易失败: {e}")
        
        return trades
    
    def get_today_trade_count(self, coin: Optional[str] = None) -> int:
        today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
        trades = [t for t in self.trade_log.trades if t.time.startswith(today)]
        
        if coin:
            trades = [t for t in trades if t.coin == coin]
        
        return len(trades)
    
    def reset_daily_stats(self):
        self.trade_log.daily_volume = 0.0
        self.trade_log.daily_trade_count = 0
        self._save_trade_log()


trade_stats = TradeStats(data_dir=get_data_dir())
