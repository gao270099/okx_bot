"""
轻量级纯 Python 版 OKX CCXT 兼容引擎 (Android 原生优化版)
无需编译 Rust/C++ 动态库，100% 杜绝安卓端 dlopen 闪退
"""
import base64
import hashlib
import hmac
import json
import time
import requests

# 异常类兼容定义
class ExchangeError(Exception): pass
class NetworkError(Exception): pass
class AuthenticationError(Exception): pass
class InsufficientFunds(Exception): pass
class InvalidOrder(Exception): pass
class OrderNotFound(Exception): pass
class RateLimitExceeded(Exception): pass

class okx:
    def __init__(self, config=None):
        config = config or {}
        self.apiKey = config.get('apiKey', '')
        self.secret = config.get('secret', '')
        self.password = config.get('password', '')
        self.sandbox = config.get('sandbox', False) or config.get('testnet', False)
        self.base_url = 'https://www.okx.com'
        self.has = {
            'fetchTicker': True,
            'fetchTickers': True,
            'fetchOHLCV': True,
            'fetchBalance': True,
            'createOrder': True,
            'cancelOrder': True,
            'fetchOpenOrders': True,
            'fetchPositions': True
        }
        self.markets = {}

    def _to_inst(self, symbol):
        if not symbol:
            return ''
        return symbol.replace('/', '-').upper()

    def _from_inst(self, inst_id):
        if not inst_id:
            return ''
        parts = inst_id.split('-')
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return inst_id

    def _sign(self, timestamp, method, path, body=''):
        msg = f"{timestamp}{method.upper()}{path}{body}"
        mac = hmac.new(self.secret.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
        return base64.b64encode(mac.digest()).decode('utf-8')

    def _request(self, method, path, params=None, body=None):
        timestamp = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
        query = ''
        if params:
            query = '?' + '&'.join(f"{k}={v}" for k, v in params.items() if v is not None)
            path += query
        body_str = json.dumps(body) if body else ''
        headers = {
            'OK-ACCESS-KEY': self.apiKey,
            'OK-ACCESS-SIGN': self._sign(timestamp, method, path, body_str) if self.secret else '',
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.password,
            'Content-Type': 'application/json'
        }
        if self.sandbox:
            headers['x-simulated-trading'] = '1'
        url = self.base_url + path
        try:
            resp = requests.request(method, url, headers=headers, data=body_str if body else None, timeout=12)
            data = resp.json()
            if data.get('code') != '0':
                raise ExchangeError(f"OKX API Error [{data.get('code')}]: {data.get('msg')}")
            return data.get('data', [])
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error connecting to OKX: {str(e)}")

    def fetch_ticker(self, symbol):
        inst_id = self._to_inst(symbol)
        data = self._request('GET', '/api/v5/market/ticker', params={'instId': inst_id})
        if not data:
            raise ExchangeError(f"Ticker not found for {symbol}")
        t = data[0]
        return {
            'symbol': symbol,
            'last': float(t.get('last', 0.0)),
            'high': float(t.get('high24h', 0.0)),
            'low': float(t.get('low24h', 0.0)),
            'bid': float(t.get('bidPx', 0.0)),
            'ask': float(t.get('askPx', 0.0)),
            'volume': float(t.get('vol24h', 0.0)),
            'timestamp': int(t.get('ts', 0)),
            'info': t
        }

    def fetch_ohlcv(self, symbol, timeframe='1m', since=None, limit=100):
        inst_id = self._to_inst(symbol)
        params = {'instId': inst_id, 'bar': timeframe, 'limit': limit}
        if since:
            params['after'] = since
        data = self._request('GET', '/api/v5/market/candles', params=params)
        candles = []
        for row in reversed(data):
            candles.append([
                int(row[0]),
                float(row[1]),
                float(row[2]),
                float(row[3]),
                float(row[4]),
                float(row[5])
            ])
        return candles

    def fetch_balance(self):
        data = self._request('GET', '/api/v5/account/balance')
        balance = {'free': {}, 'used': {}, 'total': {}, 'info': data}
        if data and 'details' in data[0]:
            for d in data[0]['details']:
                ccy = d.get('ccy')
                avail = float(d.get('availBal', 0.0) or 0.0)
                frozen = float(d.get('frozenBal', 0.0) or 0.0)
                balance['free'][ccy] = avail
                balance['used'][ccy] = frozen
                balance['total'][ccy] = avail + frozen
        return balance

    def create_order(self, symbol, type, side, amount, price=None, params=None):
        params = params or {}
        inst_id = self._to_inst(symbol)
        body = {
            'instId': inst_id,
            'tdMode': params.get('tdMode', 'cash'),
            'side': side.lower(),
            'ordType': type.lower(),
            'sz': str(amount)
        }
        if price is not None:
            body['px'] = str(price)
        data = self._request('POST', '/api/v5/trade/order', body=body)
        if not data:
            raise ExchangeError("Order creation returned empty response")
        return {
            'id': data[0].get('ordId'),
            'symbol': symbol,
            'status': 'open',
            'info': data[0]
        }

    def cancel_order(self, id, symbol=None, params=None):
        params = params or {}
        inst_id = self._to_inst(symbol) if symbol else params.get('instId', '')
        body = {'ordId': str(id), 'instId': inst_id}
        data = self._request('POST', '/api/v5/trade/cancel-order', body=body)
        return {'id': id, 'status': 'canceled', 'info': data}

    def fetch_open_orders(self, symbol=None, since=None, limit=None, params=None):
        params = params or {}
        if symbol:
            params['instId'] = self._to_inst(symbol)
        data = self._request('GET', '/api/v5/trade/orders-pending', params=params)
        return [{'id': o.get('ordId'), 'symbol': self._from_inst(o.get('instId')), 'price': float(o.get('px', 0)), 'amount': float(o.get('sz', 0)), 'status': 'open', 'info': o} for o in data]

    def set_sandbox_mode(self, enabled):
        self.sandbox = enabled
