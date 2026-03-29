import aiohttp
import asyncio
import hashlib
import base64
import hmac
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from loguru import logger

BEIJING_TZ = timezone(timedelta(hours=8))


class FeishuNotifier:
    def __init__(self, app_id: str = "", app_secret: str = "", enabled: bool = False):
        self.app_id = app_id
        self.app_secret = app_secret
        self.enabled = enabled
        self.access_token: Optional[str] = None
        self.token_expire_time: Optional[float] = None
        self.webhook_url: str = ""
        self.chat_id: str = ""
        
        # 速率限制：记录最近发送时间
        self._last_send_time: float = 0
        self._min_interval: float = 0.5  # 最小发送间隔 0.5 秒
        self._send_lock = asyncio.Lock()  # 发送锁，防止并发
        
        # 重试配置
        self._max_retries: int = 3
        self._retry_delay: float = 1.0  # 重试延迟 1 秒
        self._timeout: float = 15.0  # 超时时间 15 秒

    def configure(self, app_id: str = "", app_secret: str = "", enabled: bool = True, webhook_url: str = "", chat_id: str = ""):
        self.app_id = app_id
        self.app_secret = app_secret
        self.enabled = enabled
        self.webhook_url = webhook_url
        self.chat_id = chat_id
        self.access_token = None
        self.token_expire_time = None
        logger.info(f"飞书通知配置: enabled={enabled}, app_id={'已配置' if app_id else '未配置'}, chat_id={chat_id if chat_id else '未配置'}")

    async def _get_access_token(self) -> Optional[str]:
        """获取飞书 Access Token"""
        if not self.app_id or not self.app_secret:
            return None

        # 检查 token 是否仍然有效（提前5分钟刷新）
        if self.access_token and self.token_expire_time and time.time() < self.token_expire_time - 300:
            return self.access_token

        try:
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            payload = {
                "app_id": self.app_id,
                "app_secret": self.app_secret
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("code") == 0:
                            self.access_token = result.get("tenant_access_token")
                            expire = result.get("expire", 7200)
                            self.token_expire_time = time.time() + expire
                            logger.info(f"飞书 Access Token 获取成功，有效期 {expire} 秒")
                            return self.access_token
                        else:
                            logger.warning(f"获取飞书 Access Token 失败: {result}")
                            return None
                    else:
                        logger.warning(f"获取飞书 Access Token HTTP 错误: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"获取飞书 Access Token 异常: {e}")
            return None

    async def send_message(self, title: str, content: str, msg_type: str = "interactive", chat_id: str = "") -> bool:
        logger.info(f"飞书通知检查: enabled={self.enabled}, app_id={bool(self.app_id)}, app_secret={bool(self.app_secret)}, webhook={bool(self.webhook_url)}")
        if not self.enabled:
            logger.info("飞书通知已禁用（enabled=False）")
            return False

        # 使用传入的 chat_id 或默认的 self.chat_id
        target_chat_id = chat_id if chat_id else self.chat_id

        # 优先使用 OAuth2.0 方式
        if self.app_id and self.app_secret:
            return await self._send_message_oauth(title, content, msg_type, target_chat_id)
        # 向后兼容：使用 Webhook 方式
        elif self.webhook_url:
            return await self._send_message_webhook(title, content, msg_type)
        else:
            logger.warning("飞书通知未配置：需要提供 App ID/App Secret 或 Webhook URL")
            return False

    async def _send_message_oauth(self, title: str, content: str, msg_type: str = "interactive", chat_id: str = "") -> bool:
        """使用 OAuth2.0 方式发送消息（带速率限制和重试）"""
        async with self._send_lock:  # 加锁防止并发
            # 速率限制：确保最小间隔
            elapsed = time.time() - self._last_send_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            
            access_token = await self._get_access_token()
            if not access_token:
                logger.warning("无法获取飞书 Access Token")
                return False

            timestamp = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")

            if msg_type == "trade":
                card_content = self._build_trade_card(title, content, timestamp)
            elif msg_type == "signal":
                card_content = self._build_signal_card(title, content, timestamp)
            elif msg_type == "alert":
                card_content = self._build_alert_card(title, content, timestamp)
            else:
                card_content = self._build_simple_card(title, content, timestamp)

            url = "https://open.feishu.cn/open-apis/message/v4/send"
            
            payload = {
                "msg_type": "interactive",
                "card": card_content
            }

            if chat_id:
                payload["chat_id"] = chat_id
            else:
                logger.warning("未指定 chat_id，消息可能无法送达")
                return False

            # 重试机制
            for attempt in range(self._max_retries):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            url,
                            json=payload,
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {access_token}"
                            },
                            timeout=aiohttp.ClientTimeout(total=self._timeout)
                        ) as response:
                            self._last_send_time = time.time()  # 记录发送时间
                            
                            if response.status == 200:
                                result = await response.json()
                                if result.get("code") == 0:
                                    logger.info(f"飞书通知发送成功: {title}")
                                    return True
                                else:
                                    logger.warning(f"飞书通知发送失败: {result}")
                                    # 速率限制错误，等待后重试
                                    if result.get("code") == 99991663:
                                        wait_time = 2.0 if attempt < self._max_retries - 1 else 0
                                        logger.warning(f"飞书 API 速率限制，等待 {wait_time} 秒后重试 (尝试 {attempt + 1}/{self._max_retries})")
                                        if wait_time > 0:
                                            await asyncio.sleep(wait_time)
                                            continue
                                    return False
                            else:
                                logger.warning(f"飞书通知HTTP错误: {response.status}")
                                if attempt < self._max_retries - 1:
                                    await asyncio.sleep(self._retry_delay)
                                    continue
                                return False

                except asyncio.TimeoutError:
                    logger.warning(f"飞书通知发送超时 (尝试 {attempt + 1}/{self._max_retries})")
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(self._retry_delay)
                        continue
                    return False
                except Exception as e:
                    logger.error(f"飞书通知发送异常: {e} (尝试 {attempt + 1}/{self._max_retries})")
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(self._retry_delay)
                        continue
                    return False
            
            return False

    async def _send_message_webhook(self, title: str, content: str, msg_type: str = "interactive") -> bool:
        """使用 Webhook 方式发送消息（向后兼容，带速率限制和重试）"""
        async with self._send_lock:  # 加锁防止并发
            # 速率限制：确保最小间隔
            elapsed = time.time() - self._last_send_time
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            
            if not self.webhook_url:
                return False

            timestamp = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")

            if msg_type == "trade":
                card_content = self._build_trade_card(title, content, timestamp)
            elif msg_type == "signal":
                card_content = self._build_signal_card(title, content, timestamp)
            elif msg_type == "alert":
                card_content = self._build_alert_card(title, content, timestamp)
            else:
                card_content = self._build_simple_card(title, content, timestamp)

            payload = {
                "msg_type": "interactive",
                "card": card_content
            }

            # 重试机制
            for attempt in range(self._max_retries):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            self.webhook_url,
                            json=payload,
                            headers={"Content-Type": "application/json"},
                            timeout=aiohttp.ClientTimeout(total=self._timeout)
                        ) as response:
                            self._last_send_time = time.time()  # 记录发送时间
                            
                            if response.status == 200:
                                result = await response.json()
                                if result.get("code") == 0 or result.get("StatusCode") == 0:
                                    logger.info(f"飞书通知发送成功: {title}")
                                    return True
                                else:
                                    logger.warning(f"飞书通知发送失败: {result}")
                                    if attempt < self._max_retries - 1:
                                        await asyncio.sleep(self._retry_delay)
                                        continue
                                    return False
                            else:
                                logger.warning(f"飞书通知HTTP错误: {response.status}")
                                if attempt < self._max_retries - 1:
                                    await asyncio.sleep(self._retry_delay)
                                    continue
                                return False

                except asyncio.TimeoutError:
                    logger.warning(f"飞书通知发送超时 (尝试 {attempt + 1}/{self._max_retries})")
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(self._retry_delay)
                        continue
                    return False
                except Exception as e:
                    logger.error(f"飞书通知发送异常: {e} (尝试 {attempt + 1}/{self._max_retries})")
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(self._retry_delay)
                        continue
                    return False
            
            return False

    def _build_trade_card(self, title: str, content: str, timestamp: str) -> Dict:
        return {
            "header": {
                "title": {"tag": "plain_text", "content": f"📊 {title}"},
                "template": "blue"
            },
            "elements": [
                {"tag": "markdown", "content": content},
                {"tag": "hr"},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": f"⏰ {timestamp}"}]}
            ]
        }

    def _build_signal_card(self, title: str, content: str, timestamp: str) -> Dict:
        return {
            "header": {
                "title": {"tag": "plain_text", "content": f"🎯 {title}"},
                "template": "purple"
            },
            "elements": [
                {"tag": "markdown", "content": content},
                {"tag": "hr"},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": f"⏰ {timestamp}"}]}
            ]
        }

    def _build_alert_card(self, title: str, content: str, timestamp: str) -> Dict:
        return {
            "header": {
                "title": {"tag": "plain_text", "content": f"🚨 {title}"},
                "template": "red"
            },
            "elements": [
                {"tag": "markdown", "content": content},
                {"tag": "hr"},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": f"⏰ {timestamp}"}]}
            ]
        }

    def _build_simple_card(self, title: str, content: str, timestamp: str) -> Dict:
        return {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "gray"
            },
            "elements": [
                {"tag": "markdown", "content": content},
                {"tag": "hr"},
                {"tag": "note", "elements": [{"tag": "plain_text", "content": f"⏰ {timestamp}"}]}
            ]
        }

    async def notify_trade(self, action: str, coin: str, price: float, amount: float, pnl_percent: float = 0, reason: str = "", is_swap: bool = False, leverage: float = 1.0, total_value: float = 0) -> bool:
        action_lower = action.lower()
        
        # 根据action确定交易类型
        if action_lower == "pyramid_buy":
            action_emoji = "📈"
            action_display = "加仓（多单）"
        elif action_lower == "pyramid_short":
            action_emoji = "📉"
            action_display = "加仓（空单）"
        elif action_lower == "cover_short":
            action_emoji = "🔄"
            action_display = "平空"
        elif action_lower == "buy":
            action_emoji = "🟢"
            action_display = "开多"
        elif action_lower == "sell":
            action_emoji = "🔵"
            action_display = "平多"
        elif action_lower == "sell_short":
            action_emoji = "🔴"
            action_display = "开空"
        elif action_lower == "reduce":
            action_emoji = "📉"
            action_display = "减仓"
        else:
            action_emoji = "⚪"
            action_display = action.upper()
        
        # amount 始终是数量
        quantity = amount
        
        # 计算成交金额：如果传入了 total_value 则使用，否则根据 amount * price 计算
        if total_value > 0:
            final_value = total_value
        else:
            final_value = amount * price
        
        # 构建内容
        content = f"""**交易类型:** {action_emoji} {action_display}
**币种:** {coin}
**价格:** ${price:.6f}
**数量:** {quantity:.4f}
**成交金额:** ${final_value:.2f} USDT
**杠杆:** {leverage}x {'(合约)' if is_swap else '(现货)'}
**原因:** {reason}"""
        if pnl_percent != 0:
            content += f"\n**盈亏:** {pnl_percent:.2f}%"

        return await self.send_message(f"{action_emoji} {coin} {action_display}", content, "trade")

        pnl_emoji = "💰" if pnl_percent > 0 else "💸" if pnl_percent < 0 else "➖"

        content = f"""**交易动作:** {action_emoji} **{action_display}**
**交易币种:** {coin}
**交易价格:** ${price:.4f}
**交易数量:** ${amount:.2f}"""

        if pnl_percent != 0:
            content += f"\n**盈亏:** {pnl_emoji} {pnl_percent:.2f}%"

        if reason:
            content += f"\n**原因:** {reason}"

        return await self.send_message(f"{action_display} {coin}", content, "trade")

    async def notify_signal(self, coin: str, trend_score: int, price: float, signal_type: str = "买入信号", resonance_score: float = 0) -> bool:
        content = f"""**币种:** {coin}
**信号类型:** 🎯 {signal_type}
**当前价格:** ${price:.4f}
**趋势评分:** {trend_score}/10
**共振评分:** {resonance_score:.1f}/10"""

        return await self.send_message(f"信号 {coin}", content, "signal")

    async def notify_stop_loss(self, coin: str, pnl_percent: float, price: float, reason: str = "") -> bool:
        content = f"""**触发类型:** 🚨 止损
**币种:** {coin}
**当前价格:** ${price:.4f}
**亏损幅度:** {pnl_percent:.2f}%

**原因:** {reason if reason else "触发止损线"}"""

        return await self.send_message(f"止损 {coin}", content, "alert")

    async def notify_take_profit(self, coin: str, pnl_percent: float, price: float, reason: str = "") -> bool:
        content = f"""**触发类型:** 🎉 止盈
**币种:** {coin}
**当前价格:** ${price:.4f}
**盈利幅度:** +{pnl_percent:.2f}%

**原因:** {reason if reason else "达到止盈目标"}"""

        return await self.send_message(f"止盈 {coin}", content, "trade")

    async def notify_pyramid_buy(self, coin: str, layer: int, price: float, amount: float, total_pnl: float) -> bool:
        content = f"""**动作:** 🏔️ 金字塔补仓
**币种:** {coin}
**补仓层数:** 第{layer}层
**补仓价格:** ${price:.4f}
**补仓金额:** ${amount:.2f}
**持仓总盈亏:** {total_pnl:.2f}%"""

        return await self.send_message(f"金字塔补仓 {coin}", content, "trade")

    async def notify_error(self, error_type: str, error_message: str, context: str = "") -> bool:
        content = f"""**错误类型:** 🚨 {error_type}
**错误信息:** {error_message}"""

        if context:
            content += f"\n**上下文:** {context}"

        return await self.send_message("交易系统错误", content, "alert")


feishu_notifier = FeishuNotifier()
