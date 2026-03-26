"""
回测引擎 v1.0
用于测试交易策略在历史数据上的表现
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import json
import os

from app.strategies.indicators import analyze_trend, TrendAnalysis
from app.services.trading_engine import TradingConfig


@dataclass
class BacktestPosition:
    coin: str
    entry_price: float
    amount: float
    usdt_value: float
    entry_time: str
    stop_loss_percent: float = -1.5
    take_profit_percent: float = 3.0
    highest_price: float = 0.0
    is_short: bool = False
    leverage: float = 1.0
    strategy: str = ""


@dataclass
class BacktestTrade:
    coin: str
    action: str
    price: float
    amount: float
    usdt_value: float
    pnl: float = 0.0
    pnl_percent: float = 0.0
    reason: str = ""
    timestamp: str = ""
    leverage: float = 1.0
    strategy: str = ""


@dataclass
class BacktestResult:
    start_time: str
    end_time: str
    initial_balance: float
    final_balance: float
    total_pnl: float
    total_pnl_percent: float
    total_trades: int
    win_trades: int
    loss_trades: int
    win_rate: float
    max_drawdown: float
    max_drawdown_percent: float
    sharpe_ratio: float
    profit_factor: float
    avg_profit: float
    avg_loss: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    trades: List[Dict] = field(default_factory=list)
    daily_pnl: List[Dict] = field(default_factory=list)
    position_history: List[Dict] = field(default_factory=list)


class BacktestEngine:
    def __init__(self, config: TradingConfig = None, initial_balance: float = 1000.0):
        self.config = config or TradingConfig()
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: Dict[str, BacktestPosition] = {}
        self.short_positions: Dict[str, BacktestPosition] = {}
        self.trades: List[BacktestTrade] = []
        self.daily_balances: List[Dict] = []
        self.max_balance = initial_balance
        self.max_drawdown = 0.0
        self.max_drawdown_percent = 0.0
        
    def reset(self):
        self.balance = self.initial_balance
        self.positions.clear()
        self.short_positions.clear()
        self.trades.clear()
        self.daily_balances.clear()
        self.max_balance = self.initial_balance
        self.max_drawdown = 0.0
        self.max_drawdown_percent = 0.0
    
    def _check_buy_conditions(self, trend_analysis: TrendAnalysis, change_24h: float, 
                               volume_ratio: float, btc_trend: int = 5, eth_trend: int = 5) -> Dict:
        bullish_score = trend_analysis.bullish_score
        bearish_score = trend_analysis.bearish_score
        trend_score = trend_analysis.score
        rsi = trend_analysis.indicators.get("rsi", 50.0)
        
        checks = []
        
        if bullish_score < self.config.long_min_bullish_score:
            checks.append(f"看涨评分{bullish_score}<{self.config.long_min_bullish_score}")
            return {"passed": False, "reason": f"看涨评分不足({bullish_score}/{self.config.long_min_bullish_score})", "checks": checks}
        
        if bullish_score <= bearish_score + self.config.long_bullish_gap:
            checks.append(f"看涨{bullish_score}未领先看跌{bearish_score}超过{self.config.long_bullish_gap}分")
            return {"passed": False, "reason": "看涨未明显领先看跌，市场分歧", "checks": checks}
        
        trend_ok = self.config.long_min_trend_score <= trend_score <= self.config.long_max_trend_score
        rsi_ok = self.config.long_rsi_min <= rsi <= self.config.long_rsi_max
        change_ok = self.config.long_min_pullback_percent <= change_24h <= self.config.long_max_pullback_percent
        volume_ok = volume_ratio >= self.config.long_min_volume_ratio
        
        checks.append(f"趋势评分{trend_score}{'✓' if trend_ok else '✗'}")
        checks.append(f"RSI{rsi:.1f}{'✓' if rsi_ok else '✗'}")
        checks.append(f"24h涨跌{change_24h:.2f}%{'✓' if change_ok else '✗'}")
        checks.append(f"成交量{volume_ratio:.2f}x{'✓' if volume_ok else '✗'}")
        
        passed = trend_ok and rsi_ok and change_ok and volume_ok
        
        return {
            "passed": passed,
            "reason": "短线策略通过" if passed else " | ".join(checks),
            "checks": checks,
            "strategy": "短线策略"
        }
    
    def _check_short_conditions(self, trend_analysis: TrendAnalysis, change_24h: float,
                                  volume_ratio: float, btc_trend: int = 5, eth_trend: int = 5) -> Dict:
        bullish_score = trend_analysis.bullish_score
        bearish_score = trend_analysis.bearish_score
        trend_score = trend_analysis.score
        rsi = trend_analysis.indicators.get("rsi", 50.0)
        
        checks = []
        
        is_bearish = bearish_score >= self.config.short_min_bearish_score
        is_not_bullish = bullish_score < self.config.long_min_bullish_score
        is_high_price = change_24h > self.config.short_min_pullback_percent
        is_rsi_overbought = self.config.short_rsi_min <= rsi <= self.config.short_rsi_max
        volume_sufficient = volume_ratio > self.config.short_min_volume_ratio
        
        checks.append(f"看跌评分{bearish_score}/10{'(达标)' if is_bearish else '(未达标)'}")
        checks.append(f"看涨评分{bullish_score}/10{'(偏空)' if is_not_bullish else '(偏多)'}")
        checks.append(f"高位({change_24h:.2f}%){'✓' if is_high_price else '✗'}")
        checks.append(f"RSI{rsi:.1f}{'(超买)' if is_rsi_overbought else '(未超买)'}")
        checks.append(f"成交量{volume_ratio:.2f}x{'(放量)' if volume_sufficient else '(未放量)'}")
        
        passed = False
        reason = ""
        
        if is_bearish and is_not_bullish:
            passed = True
            reason = f"做空信号: 看跌评分{bearish_score}/10, 看涨{bullish_score}/10(偏空)"
        elif is_high_price and is_rsi_overbought and volume_sufficient and is_not_bullish:
            passed = True
            reason = f"做空信号: 高位反转(涨幅{change_24h:.2f}%), 看涨{bullish_score}/10(偏空)"
        
        return {
            "passed": passed,
            "reason": reason if passed else " | ".join(checks),
            "checks": checks,
            "strategy": "短线做空"
        }
    
    def buy(self, coin: str, price: float, usdt_value: float, 
            reason: str = "", strategy: str = "", timestamp: str = "",
            leverage: float = 1.0) -> bool:
        if usdt_value > self.balance:
            return False
        
        if coin in self.positions:
            return False
        
        amount = usdt_value / price
        
        self.positions[coin] = BacktestPosition(
            coin=coin,
            entry_price=price,
            amount=amount,
            usdt_value=usdt_value,
            entry_time=timestamp,
            stop_loss_percent=self.config.long_stop_loss_percent,
            take_profit_percent=self.config.long_take_profit_percent,
            highest_price=price,
            is_short=False,
            leverage=leverage,
            strategy=strategy
        )
        
        self.balance -= usdt_value
        
        trade = BacktestTrade(
            coin=coin,
            action="buy",
            price=price,
            amount=amount,
            usdt_value=usdt_value,
            reason=reason,
            timestamp=timestamp,
            leverage=leverage,
            strategy=strategy
        )
        self.trades.append(trade)
        
        return True
    
    def sell(self, coin: str, price: float, reason: str = "", timestamp: str = "") -> bool:
        if coin not in self.positions:
            return False
        
        pos = self.positions[coin]
        leverage = pos.leverage
        
        pnl = (price - pos.entry_price) / pos.entry_price * pos.usdt_value * leverage
        pnl_percent = (price - pos.entry_price) / pos.entry_price * 100 * leverage
        
        self.balance += pos.usdt_value + pnl
        
        trade = BacktestTrade(
            coin=coin,
            action="sell",
            price=price,
            amount=pos.amount,
            usdt_value=pos.usdt_value,
            pnl=pnl,
            pnl_percent=pnl_percent,
            reason=reason,
            timestamp=timestamp,
            leverage=leverage,
            strategy=pos.strategy
        )
        self.trades.append(trade)
        
        del self.positions[coin]
        
        self._update_drawdown()
        
        return True
    
    def sell_short(self, coin: str, price: float, usdt_value: float,
                   reason: str = "", strategy: str = "", timestamp: str = "",
                   leverage: float = 1.0) -> bool:
        if usdt_value > self.balance:
            return False
        
        if coin in self.short_positions:
            return False
        
        amount = usdt_value / price
        
        self.short_positions[coin] = BacktestPosition(
            coin=coin,
            entry_price=price,
            amount=amount,
            usdt_value=usdt_value,
            entry_time=timestamp,
            stop_loss_percent=self.config.short_stop_loss_percent,
            take_profit_percent=-self.config.short_take_profit_percent,
            highest_price=price,
            is_short=True,
            leverage=leverage,
            strategy=strategy
        )
        
        self.balance -= usdt_value
        
        trade = BacktestTrade(
            coin=coin,
            action="sell_short",
            price=price,
            amount=amount,
            usdt_value=usdt_value,
            reason=reason,
            timestamp=timestamp,
            leverage=leverage,
            strategy=strategy
        )
        self.trades.append(trade)
        
        return True
    
    def buy_short(self, coin: str, price: float, reason: str = "", timestamp: str = "") -> bool:
        if coin not in self.short_positions:
            return False
        
        pos = self.short_positions[coin]
        leverage = pos.leverage
        
        pnl = (pos.entry_price - price) / pos.entry_price * pos.usdt_value * leverage
        pnl_percent = (pos.entry_price - price) / pos.entry_price * 100 * leverage
        
        self.balance += pos.usdt_value + pnl
        
        trade = BacktestTrade(
            coin=coin,
            action="buy_short",
            price=price,
            amount=pos.amount,
            usdt_value=pos.usdt_value,
            pnl=pnl,
            pnl_percent=pnl_percent,
            reason=reason,
            timestamp=timestamp,
            leverage=leverage,
            strategy=pos.strategy
        )
        self.trades.append(trade)
        
        del self.short_positions[coin]
        
        self._update_drawdown()
        
        return True
    
    def _update_drawdown(self):
        total_value = self.balance
        for pos in self.positions.values():
            total_value += pos.usdt_value
        for pos in self.short_positions.values():
            total_value += pos.usdt_value
        
        if total_value > self.max_balance:
            self.max_balance = total_value
        
        drawdown = self.max_balance - total_value
        drawdown_percent = drawdown / self.max_balance * 100 if self.max_balance > 0 else 0
        
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
            self.max_drawdown_percent = drawdown_percent
    
    def check_stop_loss_take_profit(self, coin: str, current_price: float, timestamp: str) -> List[Dict]:
        actions = []
        
        if coin in self.positions:
            pos = self.positions[coin]
            pnl_percent = (current_price - pos.entry_price) / pos.entry_price * 100 * pos.leverage
            
            if pnl_percent <= pos.stop_loss_percent:
                actions.append({
                    "action": "sell",
                    "reason": f"止损触发({pnl_percent:.2f}%<={pos.stop_loss_percent}%)"
                })
            elif pnl_percent >= pos.take_profit_percent:
                actions.append({
                    "action": "sell",
                    "reason": f"止盈触发({pnl_percent:.2f}%>={pos.take_profit_percent}%)"
                })
        
        if coin in self.short_positions:
            pos = self.short_positions[coin]
            pnl_percent = (pos.entry_price - current_price) / pos.entry_price * 100 * pos.leverage
            
            if pnl_percent <= pos.stop_loss_percent:
                actions.append({
                    "action": "buy_short",
                    "reason": f"止损触发({pnl_percent:.2f}%<={pos.stop_loss_percent}%)"
                })
            elif pnl_percent >= -pos.take_profit_percent:
                actions.append({
                    "action": "buy_short",
                    "reason": f"止盈触发({pnl_percent:.2f}%>={-pos.take_profit_percent}%)"
                })
        
        return actions
    
    def get_total_value(self, current_prices: Dict[str, float] = None) -> float:
        total = self.balance
        for coin, pos in self.positions.items():
            if current_prices and coin in current_prices:
                total += pos.amount * current_prices[coin]
            else:
                total += pos.usdt_value
        for coin, pos in self.short_positions.items():
            if current_prices and coin in current_prices:
                pnl = (pos.entry_price - current_prices[coin]) / pos.entry_price * pos.usdt_value * pos.leverage
                total += pos.usdt_value + pnl
            else:
                total += pos.usdt_value
        return total
    
    def calculate_results(self, end_prices: Dict[str, float] = None) -> BacktestResult:
        total_trades = len([t for t in self.trades if t.action in ["sell", "buy_short"]])
        win_trades = len([t for t in self.trades if t.pnl > 0])
        loss_trades = len([t for t in self.trades if t.pnl < 0])
        
        win_rate = win_trades / total_trades * 100 if total_trades > 0 else 0
        
        profits = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [abs(t.pnl) for t in self.trades if t.pnl < 0]
        
        avg_profit = sum(profits) / len(profits) if profits else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        profit_factor = sum(profits) / sum(losses) if losses and sum(losses) > 0 else float('inf') if profits else 0
        
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0
        
        for t in self.trades:
            if t.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            elif t.pnl < 0:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
        
        final_balance = self.get_total_value(end_prices)
        total_pnl = final_balance - self.initial_balance
        total_pnl_percent = total_pnl / self.initial_balance * 100 if self.initial_balance > 0 else 0
        
        daily_returns = []
        if len(self.daily_balances) > 1:
            for i in range(1, len(self.daily_balances)):
                prev = self.daily_balances[i-1]["balance"]
                curr = self.daily_balances[i]["balance"]
                if prev > 0:
                    daily_returns.append((curr - prev) / prev)
        
        sharpe_ratio = 0.0
        if daily_returns:
            avg_return = sum(daily_returns) / len(daily_returns)
            variance = sum((r - avg_return) ** 2 for r in daily_returns) / len(daily_returns)
            std_return = variance ** 0.5
            if std_return > 0:
                sharpe_ratio = (avg_return / std_return) * (252 ** 0.5)
        
        start_time = self.trades[0].timestamp if self.trades else ""
        end_time = self.trades[-1].timestamp if self.trades else ""
        
        return BacktestResult(
            start_time=start_time,
            end_time=end_time,
            initial_balance=self.initial_balance,
            final_balance=final_balance,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            total_trades=total_trades,
            win_trades=win_trades,
            loss_trades=loss_trades,
            win_rate=win_rate,
            max_drawdown=self.max_drawdown,
            max_drawdown_percent=self.max_drawdown_percent,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            trades=[{
                "coin": t.coin,
                "action": t.action,
                "price": t.price,
                "amount": t.amount,
                "usdt_value": t.usdt_value,
                "pnl": t.pnl,
                "pnl_percent": t.pnl_percent,
                "reason": t.reason,
                "timestamp": t.timestamp,
                "leverage": t.leverage,
                "strategy": t.strategy
            } for t in self.trades],
            daily_pnl=self.daily_balances,
            position_history=[]
        )


async def run_backtest(
    candles_data: Dict[str, List[List]],
    config: TradingConfig = None,
    initial_balance: float = 1000.0,
    position_size: float = 40.0,
    leverage: float = 1.0,
    enable_short: bool = False,
    btc_candles: List[List] = None,
    eth_candles: List[List] = None
) -> BacktestResult:
    """
    执行回测
    
    candles_data: {coin: [[ts, o, h, l, c, vol], ...]}
    """
    engine = BacktestEngine(config, initial_balance)
    
    coins = list(candles_data.keys())
    if not coins:
        return engine.calculate_results()
    
    first_coin = coins[0]
    total_candles = len(candles_data[first_coin])
    
    if total_candles < 50:
        return engine.calculate_results()
    
    btc_trend_score = 5
    eth_trend_score = 5
    
    for i in range(50, total_candles):
        current_timestamp = candles_data[first_coin][i][0]
        current_time = datetime.fromtimestamp(current_timestamp / 1000).isoformat()
        
        current_prices = {}
        for coin in coins:
            if i < len(candles_data[coin]):
                current_prices[coin] = float(candles_data[coin][i][4])
        
        for coin in list(engine.positions.keys()):
            if coin in current_prices:
                actions = engine.check_stop_loss_take_profit(coin, current_prices[coin], current_time)
                for action_info in actions:
                    if action_info["action"] == "sell":
                        engine.sell(coin, current_prices[coin], action_info["reason"], current_time)
        
        for coin in list(engine.short_positions.keys()):
            if coin in current_prices:
                actions = engine.check_stop_loss_take_profit(coin, current_prices[coin], current_time)
                for action_info in actions:
                    if action_info["action"] == "buy_short":
                        engine.buy_short(coin, current_prices[coin], action_info["reason"], current_time)
        
        if btc_candles and i < len(btc_candles):
            btc_analysis = await analyze_trend(btc_candles[max(0, i-50):i+1])
            btc_trend_score = btc_analysis.score
        
        if eth_candles and i < len(eth_candles):
            eth_analysis = await analyze_trend(eth_candles[max(0, i-50):i+1])
            eth_trend_score = eth_analysis.score
        
        for coin in coins:
            if i >= len(candles_data[coin]):
                continue
            
            candles = candles_data[coin][max(0, i-50):i+1]
            if len(candles) < 20:
                continue
            
            current_price = float(candles[-1][4])
            first_price = float(candles[0][4])
            change_24h = (current_price - first_price) / first_price * 100 if first_price > 0 else 0
            
            volume_sum = sum(float(c[5]) for c in candles[-24:]) if len(candles) >= 24 else sum(float(c[5]) for c in candles)
            volume_avg = volume_sum / min(24, len(candles))
            current_volume = float(candles[-1][5])
            volume_ratio = current_volume / volume_avg if volume_avg > 0 else 1.0
            
            trend_analysis = await analyze_trend(candles)
            
            if coin not in engine.positions:
                buy_check = engine._check_buy_conditions(
                    trend_analysis, change_24h, volume_ratio, btc_trend_score, eth_trend_score
                )
                
                if buy_check["passed"]:
                    if len(engine.positions) < config.long_max_positions if config else 3:
                        engine.buy(
                            coin=coin,
                            price=current_price,
                            usdt_value=position_size,
                            reason=buy_check["reason"],
                            strategy=buy_check["strategy"],
                            timestamp=current_time,
                            leverage=leverage
                        )
            
            if enable_short and coin not in engine.short_positions:
                short_check = engine._check_short_conditions(
                    trend_analysis, change_24h, volume_ratio, btc_trend_score, eth_trend_score
                )
                
                if short_check["passed"]:
                    if len(engine.short_positions) < (config.short_max_positions if config else 3):
                        engine.sell_short(
                            coin=coin,
                            price=current_price,
                            usdt_value=position_size,
                            reason=short_check["reason"],
                            strategy=short_check["strategy"],
                            timestamp=current_time,
                            leverage=leverage
                        )
        
        if i % 24 == 0:
            engine.daily_balances.append({
                "date": current_time[:10],
                "balance": engine.get_total_value(current_prices)
            })
    
    for coin in list(engine.positions.keys()):
        if coin in current_prices:
            engine.sell(coin, current_prices[coin], "回测结束平仓", current_time)
    
    for coin in list(engine.short_positions.keys()):
        if coin in current_prices:
            engine.buy_short(coin, current_prices[coin], "回测结束平仓", current_time)
    
    return engine.calculate_results(current_prices)
