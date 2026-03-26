import hmac
import base64
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
import httpx
import asyncio
from loguru import logger

from app.core.config import settings

_last_request_time: float = 0
_request_lock = asyncio.Lock()
MIN_REQUEST_INTERVAL = 0.1


class OKXClient:
    def __init__(self):
        self.api_key = settings.OKX_API_KEY
        self.secret_key = settings.OKX_SECRET_KEY
        self.passphrase = settings.OKX_PASSPHRASE
        self.base_url = settings.OKX_BASE_URL
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    def _get_timestamp(self) -> str:
        return datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
    
    def _sign(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        message = timestamp + method + request_path + body
        mac = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode('utf-8')
    
    def _get_headers(self, method: str, request_path: str, body: str = '') -> Dict[str, str]:
        timestamp = self._get_timestamp()
        signature = self._sign(timestamp, method, request_path, body)
        
        return {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json',
        }
    
    async def _wait_for_rate_limit(self):
        global _last_request_time
        async with _request_lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - _last_request_time
            if elapsed < MIN_REQUEST_INTERVAL:
                await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)
            _last_request_time = asyncio.get_event_loop().time()
    
    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, body: Optional[Dict] = None) -> Dict[str, Any]:
        await self._wait_for_rate_limit()
        
        if not self._client or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        
        request_path = endpoint
        query_string = ''
        
        if params:
            query_parts = []
            for key, value in params.items():
                query_parts.append(f"{key}={value}")
            query_string = '&'.join(query_parts)
            request_path = f"{endpoint}?{query_string}"
        
        body_str = ''
        if body:
            import json
            body_str = json.dumps(body, separators=(',', ':'))
        
        headers = self._get_headers(method, request_path, body_str)
        url = f"{self.base_url}{request_path}"
        
        max_retries = 3
        for retry in range(max_retries):
            try:
                logger.debug(f"Request: {method} {url}")
                
                if method == 'GET':
                    response = await self._client.get(url, headers=headers)
                elif method == 'POST':
                    response = await self._client.post(url, headers=headers, content=body_str)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                if response.status_code == 429:
                    wait_time = 1 * (retry + 1)
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {retry + 1}/{max_retries}")
                    await asyncio.sleep(wait_time)
                    headers = self._get_headers(method, request_path, body_str)
                    continue
                
                logger.debug(f"Response status: {response.status_code}")
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
                return {"code": str(e.response.status_code), "msg": e.response.text, "data": None}
            except httpx.TimeoutException as e:
                logger.error(f"Request timeout: {str(e)}")
                return {"code": "-2", "msg": f"请求超时: {str(e)}", "data": None}
            except httpx.ConnectError as e:
                logger.error(f"Connection error: {str(e)}")
                return {"code": "-3", "msg": f"连接错误: {str(e)}", "data": None}
            except httpx.RemoteProtocolError as e:
                if retry < max_retries - 1:
                    wait_time = 2 * (retry + 1)
                    logger.warning(f"Remote protocol error: {str(e)}, retrying in {wait_time}s ({retry + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Remote protocol error after {max_retries} retries: {str(e)}")
                return {"code": "-4", "msg": f"远程协议错误: {str(e)}", "data": None}
            except Exception as e:
                import traceback
                logger.error(f"Request error: {str(e)}\n{traceback.format_exc()}")
                return {"code": "-1", "msg": str(e), "data": None}
        
        return {"code": "429", "msg": "请求频率超限，请稍后重试", "data": None}
    
    async def get_balance(self) -> Dict[str, Any]:
        return await self._request('GET', '/api/v5/account/balance')
    
    async def get_ticker(self, inst_id: str) -> Dict[str, Any]:
        return await self._request('GET', '/api/v5/market/ticker', params={'instId': inst_id})
    
    async def get_tickers(self, inst_type: str = 'SPOT') -> Dict[str, Any]:
        return await self._request('GET', '/api/v5/market/tickers', params={'instType': inst_type})
    
    async def get_candles(self, inst_id: str, bar: str = '1H', limit: int = 100) -> Dict[str, Any]:
        return await self._request('GET', '/api/v5/market/candles', params={
            'instId': inst_id,
            'bar': bar,
            'limit': str(limit)
        })

    async def get_klines(self, inst_id: str, bar: str = '1H', limit: int = 100) -> list:
        """获取K线数据，返回简化格式列表"""
        result = await self.get_candles(inst_id, bar, limit)
        if result.get("code") == "0":
            data = result.get("data", [])
            # OKX返回的数据格式: [[ts, open, high, low, close, vol, volCcy], ...]
            # 转换为统一格式
            return data
        return []
    
    async def get_funding_rate(self, inst_id: str) -> Dict[str, Any]:
        return await self._request('GET', '/api/v5/public/funding-rate', params={'instId': inst_id})
    
    async def get_open_interest(self, inst_id: str) -> Dict[str, Any]:
        return await self._request('GET', '/api/v5/public/open-interest', params={'instId': inst_id})
    
    async def set_leverage(self, inst_id: str, leverage: int, td_mode: str = "cross", 
                           pos_side: str = None) -> Dict[str, Any]:
        """
        设置合约杠杆
        inst_id: 合约ID，如 BTC-USDT-SWAP
        leverage: 杠杆倍数
        td_mode: 交易模式 cross(全仓) 或 isolated(逐仓)
        pos_side: 持仓方向 long(多头) 或 short(空头)，逐仓模式需要指定
        """
        body = {
            'instId': inst_id,
            'lever': str(leverage),
            'mgnMode': td_mode
        }
        if pos_side and td_mode == 'isolated':
            body['posSide'] = pos_side
        
        return await self._request('POST', '/api/v5/account/set-leverage', body=body)
    
    async def place_order(self, inst_id: str, side: str = None, ord_type: str = "market",
                          sz: str = None, td_mode: str = "cash", px: Optional[str] = None,
                          order_type: str = None, size: str = None, price: Optional[str] = None,
                          pos_side: str = None) -> Dict[str, Any]:
        """
        下单
        side: buy(买入) 或 sell(卖出)
        td_mode: cash(现货) 或 cross(全仓合约) 或 isolated(逐仓合约)
        pos_side: 合约持仓方向 long(多头) 或 short(空头)，合约模式需要指定
        """
        if order_type:
            ord_type = order_type
        if size:
            sz = size
        if price:
            px = price
        
        body = {
            'instId': inst_id,
            'tdMode': td_mode,
            'side': side,
            'ordType': ord_type,
            'sz': sz
        }
        if px and ord_type == 'limit':
            body['px'] = px
        
        if td_mode in ['cross', 'isolated'] and pos_side:
            body['posSide'] = pos_side
        
        return await self._request('POST', '/api/v5/trade/order', body=body)
    
    async def place_spot_order(self, inst_id: str, side: str, size: str, 
                                ord_type: str = "market", price: Optional[str] = None) -> Dict[str, Any]:
        """现货下单"""
        return await self.place_order(
            inst_id=inst_id,
            side=side,
            sz=size,
            td_mode="cash",
            ord_type=ord_type,
            px=price
        )
    
    async def place_swap_order(self, inst_id: str, side: str, size: str, 
                                pos_side: str, leverage: int = None,
                                ord_type: str = "market", price: Optional[str] = None) -> Dict[str, Any]:
        """
        合约下单
        inst_id: 合约ID，如 BTC-USDT-SWAP
        side: buy 或 sell
        pos_side: long(开多/平空) 或 short(开空/平多)
        leverage: 杠杆倍数，可选
        """
        if leverage:
            await self.set_leverage(inst_id, leverage, td_mode="cross")
        
        return await self.place_order(
            inst_id=inst_id,
            side=side,
            sz=size,
            td_mode="cross",
            pos_side=pos_side,
            ord_type=ord_type,
            px=price
        )
    
    async def open_long(self, inst_id: str, size: str, leverage: int = None,
                        ord_type: str = "market", price: Optional[str] = None) -> Dict[str, Any]:
        """开多仓"""
        return await self.place_swap_order(
            inst_id=inst_id,
            side="buy",
            size=size,
            pos_side="long",
            leverage=leverage,
            ord_type=ord_type,
            price=price
        )
    
    async def close_long(self, inst_id: str, size: str, 
                         ord_type: str = "market", price: Optional[str] = None) -> Dict[str, Any]:
        """平多仓"""
        return await self.place_swap_order(
            inst_id=inst_id,
            side="sell",
            size=size,
            pos_side="long",
            ord_type=ord_type,
            price=price
        )
    
    async def open_short(self, inst_id: str, size: str, leverage: int = None,
                         ord_type: str = "market", price: Optional[str] = None) -> Dict[str, Any]:
        """开空仓"""
        return await self.place_swap_order(
            inst_id=inst_id,
            side="sell",
            size=size,
            pos_side="short",
            leverage=leverage,
            ord_type=ord_type,
            price=price
        )
    
    async def close_short(self, inst_id: str, size: str,
                          ord_type: str = "market", price: Optional[str] = None) -> Dict[str, Any]:
        """平空仓"""
        return await self.place_swap_order(
            inst_id=inst_id,
            side="buy",
            size=size,
            pos_side="short",
            ord_type=ord_type,
            price=price
        )
    
    async def cancel_order(self, inst_id: str, order_id: str) -> Dict[str, Any]:
        body = {
            'instId': inst_id,
            'ordId': order_id
        }
        return await self._request('POST', '/api/v5/trade/cancel-order', body=body)
    
    async def get_order(self, inst_id: str, order_id: str) -> Dict[str, Any]:
        return await self._request('GET', '/api/v5/trade/order', params={
            'instId': inst_id,
            'ordId': order_id
        })
    
    async def get_pending_orders(self, inst_id: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if inst_id:
            params['instId'] = inst_id
        return await self._request('GET', '/api/v5/trade/orders-pending', params=params)


okx_client = OKXClient()
