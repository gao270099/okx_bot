"""
轻量级纯 Python 版 OKX CCXT 兼容引擎 (Android 原生优化版 V2)
补齐 load_markets、market 等交易对初始化方法，支持实盘与模拟盘
"""
import base64
import hashlib
import hmac
import json
import time
import requests

# 常见异常类兼容定义
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
        self.markets = {}
        self.currencies = {}
        self.timeframes = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m',
            '30m': '30m', '1h': '1H', '2h': '2H', '4h': '4H',
            '1d': '1D', '1w': '1W', '1M': '1M'
        }
        self.has = {
            'fetchTicker': True,
            'fetchTickers': True,
            'fetchOHLCV': True,
            'fetchBalance': True,
            'createOrder': True,
            'cancelOrder': True,
            'fetchOpenOrders': True,
            'fetchPositions': True,
            'loadMarkets': True
        }

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
            resp = requests.request(method, url, headers=headers, data=body_str if body else None, timeout=15)
            data = resp.json()
            if data.get('code') != '0':
                raise ExchangeError(f"OKX API Error [{data.get('code')}]: {data.get('msg')}")
            return data.get('data', [])
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network error connecting to OKX: {str(e)}")

    def load_markets(self, reload=False, params=None):
        """加载市场交易对配置，解决 load_markets 属性缺失"""
        if self.markets and not reload:
            return self.markets
        try:
            instruments = self._request('GET', '/api/v5/public/instruments', params={'instType': 'SPOT'})
            for item in instruments:
                inst_id = item.get('instId', '')
                base = item.get('baseCcy', '')
                quote = item.get('quoteCcy', '')
                symbol = f"{base}/{quote}"
                self.markets[symbol] = {
                    'id': inst_id,
                    'symbol': symbol,
                    'base': base,
                    'quote': quote,
                    'active': item.get('state') == 'live',
                    'precision': {
                        'amount': float(item.get('lotSz', 0.0001) or 0.0001),
                        'price': float(item.get('tickSz', 0.01) or 0.01)
                    },
                    'limits': {
                        'amount': {'min': float(item.get('minSz', 0.0001) or 0.0001)},
                    },
                    'info': item
                }
        except Exception:
            # 弱网或离线兜底，内置主流交易对，保障逻辑顺畅执行
            for s in ['ETH/USDT', 'BTC/USDT', 'SOL/USDT', 'OKB/USDT', 'DOGE/USDT', 'XRP/USDT']:
                b, q = s.split('/')
                self.markets[s] = {
                    'id': self._to_inst(s),
                    'symbol': s,
                    'base': b,
                    'quote': q,
                    'active': True,
                    'precision': {'amount': 0.0001, 'price': 0.01},
                    'limits': {'amount': {'min': 0.0001}}
                }
        return self.markets

    def market(self, symbol):
        if not self.markets:
            self.load_markets()
        return self.markets.get(symbol, {'id': self._to_inst(symbol), 'symbol': symbol})

    def check_required_credentials(self, error=True):
        if not (self.apiKey and self.secret and self.password):
            if error:
                raise AuthenticationError("API credentials (apiKey, secret, password) are required")
            return False
        return True

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
        tf = self.timeframes.get(timeframe, timeframe)
        params = {'instId': inst_id, 'bar': tf, 'limit': limit}
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
        return
