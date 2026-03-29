import aiohttp
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger
from pydantic import BaseModel

from app.core.config import settings
from app.services.trade_stats import TradeRecord


class StopLossSuggestion(BaseModel):
    enabled: Optional[bool] = None
    trend_8_plus: Optional[float] = None
    trend_6_7: Optional[float] = None
    trend_default: Optional[float] = None
    trend_0_2: Optional[float] = None
    trend_3_4: Optional[float] = None


class TakeProfitSuggestion(BaseModel):
    enabled: Optional[bool] = None
    trend_9_10: Optional[float] = None
    trend_7_8: Optional[float] = None
    trend_5_6: Optional[float] = None
    trend_default: Optional[float] = None
    trend_0_1: Optional[float] = None
    trend_2_3: Optional[float] = None
    trend_4: Optional[float] = None


class BandTradeSuggestion(BaseModel):
    enabled: Optional[bool] = None
    reduce_at: Optional[float] = None
    reduce_percent: Optional[float] = None
    second_reduce_at: Optional[float] = None
    second_reduce_percent: Optional[float] = None
    final_reduce_at: Optional[float] = None


class SmallProfitSuggestion(BaseModel):
    enabled: Optional[bool] = None
    threshold_percent: Optional[float] = None
    position_threshold: Optional[float] = None
    reduce_ratio: Optional[float] = None


class AISuggestion(BaseModel):
    analysis: str
    suggestions: Dict[str, Any]
    confidence: float
    reason: str
    stop_loss_suggestion: Optional[StopLossSuggestion] = None
    take_profit_suggestion: Optional[TakeProfitSuggestion] = None
    band_trade_suggestion: Optional[BandTradeSuggestion] = None
    small_profit_suggestion: Optional[SmallProfitSuggestion] = None


PARAM_RANGES = {
    "long": {
        "stop_loss": {
            "trend_8_plus": (2.0, 5.0),
            "trend_6_7": (1.5, 3.0),
            "trend_default": (1.0, 2.0)
        },
        "take_profit": {
            "trend_9_10": (12.0, 20.0),
            "trend_7_8": (8.0, 15.0),
            "trend_5_6": (5.0, 10.0),
            "trend_default": (4.0, 8.0)
        },
        "band_trade": {
            "reduce_at": (1.0, 3.0),
            "reduce_percent": (20.0, 40.0),
            "second_reduce_at": (2.0, 5.0),
            "second_reduce_percent": (30.0, 60.0),
            "final_reduce_at": (4.0, 10.0)
        },
        "small_profit": {
            "threshold_percent": (30.0, 70.0),
            "position_threshold": (10.0, 25.0),
            "reduce_ratio": (30.0, 70.0)
        },
        "basic": {
            "stop_loss": (-5.0, -2.0),
            "take_profit": (5.0, 15.0),
            "trade_size": (30.0, 100.0),
            "sentiment_threshold": (5, 9),
            "max_positions": (1, 7)
        }
    },
    "short": {
        "stop_loss": {
            "trend_0_2": (2.0, 5.0),
            "trend_3_4": (1.5, 3.0),
            "trend_default": (1.0, 2.0)
        },
        "take_profit": {
            "trend_0_1": (12.0, 20.0),
            "trend_2_3": (8.0, 15.0),
            "trend_4": (5.0, 10.0),
            "trend_default": (4.0, 8.0)
        },
        "band_trade": {
            "reduce_at": (1.0, 3.0),
            "reduce_percent": (20.0, 40.0),
            "second_reduce_at": (2.0, 5.0),
            "second_reduce_percent": (30.0, 60.0),
            "final_reduce_at": (4.0, 10.0)
        },
        "small_profit": {
            "threshold_percent": (30.0, 70.0),
            "position_threshold": (10.0, 25.0),
            "reduce_ratio": (30.0, 70.0)
        },
        "basic": {
            "stop_loss": (-5.0, -2.0),
            "take_profit": (3.0, 10.0),
            "trade_size": (30.0, 100.0),
            "sentiment_threshold": (3, 7),
            "max_positions": (1, 3)
        }
    }
}


class AIStrategyAdvisor:
    """AI策略顾问 - 调用LM Studio获取策略建议"""
    
    def __init__(self):
        self.base_url = settings.LM_STUDIO_URL
        self.model = settings.LM_STUDIO_MODEL
        self.timeout = 60
    
    async def analyze_performance(
        self,
        trades: List[TradeRecord],
        performance: Dict[str, Any],
        current_params: Dict[str, Any],
        side: str = "long"
    ) -> Optional[AISuggestion]:
        """分析交易数据，返回AI建议"""
        
        if not trades:
            logger.warning("没有交易数据，无法进行AI分析")
            return None
        
        try:
            side_trades = [t for t in trades if t.side == side and t.action in ["sell", "buy_short"]]
            
            if not side_trades:
                logger.warning(f"没有{side}方向的平仓交易数据")
                return None
            
            system_prompt = self._build_system_prompt(side)
            user_prompt = self._build_user_prompt(side_trades, performance, current_params, side)
            
            response = await self._call_lm_studio(system_prompt, user_prompt)
            
            if response:
                suggestion = self._parse_response(response, side)
                return suggestion
            
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            return None
    
    def _build_system_prompt(self, side: str) -> str:
        """构建系统Prompt"""
        side_name = "做多" if side == "long" else "做空"
        
        if side == "long":
            stop_loss_desc = """止损参数（趋势分数越高，止损越宽松）：
- trend_8_plus: 趋势≥8分止损，范围2-5%
- trend_6_7: 趋势6-7分止损，范围1.5-3%
- trend_default: 默认止损，范围1-2%"""
            
            take_profit_desc = """止盈参数（趋势分数越高，止盈越大）：
- trend_9_10: 趋势9-10分止盈，范围12-20%
- trend_7_8: 趋势7-8分止盈，范围8-15%
- trend_5_6: 趋势5-6分止盈，范围5-10%
- trend_default: 默认止盈，范围4-8%"""
        else:
            stop_loss_desc = """止损参数（趋势分数越低，止损越宽松）：
- trend_0_2: 趋势0-2分止损，范围2-5%
- trend_3_4: 趋势3-4分止损，范围1.5-3%
- trend_default: 默认止损，范围1-2%"""
            
            take_profit_desc = """止盈参数（趋势分数越低，止盈越大）：
- trend_0_1: 趋势0-1分止盈，范围12-20%
- trend_2_3: 趋势2-3分止盈，范围8-15%
- trend_4: 趋势4分止盈，范围5-10%
- trend_default: 默认止盈，范围4-8%"""
        
        return f"""你是专业的量化交易策略分析师。你的任务是分析{side_name}方向的交易数据，给出止盈止损参数调整建议。

你需要分析以下参数：

【智能止损参数】
{stop_loss_desc}

【动态止盈参数】
{take_profit_desc}

【分层减仓止盈参数】
- reduce_at: 第一档减仓点，范围1-3%
- reduce_percent: 第一档减仓比例，范围20-40%
- second_reduce_at: 第二档减仓点，范围2-5%
- second_reduce_percent: 第二档减仓比例，范围30-60%
- final_reduce_at: 最终止盈点，范围4-10%

【小盈减仓参数】
- threshold_percent: 触发阈值（止盈线%），范围30-70%
- position_threshold: 仓位阈值，范围10-25%
- reduce_ratio: 减仓比例，范围30-70%

【基础参数】
- stop_loss: 基础止损百分比，范围-5%到-2%
- take_profit: 基础止盈百分比，范围5-15%
- trade_size: 单笔交易金额，范围$30-$100
- sentiment_threshold: 情绪阈值，范围5-9
- max_positions: 最大持仓数，范围1-7

输出格式必须是JSON：
{{
  "analysis": "分析结论（中文，详细分析交易表现）",
  "suggestions": {{
    "stop_loss": -4.0,
    "take_profit": 8.0,
    "trade_size": 50.0,
    "sentiment_threshold": 7,
    "max_positions": 3
  }},
  "stop_loss_suggestion": {{
    "enabled": true,
    "trend_8_plus": 3.5,
    "trend_6_7": 2.5,
    "trend_default": 1.5
  }},
  "take_profit_suggestion": {{
    "enabled": true,
    "trend_9_10": 15.0,
    "trend_7_8": 10.0,
    "trend_5_6": 8.0,
    "trend_default": 6.0
  }},
  "band_trade_suggestion": {{
    "enabled": true,
    "reduce_at": 1.5,
    "reduce_percent": 30.0,
    "second_reduce_at": 3.0,
    "second_reduce_percent": 50.0,
    "final_reduce_at": 6.0
  }},
  "small_profit_suggestion": {{
    "enabled": true,
    "threshold_percent": 50.0,
    "position_threshold": 15.0,
    "reduce_ratio": 50.0
  }},
  "confidence": 0.8,
  "reason": "调整原因（中文，详细说明为什么这样调整）"
}}

注意：
- confidence 表示你对建议的信心程度，0-1之间
- 必须严格输出JSON格式，不要包含其他内容
- 只输出需要调整的参数，不需要调整的参数可以省略"""
    
    def _build_user_prompt(
        self,
        trades: List[TradeRecord],
        performance: Dict[str, Any],
        current_params: Dict[str, Any],
        side: str
    ) -> str:
        """构建用户Prompt"""
        side_name = "做多" if side == "long" else "做空"
        recent_trades = sorted(trades, key=lambda t: t.time, reverse=True)[:10]
        recent_pnl = [f"{t.pnl:.2f}%" for t in recent_trades if t.pnl != 0]
        
        sl_sug = current_params.get("stop_loss_suggestion", {})
        tp_sug = current_params.get("take_profit_suggestion", {})
        bt_sug = current_params.get("band_trade_suggestion", {})
        sp_sug = current_params.get("small_profit_suggestion", {})
        
        prompt = f"""分析以下{side_name}方向交易数据，给出参数调整建议：

【交易表现】
- 总交易数: {len(trades)}笔
- 胜率: {performance.get('win_rate', 0):.1f}%
- 平均盈利: +{performance.get('avg_profit', 0):.2f}%
- 平均亏损: {performance.get('avg_loss', 0):.2f}%
- 盈亏比: {performance.get('profit_loss_ratio', 0):.2f}
- 连续亏损: {performance.get('consecutive_losses', 0)}笔
- 最近10笔盈亏: {', '.join(recent_pnl) if recent_pnl else '无'}

【当前基础参数】
- 止损: {current_params.get('stop_loss', -5.0)}%
- 止盈: {current_params.get('take_profit', 10.0)}%
- 交易金额: {current_params.get('trade_size', 60)}$
- 情绪阈值: {current_params.get('sentiment_threshold', 7)}
- 最大持仓: {current_params.get('max_positions', 3)}

【当前智能止损参数】
- 启用: {sl_sug.get('enabled', True)}
- 趋势≥8分止损: {sl_sug.get('trend_8_plus', 3.0)}%
- 趋势6-7分止损: {sl_sug.get('trend_6_7', 2.0)}%
- 默认止损: {sl_sug.get('trend_default', 1.5)}%

【当前动态止盈参数】
- 启用: {tp_sug.get('enabled', True)}
- 趋势9-10分止盈: {tp_sug.get('trend_9_10', 15.0)}%
- 趋势7-8分止盈: {tp_sug.get('trend_7_8', 10.0)}%
- 趋势5-6分止盈: {tp_sug.get('trend_5_6', 8.0)}%
- 默认止盈: {tp_sug.get('trend_default', 6.0)}%

【当前分层减仓参数】
- 启用: {bt_sug.get('enabled', True)}
- 第一档减仓点: {bt_sug.get('reduce_at', 1.5)}%
- 第一档减仓比例: {bt_sug.get('reduce_percent', 30.0)}%
- 第二档减仓点: {bt_sug.get('second_reduce_at', 3.0)}%
- 第二档减仓比例: {bt_sug.get('second_reduce_percent', 50.0)}%
- 最终止盈点: {bt_sug.get('final_reduce_at', 6.0)}%

【当前小盈减仓参数】
- 启用: {sp_sug.get('enabled', True)}
- 触发阈值: {sp_sug.get('threshold_percent', 50.0)}%
- 仓位阈值: {sp_sug.get('position_threshold', 15.0)}%
- 减仓比例: {sp_sug.get('reduce_ratio', 50.0)}%

请根据交易表现给出参数调整建议。"""
        return prompt
    
    async def _call_lm_studio(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """调用LM Studio API"""
        url = f"{self.base_url}/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        return content
                    else:
                        error_text = await response.text()
                        logger.error(f"LM Studio API返回错误: {response.status} - {error_text}")
                        return None
        except aiohttp.ClientError as e:
            logger.error(f"LM Studio API调用失败: {e}")
            return None
        except Exception as e:
            logger.error(f"LM Studio API调用异常: {e}")
            return None
    
    def _parse_response(self, response: str, side: str) -> Optional[AISuggestion]:
        """解析AI响应"""
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                
                suggestions = data.get("suggestions", {})
                if not self._validate_basic_suggestions(suggestions, side):
                    logger.warning("基础建议参数超出范围，将进行裁剪")
                    suggestions = self._clamp_suggestions(suggestions, side, "basic")
                
                stop_loss_sug = None
                if "stop_loss_suggestion" in data:
                    sl_data = data["stop_loss_suggestion"]
                    if self._validate_advanced_suggestions(sl_data, side, "stop_loss"):
                        stop_loss_sug = StopLossSuggestion(**sl_data)
                    else:
                        stop_loss_sug = StopLossSuggestion(**self._clamp_suggestions(sl_data, side, "stop_loss"))
                
                take_profit_sug = None
                if "take_profit_suggestion" in data:
                    tp_data = data["take_profit_suggestion"]
                    if self._validate_advanced_suggestions(tp_data, side, "take_profit"):
                        take_profit_sug = TakeProfitSuggestion(**tp_data)
                    else:
                        take_profit_sug = TakeProfitSuggestion(**self._clamp_suggestions(tp_data, side, "take_profit"))
                
                band_trade_sug = None
                if "band_trade_suggestion" in data:
                    bt_data = data["band_trade_suggestion"]
                    if self._validate_advanced_suggestions(bt_data, side, "band_trade"):
                        band_trade_sug = BandTradeSuggestion(**bt_data)
                    else:
                        band_trade_sug = BandTradeSuggestion(**self._clamp_suggestions(bt_data, side, "band_trade"))
                
                small_profit_sug = None
                if "small_profit_suggestion" in data:
                    sp_data = data["small_profit_suggestion"]
                    if self._validate_advanced_suggestions(sp_data, side, "small_profit"):
                        small_profit_sug = SmallProfitSuggestion(**sp_data)
                    else:
                        small_profit_sug = SmallProfitSuggestion(**self._clamp_suggestions(sp_data, side, "small_profit"))
                
                return AISuggestion(
                    analysis=data.get("analysis", ""),
                    suggestions=suggestions,
                    confidence=min(1.0, max(0.0, data.get("confidence", 0.5))),
                    reason=data.get("reason", ""),
                    stop_loss_suggestion=stop_loss_sug,
                    take_profit_suggestion=take_profit_sug,
                    band_trade_suggestion=band_trade_sug,
                    small_profit_suggestion=small_profit_sug
                )
            else:
                logger.error("AI响应中未找到JSON")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"解析AI响应失败: {e}")
            return None
        except Exception as e:
            logger.error(f"处理AI响应失败: {e}")
            return None
    
    def _validate_basic_suggestions(self, suggestions: Dict[str, Any], side: str) -> bool:
        """验证基础建议参数是否在合理范围内"""
        ranges = PARAM_RANGES[side]["basic"]
        
        for key, (min_val, max_val) in ranges.items():
            if key in suggestions:
                value = suggestions[key]
                if isinstance(value, (int, float)):
                    if not (min_val <= value <= max_val):
                        logger.warning(f"{key}={value} 超出范围 [{min_val}, {max_val}]")
                        return False
        return True
    
    def _validate_advanced_suggestions(self, suggestions: Dict[str, Any], side: str, category: str) -> bool:
        """验证高级建议参数是否在合理范围内"""
        ranges = PARAM_RANGES[side].get(category, {})
        
        for key, (min_val, max_val) in ranges.items():
            if key in suggestions and suggestions[key] is not None:
                value = suggestions[key]
                if isinstance(value, (int, float)):
                    if not (min_val <= value <= max_val):
                        logger.warning(f"{category}.{key}={value} 超出范围 [{min_val}, {max_val}]")
                        return False
        return True
    
    def _clamp_suggestions(self, suggestions: Dict[str, Any], side: str, category: str) -> Dict[str, Any]:
        """将建议参数裁剪到合理范围内"""
        ranges = PARAM_RANGES[side].get(category, {})
        result = {}
        
        for key, value in suggestions.items():
            if key in ranges and value is not None and isinstance(value, (int, float)):
                min_val, max_val = ranges[key]
                result[key] = max(min_val, min(max_val, value))
            else:
                result[key] = value
        
        return result
    
    async def health_check(self) -> bool:
        """检查LM Studio连接状态"""
        try:
            url = f"{self.base_url}/v1/models"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"LM Studio连接检查失败: {e}")
            return False


ai_strategy_advisor = AIStrategyAdvisor()
