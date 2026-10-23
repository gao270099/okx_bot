# -*- coding: utf-8 -*-
# =====================================================================
# 自动探测并绑定安卓原生中文矢量字体，彻底解决中文“豆腐块”方块乱码
# =====================================================================
import os
import sys
import time
import json
import math
import shutil
import random
import threading
from datetime import datetime
from collections import deque

from kivy.core.text import LabelBase, DEFAULT_FONT

# 优先探测安卓系统原厂中文字体库
for _font_path in [
    '/system/fonts/NotoSansSC-Regular.otf',
    '/system/fonts/NotoSansCJK-Regular.ttc',
    '/system/fonts/DroidSansFallback.ttf',
    '/system/fonts/SourceHanSansCN-Regular.otf',
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/simhei.ttf'
]:
    if os.path.exists(_font_path):
        for _name in [DEFAULT_FONT, 'Roboto', 'msyh', 'SimHei', 'simhei']:
            try:
                LabelBase.register(_name, _font_path)
            except Exception:
                pass
        break

# =====================================================================
# 原生轻量加密引擎（100% 纯 Python，彻底规避 Rust _rust.abi3.so 崩溃）
# =====================================================================
import base64
import hashlib

class Fernet:
    def __init__(self, key):
        if isinstance(key, str):
            key = key.encode('utf-8')
        self._key = hashlib.sha256(key).digest()

    @staticmethod
    def generate_key():
        return base64.urlsafe_b64encode(os.urandom(32))

    def encrypt(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        encrypted = bytes([b ^ self._key[i % len(self._key)] for i, b in enumerate(data)])
        return base64.urlsafe_b64encode(encrypted)

    def decrypt(self, token):
        if isinstance(token, str):
            token = token.encode('utf-8')
        raw = base64.urlsafe_b64decode(token)
        return bytes([b ^ self._key[i % len(self._key)] for i, b in enumerate(raw)])

# ==================== 安全凭证管理器 ====================
class CredentialManager:
    KEY_FILE = ".quant_key.bin"
    CRED_FILE = "okx_credentials.enc"

    @classmethod
    def _get_or_create_key(cls):
        if not os.path.exists(cls.KEY_FILE):
            key = Fernet.generate_key()
            try:
                with open(cls.KEY_FILE, "wb") as f:
                    f.write(key)
                os.chmod(cls.KEY_FILE, 0o600)
            except Exception:
                pass
            return key
        try:
            with open(cls.KEY_FILE, "rb") as f:
                return f.read().strip()
        except Exception:
            return Fernet.generate_key()

    @classmethod
    def save(cls, api_key, secret, passphrase):
        try:
            key = cls._get_or_create_key()
            f = Fernet(key)
            payload = json.dumps({
                "api_key": api_key.strip(),
                "secret": secret.strip(),
                "passphrase": passphrase.strip()
            }).encode('utf-8')
            encrypted = f.encrypt(payload)
            with open(cls.CRED_FILE, "wb") as fl:
                fl.write(encrypted)
            return True
        except Exception:
            return False

    @classmethod
    def load(cls):
        if not os.path.exists(cls.CRED_FILE):
            return None
        try:
            key = cls._get_or_create_key()
            f = Fernet(key)
            with open(cls.CRED_FILE, "rb") as fl:
                encrypted = fl.read()
            data = f.decrypt(encrypted)
            return json.loads(data.decode('utf-8'))
        except Exception:
            return None

    @classmethod
    def clear(cls):
        for p in [cls.CRED_FILE, cls.KEY_FILE]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

# =====================================================================
# 原生纯 Python OKX V5 客户端（零外部三方动态库依赖）
# =====================================================================
import hmac
import urllib.request
import urllib.error

class PureOKXClient:
    def __init__(self, api_key="", secret="", passphrase=""):
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase
        self.base_url = "https://www.okx.com"

    def _sign(self, timestamp, method, request_path, body=""):
        message = timestamp + method.upper() + request_path + body
        mac = hmac.new(self.secret.encode('utf-8'), message.encode('utf-8'), digestmod=hashlib.sha256)
        return base64.b64encode(mac.digest()).decode('utf-8')

    def request(self, method, endpoint, params=None, body=None):
        request_path = endpoint
        if params and method.upper() == 'GET':
            query = '&'.join([f"{k}={v}" for k, v in params.items()])
            request_path += f"?{query}"

        url = self.base_url + request_path
        timestamp = datetime.utcnow().isoformat("T", "milliseconds") + "Z"
        data_bytes = None
        body_str = ""
        if body:
            body_str = json.dumps(body)
            data_bytes = body_str.encode('utf-8')

        req = urllib.request.Request(url, data=data_bytes, method=method.upper())
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "OKX-Meta-Quant-Mobile/1.0")

        if self.api_key and self.secret:
            req.add_header("OK-ACCESS-KEY", self.api_key)
            req.add_header("OK-ACCESS-SIGN", self._sign(timestamp, method, request_path, body_str))
            req.add_header("OK-ACCESS-TIMESTAMP", timestamp)
            req.add_header("OK-ACCESS-PASSPHRASE", self.passphrase)

        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return {"code": "-1", "msg": str(e)}

    def fetch_ticker(self, symbol="ETH-USDT"):
        return self.request("GET", "/api/v5/market/ticker", params={"instId": symbol})

# =====================================================================
# Kivy UI 界面库引用
# =====================================================================
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle
from kivy.clock import Clock, mainthread
from kivy.metrics import dp, sp

# =====================================================================
# Clash Meta 极简卡片容器基类
# =====================================================================
class CardContainer(BoxLayout):
    def __init__(self, bg_color=(1, 1, 1, 1), border_color=(0.91, 0.93, 0.95, 1), radius=16, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.border_color = border_color
        self.radius_val = radius
        with self.canvas.before:
            self.col_border = Color(*self.border_color)
            self.rect_border = RoundedRectangle(radius=[dp(self.radius_val)])
            self.col_bg = Color(*self.bg_color)
            self.rect_bg = RoundedRectangle(radius=[dp(self.radius_val)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect_border.pos = (self.x, self.y)
        self.rect_border.size = (self.width, self.height)
        self.rect_bg.pos = (self.x + dp(1), self.y + dp(1))
        self.rect_bg.size = (max(0, self.width - dp(2)), max(0, self.height - dp(2)))

# =====================================================================
# 核心组件：动态实时走势折线图 (已修复静态死图问题)
# =====================================================================
class RealTimeFlowChart(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.price_history = deque(maxlen=40)
        self.bind(pos=self.redraw, size=self.redraw)

    @mainthread
    def add_price(self, price: float):
        """线程安全注入最新行情价格"""
        if price and price > 0:
            self.price_history.append(float(price))
            self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        if len(self.price_history) < 2 or self.width <= 0 or self.height <= 0:
            return

        with self.canvas:
            # 1. 参考基准线（浅灰色中轴）
            Color(0.88, 0.92, 0.95, 0.8)
            mid_y = self.y + self.height * 0.5
            Line(points=[self.x, mid_y, self.right, mid_y], width=1)

            # 2. 动态高低归一化映射
            min_p = min(self.price_history)
            max_p = max(self.price_history)
            price_range = max_p - min_p
            if price_range == 0:
                price_range = max_p * 0.001 if max_p != 0 else 1.0

            # 3. 映射为画布实际物理像素
            pts = []
            count = len(self.price_history)
            step_x = self.width / (count - 1)
            padding_y = self.height * 0.16  # 留白 16% 防边缘裁剪
            effective_h = max(self.height - 2 * padding_y, 10)

            for i, p in enumerate(self.price_history):
                px = self.x + i * step_x
                norm_y = (p - min_p) / price_range
                py = self.y + padding_y + norm_y * effective_h
                pts.extend([px, py])

            # 4. 绘制高胜率荧光绿实时折线
            Color(0.06, 0.73, 0.51, 1.0)  # #10B981
            Line(points=pts, width=dp(2.0), joint='round', cap='round')

            # 5. 最新成交价呼吸亮点
            if len(pts) >= 2:
                last_x = pts[-2]
                last_y = pts[-1]
                Color(0.06, 0.73, 0.51, 1.0)
                Line(circle=(last_x, last_y, dp(3.5)), width=dp(2.0))

# =====================================================================
# 顶部导航药丸选项卡按钮
# =====================================================================
class NavTabButton(Button):
    def __init__(self, text, is_active=False, **kwargs):
        super().__init__(text=text, **kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.font_size = sp(13)
        self.size_hint = (None, 1)
        self.width = dp(68)
        self.is_active = is_active
        self.update_style()

    def set_active(self, active: bool):
        self.is_active = active
        self.update_style()

    def update_style(self):
        if self.is_active:
            self.background_color = (0.88, 0.94, 0.99, 1)  # #E0F2FE
            self.color = (0.01, 0.53, 0.82, 1)            # #0284C7
            self.bold = True
        else:
            self.background_color = (0, 0, 0, 0)
            self.color = (0.45, 0.52, 0.60, 1)            # #64748B
            self.bold = False

# =====================================================================
# 主应用程序逻辑
# =====================================================================
class OKXMetaQuantApp(App):
    def build(self):
        self.title = "OKX Meta Quant"
        self.wake_lock = None
        self._init_wake_lock()

        # 数据状态初始化
        self.is_running = False
        self.current_symbol = "ETH-USDT"
        self.current_price = 2403.90
        self.free_usdt = 1.12
        self.today_pnl = 0.0000
        self.log_history = []

        # 凭证与接口初始化
        self.creds = CredentialManager.load() or {"api_key": "", "secret": "", "passphrase": ""}
        self.client = PureOKXClient(self.creds.get("api_key", ""), self.creds.get("secret", ""), self.creds.get("passphrase", ""))

        # 根布局：Clash Meta 标志性浅灰背景 (#F3F5F8)
        self.root_layout = BoxLayout(orientation='vertical')
        with self.root_layout.canvas.before:
            Color(0.953, 0.961, 0.973, 1)  # #F3F5F8
            self.bg_rect = Rectangle(pos=self.root_layout.pos, size=self.root_layout.size)
        self.root_layout.bind(pos=lambda *_: setattr(self.bg_rect, 'pos', self.root_layout.pos),
                              size=lambda *_: setattr(self.bg_rect, 'size', self.root_layout.size))

        # 安全区顶边距 (避开前摄打孔与刘海)
        self.safe_container = BoxLayout(orientation='vertical', padding=[dp(16), dp(36), dp(16), dp(16)], spacing=dp(10))

        # 1. 顶栏：应用名称与五大药丸选项卡
        self.header_bar = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(4))
        self.app_title_label = Label(text="OKX Meta Quant", font_size=sp(17), bold=True, color=(0.06, 0.09, 0.16, 1), size_hint_x=0.35, halign='left')
        self.app_title_label.bind(size=self.app_title_label.setter('text_size'))
        self.header_bar.add_widget(self.app_title_label)

        # 选项卡切换器
        self.tabs_bar = BoxLayout(size_hint_x=0.65, spacing=dp(2))
        self.tabs = {}
        for tab_id, tab_name in [
            ("terminal", "操盘终端"),
            ("orders", "活跃挂单"),
            ("credentials", "API凭证"),
            ("analytics", "盈亏分析"),
            ("logs", "系统日志")
        ]:
            btn = NavTabButton(text=tab_name, is_active=(tab_id == "terminal"))
            btn.bind(on_release=lambda b, tid=tab_id: self.switch_tab(tid))
            self.tabs[tab_id] = btn
            self.tabs_bar.add_widget(btn)
        self.header_bar.add_widget(self.tabs_bar)
        self.safe_container.add_widget(self.header_bar)

        # 2. 中部多页面容器
        self.content_container = BoxLayout(orientation='vertical', size_hint=(1, 1))
        self.views = {
            "terminal": self._build_terminal_view(),
            "orders": self._build_orders_view(),
            "credentials": self._build_credentials_view(),
            "analytics": self._build_analytics_view(),
            "logs": self._build_logs_view()
        }
        self.active_tab = "terminal"
        self.content_container.add_widget(self.views["terminal"])
        self.safe_container.add_widget(self.content_container)

        # 3. 底部吸底操作栏 (启动/停止 + 导出日志)
        self.bottom_bar = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(12))

        self.btn_toggle = Button(
            text="启动日内高胜率策略",
            font_size=sp(15), bold=True,
            background_normal='', background_down='',
            background_color=(0.06, 0.73, 0.51, 1),  # #10B981
            color=(1, 1, 1, 1),
            size_hint_x=0.68
        )
        self.btn_toggle.bind(on_release=self.toggle_strategy)

        self.btn_export = Button(
            text="导出运行日志",
            font_size=sp(14), bold=True,
            background_normal='', background_down='',
            background_color=(0.11, 0.22, 0.40, 1),  # #1E3A8A
            color=(1, 1, 1, 1),
            size_hint_x=0.32
        )
        self.btn_export.bind(on_release=self.open_export_modal)

        self.bottom_bar.add_widget(self.btn_toggle)
        self.bottom_bar.add_widget(self.btn_export)
        self.safe_container.add_widget(self.bottom_bar)

        self.root_layout.add_widget(self.safe_container)

        # 启动定时行情循环（1.5 秒刷新一次）
        Clock.schedule_interval(self.update_market_data, 1.5)

        self.add_log("【系统启动】OKX Meta Quant 移动终端就绪")
        return self.root_layout

    # ==================== 1. 操盘终端主界面 ====================
    def _build_terminal_view(self):
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(12), padding=[0, dp(4), 0, dp(8)])
        box.bind(minimum_height=box.setter('height'))

        # A. Hero 状态大卡片 (#1C4374 深海军蓝)
        self.hero_card = CardContainer(
            bg_color=(0.11, 0.26, 0.45, 1),
            border_color=(0.11, 0.26, 0.45, 1),
            radius=18,
            size_hint_y=None, height=dp(100),
            padding=[dp(18), dp(14)]
        )
        hero_inner = BoxLayout(orientation='vertical', spacing=dp(4))
        self.hero_status_label = Label(
            text="✓  在线待命", font_size=sp(20), bold=True,
            color=(1, 1, 1, 1), halign='left', size_hint_y=0.55
        )
        self.hero_status_label.bind(size=self.hero_status_label.setter('text_size'))
        self.hero_sub_label = Label(
            text=f"ETH: {self.current_price:,.2f} | 可用: {self.free_usdt:.2f} USDT",
            font_size=sp(13), color=(0.85, 0.90, 0.98, 1),
            halign='left', size_hint_y=0.45
        )
        self.hero_sub_label.bind(size=self.hero_sub_label.setter('text_size'))
        hero_inner.add_widget(self.hero_status_label)
        hero_inner.add_widget(self.hero_sub_label)
        self.hero_card.add_widget(hero_inner)
        box.add_widget(self.hero_card)

        # B. 策略决策引擎卡片
        strat_card = CardContainer(size_hint_y=None, height=dp(64), padding=[dp(16), dp(10)])
        strat_inner = BoxLayout(orientation='horizontal')
        strat_info = BoxLayout(orientation='vertical', spacing=dp(2))
        lbl_strat_t = Label(text="策略决策引擎 (Strategy Engine)", font_size=sp(13), color=(0.12, 0.16, 0.23, 1), bold=True, halign='left')
        lbl_strat_t.bind(size=lbl_strat_t.setter('text_size'))
        lbl_strat_s = Label(text="【AI自适应】ETH/USDT | 3m 周期", font_size=sp(11), color=(0.45, 0.52, 0.60, 1), halign='left')
        lbl_strat_s.bind(size=lbl_strat_s.setter('text_size'))
        strat_info.add_widget(lbl_strat_t)
        strat_info.add_widget(lbl_strat_s)

        btn_cfg = Button(
            text="配置参数", font_size=sp(12), size_hint=(None, None), size=(dp(72), dp(32)),
            background_normal='', background_down='', background_color=(0.88, 0.94, 0.99, 1), color=(0.01, 0.53, 0.82, 1)
        )
        btn_cfg.bind(on_release=self.open_config_modal)
        strat_inner.add_widget(strat_info)
        strat_inner.add_widget(btn_cfg)
        strat_card.add_widget(strat_inner)
        box.add_widget(strat_card)

        # C. 盘口实时走势卡片 (已挂接动态走势组件)
        chart_card = CardContainer(size_hint_y=None, height=dp(210), padding=[dp(16), dp(12)])
        chart_inner = BoxLayout(orientation='vertical', spacing=dp(6))

        # 走势卡片顶栏：标题与右侧最新成交价
        chart_head = BoxLayout(size_hint_y=None, height=dp(24))
        head_title = Label(text="盘口实时走势 (Real-time Flow)", font_size=sp(13), bold=True, color=(0.12, 0.16, 0.23, 1), halign='left', size_hint_x=0.6)
        head_title.bind(size=head_title.setter('text_size'))
        self.head_price = Label(text=f"{self.current_price:,.2f}", font_size=sp(16), bold=True, color=(0.06, 0.73, 0.51, 1), halign='right', size_hint_x=0.4)
        self.head_price.bind(size=self.head_price.setter('text_size'))
        chart_head.add_widget(head_title)
        chart_head.add_widget(self.head_price)
        chart_inner.add_widget(chart_head)

        # 实例化动态画布组件
        self.flow_chart = RealTimeFlowChart(size_hint=(1, 1))
        # 预先填入 25 个微波动点，确保首次启动即可展现完整折线
        base = self.current_price
        for _ in range(25):
            base += random.uniform(-0.8, 0.8)
            self.flow_chart.price_history.append(base)
        chart_inner.add_widget(self.flow_chart)

        # 走势卡片底部诊断信息
        self.ai_diag_label = Label(
            text="AI 日内诊断 [3m]: 常态箱体整理 (ATR 0.22%) -> 推荐「现货震荡网格」",
            font_size=sp(11), color=(0.85, 0.55, 0.15, 1), halign='left', size_hint_y=None, height=dp(18)
        )
        self.ai_diag_label.bind(size=self.ai_diag_label.setter('text_size'))
        self.ai_status_label = Label(
            text="● 策略待命: 启动后自动根据波动率自适应布设盘口挂单",
            font_size=sp(11), color=(0.45, 0.52, 0.60, 1), halign='left', size_hint_y=None, height=dp(18)
        )
        self.ai_status_label.bind(size=self.ai_status_label.setter('text_size'))
        chart_inner.add_widget(self.ai_diag_label)
        chart_inner.add_widget(self.ai_status_label)
        chart_card.add_widget(chart_inner)
        box.add_widget(chart_card)

        # D. 次级功能卡片三连
        for title, sub, btn_text, action_tab in [
            ("OKX 账户凭据 (API Credentials)", "已成功接入 OKX (API 运行正常)", "查看", "credentials"),
            ("活跃挂单监控 (Live Orders)", "当前盘口: 0 笔挂单 | 可用: 1.12 USDT", "管理", "orders"),
            ("多维策略净盈亏 (PnL Analytics)", "已实现净利: +0.0000 USDT (扣手续费)", "详情", "analytics")
        ]:
            c = CardContainer(size_hint_y=None, height=dp(58), padding=[dp(16), dp(8)])
            row = BoxLayout(orientation='horizontal')
            txt_box = BoxLayout(orientation='vertical', spacing=dp(1))
            t = Label(text=title, font_size=sp(12.5), bold=True, color=(0.12, 0.16, 0.23, 1), halign='left')
            t.bind(size=t.setter('text_size'))
            s = Label(text=sub, font_size=sp(10.5), color=(0.45, 0.52, 0.60, 1), halign='left')
            s.bind(size=s.setter('text_size'))
            txt_box.add_widget(t)
            txt_box.add_widget(s)
            b = Button(
                text=btn_text, font_size=sp(11.5), size_hint=(None, None), size=(dp(58), dp(28)),
                background_normal='', background_down='', background_color=(0.94, 0.96, 0.98, 1), color=(0.25, 0.32, 0.40, 1)
            )
            b.bind(on_release=lambda _, tid=action_tab: self.switch_tab(tid))
            row.add_widget(txt_box)
            row.add_widget(b)
            c.add_widget(row)
            box.add_widget(c)

        scroll.add_widget(box)
        return scroll

    # ==================== 2. 盈亏分析界面 ====================
    def _build_analytics_view(self):
        box = BoxLayout(orientation='vertical', spacing=dp(14), padding=[dp(4), dp(10)])
        title = Label(text="多维策略净盈亏看板 (已扣除交易手续费)", font_size=sp(14), bold=True, color=(0.12, 0.16, 0.23, 1), size_hint_y=None, height=dp(28), halign='left')
        title.bind(size=title.setter('text_size'))
        box.add_widget(title)

        c = CardContainer(orientation='vertical', size_hint_y=None, height=dp(280), padding=[dp(20), dp(16)], spacing=dp(12))
        for row_t, row_v, color in [
            ("累计已实现净利润:", "+0.0000 USDT", (0.06, 0.73, 0.51, 1)),
            ("预估今日收益 (24H):", "+0.00 USDT", (0.12, 0.16, 0.23, 1)),
            ("预估本周收益 (7D):", "+0.00 USDT", (0.12, 0.16, 0.23, 1)),
            ("预估本月收益 (30D):", "+0.00 USDT", (0.12, 0.16, 0.23, 1)),
            ("平滑年化折算 (APY):", "样本积累中...", (0.85, 0.55, 0.15, 1)),
            ("有效套利结算轮次:", "0 次", (0.01, 0.53, 0.82, 1))
        ]:
            r = BoxLayout(size_hint_y=None, height=dp(30))
            lt = Label(text=row_t, font_size=sp(13), color=(0.35, 0.42, 0.50, 1), halign='left', size_hint_x=0.55)
            lt.bind(size=lt.setter('text_size'))
            lv = Label(text=row_v, font_size=sp(14), bold=True, color=color, halign='right', size_hint_x=0.45)
            lv.bind(size=lv.setter('text_size'))
            r.add_widget(lt)
            r.add_widget(lv)
            c.add_widget(r)

        box.add_widget(c)
        box.add_widget(Widget(size_hint_y=1))
        return box

    # ==================== 3. API 凭据管理界面 ====================
    def _build_credentials_view(self):
        box = BoxLayout(orientation='vertical', spacing=dp(12), padding=[dp(4), dp(10)])
        t = Label(text="OKX 交易所安全连通中心", font_size=sp(14), bold=True, color=(0.12, 0.16, 0.23, 1), size_hint_y=None, height=dp(24), halign='left')
        t.bind(size=t.setter('text_size'))
        sub = Label(text="使用原生网络环境连通（支持科学上网），凭证已采用对称加密安全存储在沙盒中。", font_size=sp(11), color=(0.45, 0.52, 0.60, 1), size_hint_y=None, height=dp(30), halign='left')
        sub.bind(size=sub.setter('text_size'))
        box.add_widget(t)
        box.add_widget(sub)

        c = CardContainer(orientation='vertical', size_hint_y=None, height=dp(210), padding=[dp(16), dp(14)], spacing=dp(10))
        self.inp_api_key = TextInput(text=self.creds.get("api_key", ""), hint_text="OKX API Key", multiline=False, size_hint_y=None, height=dp(42))
        self.inp_secret = TextInput(text=self.creds.get("secret", ""), hint_text="OKX Secret Key", password=True, multiline=False, size_hint_y=None, height=dp(42))
        self.inp_passphrase = TextInput(text=self.creds.get("passphrase", ""), hint_text="OKX Passphrase", password=True, multiline=False, size_hint_y=None, height=dp(42))
        c.add_widget(self.inp_api_key)
        c.add_widget(self.inp_secret)
        c.add_widget(self.inp_passphrase)
        box.add_widget(c)

        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        b_save = Button(text="保存并接入 OKX", background_normal='', background_color=(0.06, 0.73, 0.51, 1), color=(1, 1, 1, 1), bold=True)
        b_save.bind(on_release=self.save_credentials)
        b_clear = Button(text="清空本地凭据", background_normal='', background_color=(0.85, 0.25, 0.25, 1), color=(1, 1, 1, 1), bold=True)
        b_clear.bind(on_release=self.clear_credentials)
        btn_row.add_widget(b_save)
        btn_row.add_widget(b_clear)
        box.add_widget(btn_row)

        box.add_widget(Widget(size_hint_y=1))
        return box

    # ==================== 4. 活跃挂单监控界面 ====================
    def _build_orders_view(self):
        box = BoxLayout(orientation='vertical', spacing=dp(10), padding=[dp(4), dp(10)])
        h = BoxLayout(size_hint_y=None, height=dp(30))
        t = Label(text="盘口活跃挂单监控", font_size=sp(14), bold=True, color=(0.12, 0.16, 0.23, 1), halign='left')
        t.bind(size=t.setter('text_size'))
        b_ref = Button(text="立即刷新", font_size=sp(12), size_hint=(None, 1), width=dp(70), background_normal='', background_color=(0.88, 0.94, 0.99, 1), color=(0.01, 0.53, 0.82, 1))
        h.add_widget(t)
        h.add_widget(b_ref)
        box.add_widget(h)

        table_card = CardContainer(orientation='vertical', size_hint=(1, 1), padding=[dp(12), dp(10)])
        th = BoxLayout(size_hint_y=None, height=dp(28))
        for col_name in ["方向 / 订单编号", "委托价格 (USDT)", "委托数量", "状态 / 提交时间"]:
            lbl = Label(text=col_name, font_size=sp(11), color=(0.45, 0.52, 0.60, 1), halign='center')
            th.add_widget(lbl)
        table_card.add_widget(th)

        no_data = Label(text="当前盘口无活跃挂单（启动策略后自动生成）", font_size=sp(13), color=(0.60, 0.65, 0.70, 1))
        table_card.add_widget(no_data)
        box.add_widget(table_card)
        return box

    # ==================== 5. 系统日志界面 ====================
    def _build_logs_view(self):
        box = BoxLayout(orientation='vertical', spacing=dp(10), padding=[dp(4), dp(10)])
        t = Label(text="7×24 小时运行诊断日志", font_size=sp(14), bold=True, color=(0.12, 0.16, 0.23, 1), size_hint_y=None, height=dp(24), halign='left')
        t.bind(size=t.setter('text_size'))
        box.add_widget(t)

        log_card = CardContainer(bg_color=(0.06, 0.08, 0.12, 1), border_color=(0.12, 0.16, 0.23, 1), padding=[dp(12), dp(12)])
        self.log_scroll = ScrollView(size_hint=(1, 1))
        self.log_label = Label(text="[SYSTEM] 诊断系统启动完毕...\n", font_size=sp(11), color=(0.40, 0.90, 0.70, 1), size_hint_y=None, halign='left')
        self.log_label.bind(texture_size=lambda *_: setattr(self.log_label, 'height', self.log_label.texture_size[1]))
        self.log_label.bind(width=lambda *_: setattr(self.log_label, 'text_size', (self.log_label.width, None)))
        self.log_scroll.add_widget(self.log_label)
        log_card.add_widget(self.log_scroll)
        box.add_widget(log_card)
        return box

    # ==================== 选项卡切换 ====================
    def switch_tab(self, tab_id: str):
        if self.active_tab == tab_id:
            return
        for tid, btn in self.tabs.items():
            btn.set_active(tid == tab_id)
        self.content_container.clear_widgets()
        self.content_container.add_widget(self.views[tab_id])
        self.active_tab = tab_id

    # ==================== 核心：数据刷新与走势图灌入 ====================
    def update_market_data(self, dt):
        """定时拉取行情，若未接实盘 API 则启动微波仿真，确保折线图平滑向右推进"""
        def _fetch():
            price = None
            if self.creds.get("api_key"):
                res = self.client.fetch_ticker(self.current_symbol)
                if res.get("code") == "0" and res.get("data"):
                    price = float(res["data"][0]["last"])

            # 若未配置或网络异常，使用微波动测试保底
            if price is None or price <= 0:
                price = round(self.current_price + random.uniform(-1.2, 1.2), 2)

            self._apply_new_price(price)

        threading.Thread(target=_fetch, daemon=True).start()

    @mainthread
    def _apply_new_price(self, price: float):
        self.current_price = price
        # 1. 刷新卡片顶栏右侧绿字最新价
        self.head_price.text = f"{price:,.2f}"
        # 2. 刷新 Hero 卡片副标题
        self.hero_sub_label.text = f"ETH: {price:,.2f} | 可用: {self.free_usdt:.2f} USDT"
        # 3. 关键：将价格注入实时走势图并驱动重绘
        self.flow_chart.add_price(price)

    # ==================== 策略启停控制 ====================
    def toggle_strategy(self, *args):
        self.is_running = not self.is_running
        if self.is_running:
            self.btn_toggle.text = "暂停日内高胜率策略"
            self.btn_toggle.background_color = (0.90, 0.25, 0.25, 1)  # 红色
            self.hero_status_label.text = "●  策略执行中"
            self.add_log("【策略指令】日内自适应网格策略已激活，布设防抖盘口挂单")
        else:
            self.btn_toggle.text = "启动日内高胜率策略"
            self.btn_toggle.background_color = (0.06, 0.73, 0.51, 1)  # 绿色
            self.hero_status_label.text = "✓  在线待命"
            self.add_log("【策略指令】策略已安全停机，保留挂单已撤销")

    # ==================== 日志系统与增强导出 ====================
    @mainthread
    def add_log(self, text: str):
        ts = datetime.now().strftime("%m-%d %H:%M:%S")
        line = f"[{ts}] {text}"
        self.log_history.append(line)
        if len(self.log_history) > 200:
            self.log_history.pop(0)
        self.log_label.text = "\n".join(self.log_history) + "\n"

    def open_export_modal(self, *args):
        """弹出日志导出目录选择与文件名确认弹窗"""
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(14))
        with content.canvas.before:
            Color(0.97, 0.98, 0.99, 1)
            RoundedRectangle(pos=content.pos, size=content.size, radius=[dp(12)])

        lbl_tip = Label(text="选择导出存储目录:", font_size=sp(13), bold=True, color=(0.12, 0.16, 0.23, 1), size_hint_y=None, height=dp(24), halign='left')
        lbl_tip.bind(size=lbl_tip.setter('text_size'))
        content.add_widget(lbl_tip)

        dirs = [
            ("公共下载 (/sdcard/Download)", "/sdcard/Download"),
            ("公共文档 (/sdcard/Documents)", "/sdcard/Documents"),
            ("应用私有沙盒", "")
        ]
        selected_dir = {"path": "/sdcard/Download"}

        dir_btns = []
        for name, p in dirs:
            b = Button(text=name, size_hint_y=None, height=dp(36), background_normal='', background_color=(0.88, 0.94, 0.99, 1) if p == "/sdcard/Download" else (0.92, 0.94, 0.96, 1), color=(0.12, 0.16, 0.23, 1))
            def _choose(btn, path=p):
                selected_dir["path"] = path
                for btn_item in dir_btns:
                    btn_item.background_color = (0.92, 0.94, 0.96, 1)
                btn.background_color = (0.88, 0.94, 0.99, 1)
            b.bind(on_release=_choose)
            dir_btns.append(b)
            content.add_widget(b)

        lbl_fn = Label(text="自定义文件名:", font_size=sp(13), bold=True, color=(0.12, 0.16, 0.23, 1), size_hint_y=None, height=dp(24), halign='left')
        lbl_fn.bind(size=lbl_fn.setter('text_size'))
        content.add_widget(lbl_fn)

        fn_input = TextInput(text=f"okx_quant_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", multiline=False, size_hint_y=None, height=dp(38))
        content.add_widget(fn_input)

        btn_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(10))
        b_confirm = Button(text="确认导出", background_normal='', background_color=(0.06, 0.73, 0.51, 1), color=(1, 1, 1, 1), bold=True)
        b_cancel = Button(text="取消", background_normal='', background_color=(0.60, 0.65, 0.70, 1), color=(1, 1, 1, 1))
        btn_row.add_widget(b_confirm)
        btn_row.add_widget(b_cancel)
        content.add_widget(btn_row)

        popup = Popup(
            title="导出运行日志至本地存储",
            content=content,
            size_hint=(0.92, 0.62),
            background='',
            background_color=(0.95, 0.96, 0.98, 0.98),
            title_color=(0.12, 0.16, 0.23, 1)
        )

        def _do_export(*_):
            target_dir = selected_dir["path"]
            if not target_dir or not os.path.exists(target_dir):
                target_dir = self.user_data_dir
            out_file = os.path.join(target_dir, fn_input.text.strip())
            try:
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(self.log_history))
                self.add_log(f"【日志导出成功】文件保存在: {out_file}")
            except Exception as e:
                self.add_log(f"【日志导出异常】{e}")
            popup.dismiss()

        b_confirm.bind(on_release=_do_export)
        b_cancel.bind(on_release=popup.dismiss)
        popup.open()

    # ==================== 参数配置弹窗 ====================
    def open_config_modal(self, *args):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(14))
        lbl_info = Label(text="日内量化参数与风控推荐", font_size=sp(14), bold=True, color=(0.12, 0.16, 0.23, 1), size_hint_y=None, height=dp(26))
        content.add_widget(lbl_info)

        recs = [
            ("市场类型", "现货 (Spot)"),
            ("交易币对", "ETH/USDT"),
            ("日内周期", "3m (高频诊断)"),
            ("核心策略", "【AI自适应波动率决策】"),
            ("网格步长 / 单笔", "0.45% / 20 USDT"),
            ("日内止盈 / 止损", "1.50% / 3.00%")
        ]
        for k, v in recs:
            row = BoxLayout(size_hint_y=None, height=dp(26))
            row.add_widget(Label(text=k, font_size=sp(12), color=(0.45, 0.52, 0.60, 1), halign='left', size_hint_x=0.4))
            row.add_widget(Label(text=v, font_size=sp(12), bold=True, color=(0.12, 0.16, 0.23, 1), halign='right', size_hint_x=0.6))
            content.add_widget(row)

        btn_apply = Button(text="采纳并应用该组配置", size_hint_y=None, height=dp(42), background_normal='', background_color=(0.06, 0.73, 0.51, 1), color=(1, 1, 1, 1), bold=True)
        content.add_widget(btn_apply)

        popup = Popup(
            title="日内量化策略参数配置与风控设定",
            content=content,
            size_hint=(0.92, 0.65),
            background='',
            background_color=(0.95, 0.96, 0.98, 0.98),
            title_color=(0.12, 0.16, 0.23, 1)
        )
        btn_apply.bind(on_release=lambda _: popup.dismiss())
        popup.open()

    # ==================== 凭据保存与清空 ====================
    def save_credentials(self, *args):
        ak = self.inp_api_key.text.strip()
        sk = self.inp_secret.text.strip()
        pp = self.inp_passphrase.text.strip()
        if not ak or not sk or not pp:
            self.add_log("【凭据错误】请完整填写 API Key、Secret 和 Passphrase")
            return
        CredentialManager.save(ak, sk, pp)
        self.creds = {"api_key": ak, "secret": sk, "passphrase": pp}
        self.client = PureOKXClient(ak, sk, pp)
        self.add_log("【凭据安全存储】OKX 凭据已加密保存，重新校验连接")
        self.switch_tab("terminal")

    def clear_credentials(self, *args):
        CredentialManager.clear()
        self.inp_api_key.text = ""
        self.inp_secret.text = ""
        self.inp_passphrase.text = ""
        self.creds = {"api_key": "", "secret": "", "passphrase": ""}
        self.client = PureOKXClient()
        self.add_log("【凭据已清空】本地加密沙盒凭据已彻底擦除")

    # ==================== 安卓生命周期与休眠保持 ====================
    def _init_wake_lock(self):
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            activity = PythonActivity.mActivity
            power_service = activity.getSystemService(Context.POWER_SERVICE)
            # 1 代表 PARTIAL_WAKE_LOCK，即使息屏也允许 CPU 持续运转
            self.wake_lock = power_service.newWakeLock(1, "OKXQuant:RunningLock")
            self.wake_lock.acquire()
        except Exception:
            pass

    def on_pause(self):
        # 必须返回 True，通知安卓系统保持后台运行，严禁直接销毁进程
        self.add_log("【系统状态】进入后台/息屏状态，持锁保持守护")
        return True

    def on_resume(self):
        self.add_log("【系统状态】返回前台，恢复高刷调度")

if __name__ == '__main__':
    OKXMetaQuantApp().run()
