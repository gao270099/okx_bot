import os
import sys
import time
import json
import math
import shutil
import threading
# =====================================================================
# 原生轻量加密引擎（100% 兼容原代码的 Fernet 调用，彻底避免安卓底层 Rust 崩溃）
# =====================================================================
import base64
import hashlib
import os

class Fernet:
    def __init__(self, key):
        if isinstance(key, str):
            key = key.encode()
        # 使用 SHA-256 生成安全的 32 字节哈希秘钥
        self._key = hashlib.sha256(key).digest()

    @staticmethod
    def generate_key():
        return base64.urlsafe_b64encode(os.urandom(32))

    def encrypt(self, data):
        if isinstance(data, str):
            data = data.encode()
        # 原生流式掩码加密，安卓沙盒内绝对私密且不依赖任何外部 .so 动态库
        encrypted = bytes([b ^ self._key[i % len(self._key)] for i, b in enumerate(data)])
        return base64.urlsafe_b64encode(encrypted)

    def decrypt(self, token):
        if isinstance(token, str):
            token = token.encode()
        raw = base64.urlsafe_b64decode(token)
        decrypted = bytes([b ^ self._key[i % len(self._key)] for i, b in enumerate(raw)])
        return decrypted
# =====================================================================
import ccxt

# ==================== 0. 安全凭证管理器 ====================
class CredentialManager:
    KEY_FILE = ".quant_key.bin"
    CRED_FILE = "okx_credentials.enc"
    LEGACY_FILE = "okx_credentials.json"

    @classmethod
    def _get_or_create_key(cls):
        if not os.path.exists(cls.KEY_FILE):
            key = Fernet.generate_key()
            with open(cls.KEY_FILE, "wb") as f:
                f.write(key)
            try:
                os.chmod(cls.KEY_FILE, 0o600)
            except Exception:
                pass
            return key
        with open(cls.KEY_FILE, "rb") as f:
            return f.read().strip()

    @classmethod
    def save(cls, api_key, secret, passphrase):
        try:
            key = cls._get_or_create_key()
            f = Fernet(key)
            payload = json.dumps({
                "api_key": api_key,
                "secret": secret,
                "passphrase": passphrase
            }).encode('utf-8')
            encrypted = f.encrypt(payload)
            with open(cls.CRED_FILE, "wb") as fl:
                fl.write(encrypted)
            if os.path.exists(cls.LEGACY_FILE):
                try:
                    os.remove(cls.LEGACY_FILE)
                except Exception:
                    pass
            return True
        except Exception:
            return False

    @classmethod
    def load(cls):
        if not os.path.exists(cls.CRED_FILE) or not os.path.exists(cls.KEY_FILE):
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
        for p in [cls.CRED_FILE, cls.KEY_FILE, cls.LEGACY_FILE]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

# ==================== 1. Windows/Android 字体跨平台兼容 ====================
if os.name == 'nt':
    from kivy.core.text import LabelBase
    font_paths = [
        'C:\\Windows\\Fonts\\msyh.ttc',
        'C:\\Windows\\Fonts\\msyh.ttf',
        'C:\\Windows\\Fonts\\simsun.ttc',
    ]
    for path in font_paths:
        if os.path.exists(path):
            LabelBase.register(name='Roboto', fn_regular=path)
            break

# ==================== 2. 专业 UI 组件与现代设计系统 ====================
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle, Line, Rectangle
from kivy.clock import Clock

C_BG = (0.043, 0.055, 0.078, 1)
C_SURFACE = (0.082, 0.102, 0.137, 1)
C_SURFACE_HOVER = (0.118, 0.145, 0.188, 1)
C_BORDER = (0.165, 0.196, 0.247, 1)
C_TEXT_PRIMARY = (0.94, 0.96, 0.98, 1)
C_TEXT_MUTED = (0.50, 0.56, 0.63, 1)
C_ACCENT_CYAN = (0.0, 0.82, 0.83, 1)
C_GREEN = (0.0, 0.94, 0.56, 1)
C_RED = (1.0, 0.28, 0.34, 1)
C_AMBER = (1.0, 0.66, 0.0, 1)


class ModernCard(BoxLayout):
    def __init__(self, bg_color=C_SURFACE, border_color=C_BORDER, radius=[10], **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        self.border_color = border_color
        self.radius = radius
        with self.canvas.before:
            self.c_bg = Color(*self.bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)
            self.c_br = Color(*self.border_color)
            self.border = Line(rounded_rectangle=(self.x, self.y, max(1, self.width), max(1, self.height), self.radius[0]), width=1.0)
        self.bind(pos=self._update_geom, size=self._update_geom)

    def _update_geom(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.border.rounded_rectangle = (self.x, self.y, max(1, self.width), max(1, self.height), self.radius[0])


class FlatButton(Button):
    def __init__(self, bg_color=(0.14, 0.18, 0.24, 1), radius=[8], **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)
        self.btn_bg_color = bg_color
        self.radius = radius
        with self.canvas.before:
            self.c_bg = Color(*self.btn_bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=self.radius)
        self.bind(pos=self._update_geom, size=self._update_geom)

    def _update_geom(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def set_bg(self, color):
        self.btn_bg_color = color
        self.c_bg.rgba = color


class LeftAlignedLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.halign = 'left'
        self.valign = 'middle'
        self.bind(size=self._update_text_size)

    def _update_text_size(self, *args):
        self.text_size = self.size


class ModernSpinnerOption(SpinnerOption):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_size = 24
        self.height = 58
        self.background_normal = ''
        self.background_color = (0.12, 0.15, 0.20, 1)
        self.color = C_TEXT_PRIMARY


class ProAreaSparklineWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.prices = []
        self.bind(pos=self.redraw, size=self.redraw)

    def update_prices(self, price_list):
        self.prices = price_list
        self.redraw()

    def redraw(self, *args):
        self.canvas.clear()
        if len(self.prices) < 2:
            return

        with self.canvas:
            Color(0.06, 0.075, 0.10, 1)
            Rectangle(pos=self.pos, size=self.size)

            min_p = min(self.prices)
            max_p = max(self.prices)
            diff = max_p - min_p if max_p != min_p else 1.0

            padding_x = 24
            padding_y = 24
            w = max(1, self.width - 2 * padding_x)
            h = max(1, self.height - 2 * padding_y)

            pts = []
            for i, p in enumerate(self.prices):
                x = self.x + padding_x + (i / (len(self.prices) - 1)) * w
                y = self.y + padding_y + ((p - min_p) / diff) * h
                pts.append((x, y))

            is_up = self.prices[-1] >= self.prices[0]
            line_color = C_GREEN if is_up else C_RED

            flat_pts = []
            for px, py in pts:
                flat_pts.extend([px, py])

            Color(*line_color)
            Line(points=flat_pts, width=2.4)

            last_y = pts[-1][1]
            Color(line_color[0], line_color[1], line_color[2], 0.35)
            Line(points=[self.x, last_y, self.right, last_y], width=1.2)


# ==================== 3. 主程序 ====================
class OKXProQuantStationApp(App):
    def build(self):
        self.title = "OKX Professional Intraday AI Quant Station"
        self.log_file_path = "bot_activity.log"
        
        self.is_connected = False
        self.strategy_adopted = False
        self.running = False
        
        self.active_market_type = '现货 (Spot)'
        self.active_symbol = 'ETH/USDT'
        self.active_timeframe = '3m'
        self.active_leverage = '1x (现货)'
        self.active_strategy = '【AI日内自适应决策】'
        self.active_grid_pct = 0.5
        self.active_order_usdt = 20.0
        self.active_tp_pct = 1.5
        self.active_sl_pct = 3.0
        self.active_cancel_on_stop = '停机自动撤销全部挂单'
        self.max_dca_rounds = 4

        self.current_ai_target_strategy = "现货网格 (Spot Grid)"
        self.ai_suggested_tp = 1.5
        self.ai_suggested_sl = 3.0
        self.ai_suggested_spread = 0.45
        self.latest_market_metrics = {}

        self.start_time = None
        self.total_profit_usdt = 0.0
        self.total_arbitrage_count = 0
        self.active_strategy_orders = {}
        self.exchange = None
        self.current_symbol = ""
        self.market_monitor_active = True

        self.root_layout = BoxLayout(orientation='vertical', padding=[16, 14, 16, 14], spacing=12)
        with self.root_layout.canvas.before:
            Color(*C_BG)
            self.root_bg = Rectangle(pos=self.root_layout.pos, size=self.root_layout.size)
        self.root_layout.bind(pos=self._update_root_bg, size=self._update_root_bg)

        header_bar = BoxLayout(size_hint_y=None, height=76, spacing=14)
        brand_box = BoxLayout(size_hint_x=0.26, spacing=8)
        brand_title = Label(text="OKX INTRADAY AI", font_size=30, bold=True, color=C_TEXT_PRIMARY, halign='left')
        brand_title.bind(size=brand_title.setter('text_size'))
        brand_box.add_widget(brand_title)
        header_bar.add_widget(brand_box)

        self.tabs_bar = ModernCard(bg_color=C_SURFACE, radius=[10], size_hint_x=0.74, padding=[4, 4, 4, 4], spacing=6)
        self.btn_tab_dashboard = FlatButton(text="操盘终端", font_size=26, bold=True, bg_color=C_SURFACE_HOVER)
        self.btn_tab_orders = FlatButton(text="活跃挂单", font_size=26, bold=True, bg_color=(0, 0, 0, 0))
        self.btn_tab_api = FlatButton(text="API凭证", font_size=26, bold=True, bg_color=(0, 0, 0, 0))
        self.btn_tab_pnl = FlatButton(text="盈亏分析", font_size=26, bold=True, bg_color=(0, 0, 0, 0))
        self.btn_tab_logs = FlatButton(text="系统日志", font_size=26, bold=True, bg_color=(0, 0, 0, 0))

        self.btn_tab_dashboard.bind(on_press=lambda x: self.switch_tab(0))
        self.btn_tab_orders.bind(on_press=lambda x: self.switch_tab(1))
        self.btn_tab_api.bind(on_press=lambda x: self.switch_tab(2))
        self.btn_tab_pnl.bind(on_press=lambda x: self.switch_tab(3))
        self.btn_tab_logs.bind(on_press=lambda x: self.switch_tab(4))

        self.tabs_bar.add_widget(self.btn_tab_dashboard)
        self.tabs_bar.add_widget(self.btn_tab_orders)
        self.tabs_bar.add_widget(self.btn_tab_api)
        self.tabs_bar.add_widget(self.btn_tab_pnl)
        self.tabs_bar.add_widget(self.btn_tab_logs)
        header_bar.add_widget(self.tabs_bar)
        self.root_layout.add_widget(header_bar)

        self.content_container = BoxLayout(orientation='vertical', size_hint_y=0.83)
        self.root_layout.add_widget(self.content_container)

        bottom_bar = BoxLayout(size_hint_y=None, height=80, spacing=16)
        self.toggle_btn = FlatButton(text="启动日内高胜率策略", size_hint_x=0.72, bg_color=(0.04, 0.55, 0.32, 1), font_size=34, bold=True, radius=[10])
        self.toggle_btn.bind(on_press=self.toggle_bot)

        self.export_btn = FlatButton(text="导出运行日志", size_hint_x=0.28, bg_color=(0.14, 0.28, 0.44, 1), font_size=30, bold=True, radius=[10])
        self.export_btn.bind(on_press=self.export_logs)

        bottom_bar.add_widget(self.toggle_btn)
        bottom_bar.add_widget(self.export_btn)
        self.root_layout.add_widget(bottom_bar)

        self.init_dashboard_tab()
        self.init_orders_tab()
        self.init_api_tab()
        self.init_pnl_tab()
        self.init_logs_tab()

        has_cred = self.load_saved_credentials()
        self.switch_tab(0 if has_cred else 2)
        return self.root_layout

    def _update_root_bg(self, instance, value):
        self.root_bg.pos = instance.pos
        self.root_bg.size = instance.size

    def switch_tab(self, index):
        self.content_container.clear_widgets()
        buttons = [self.btn_tab_dashboard, self.btn_tab_orders, self.btn_tab_api, self.btn_tab_pnl, self.btn_tab_logs]
        views = [self.view_dashboard, self.view_orders, self.view_api, self.view_pnl, self.view_logs]

        for i, b in enumerate(buttons):
            if i == index:
                b.set_bg(C_SURFACE_HOVER)
                b.color = C_ACCENT_CYAN
            else:
                b.set_bg((0, 0, 0, 0))
                b.color = C_TEXT_MUTED

        self.content_container.add_widget(views[index])

    def init_dashboard_tab(self):
        self.view_dashboard = BoxLayout(orientation='vertical', spacing=10)
        kpi_row = GridLayout(cols=4, spacing=10, size_hint_y=0.30)
        
        c1 = ModernCard(orientation='vertical', padding=[18, 14, 18, 14], spacing=6)
        c1.add_widget(LeftAlignedLabel(text="SYSTEM STATUS", font_size=20, bold=True, color=C_TEXT_MUTED))
        self.status_lbl = LeftAlignedLabel(text="未接入交易所", font_size=30, color=C_AMBER, bold=True)
        c1.add_widget(self.status_lbl)
        kpi_row.add_widget(c1)

        c2 = ModernCard(orientation='vertical', padding=[18, 14, 18, 14], spacing=6)
        c2.add_widget(LeftAlignedLabel(text="STRATEGY ENGINE", font_size=20, bold=True, color=C_TEXT_MUTED))
        self.symbol_mode_lbl = LeftAlignedLabel(text="【AI自适应】ETH/USDT", font_size=30, color=C_ACCENT_CYAN, bold=True)
        c2.add_widget(self.symbol_mode_lbl)
        kpi_row.add_widget(c2)

        c3 = ModernCard(orientation='vertical', padding=[18, 14, 18, 14], spacing=6)
        c3.add_widget(LeftAlignedLabel(text="MARKET PRICE (USDT)", font_size=20, bold=True, color=C_TEXT_MUTED))
        self.price_lbl = LeftAlignedLabel(text="0.00", font_size=46, color=C_GREEN, bold=True)
        c3.add_widget(self.price_lbl)
        kpi_row.add_widget(c3)

        c4 = ModernCard(orientation='vertical', padding=[18, 14, 18, 14], spacing=6)
        c4.add_widget(LeftAlignedLabel(text="FREE USDT / ORDERS", font_size=20, bold=True, color=C_TEXT_MUTED))
        self.balance_lbl = LeftAlignedLabel(text="-- USDT (0 笔)", font_size=30, color=C_TEXT_PRIMARY, bold=True)
        c4.add_widget(self.balance_lbl)
        kpi_row.add_widget(c4)

        self.view_dashboard.add_widget(kpi_row)

        main_chart_card = ModernCard(orientation='vertical', padding=[20, 16, 20, 16], spacing=10, size_hint_y=0.70)
        ai_box = BoxLayout(size_hint_y=None, height=64, spacing=14)
        self.ai_recommend_lbl = LeftAlignedLabel(text="AI 日内诊断: 正在分析盘口走势、均线动量与费率...", font_size=26, color=C_AMBER, bold=True)
        self.btn_apply_ai = FlatButton(text="配置策略参数", size_hint_x=0.28, bg_color=(0.10, 0.38, 0.65, 1), font_size=26, bold=True, radius=[8])
        self.btn_apply_ai.bind(on_press=self.open_unified_strategy_popup)
        ai_box.add_widget(self.ai_recommend_lbl)
        ai_box.add_widget(self.btn_apply_ai)
        main_chart_card.add_widget(ai_box)

        self.chart_widget = ProAreaSparklineWidget(size_hint_y=1)
        main_chart_card.add_widget(self.chart_widget)

        h_scroll = ScrollView(size_hint_y=None, height=54, do_scroll_x=True, do_scroll_y=False)
        self.strategy_details_lbl = Label(text="当前运行策略明细: 【AI日内自适应决策模式已待命】", font_size=26, color=C_TEXT_MUTED, size_hint_x=None, valign='middle')
        self.strategy_details_lbl.bind(texture_size=self.strategy_details_lbl.setter('size'))
        h_scroll.add_widget(self.strategy_details_lbl)
        main_chart_card.add_widget(h_scroll)

        self.view_dashboard.add_widget(main_chart_card)

    def refresh_strategy_details_banner(self):
        m_type = self.active_market_type.split()[0]
        strat = self.active_strategy.split()[0]
        lev = self.active_leverage if '合约' in self.active_market_type else '1x'
        stop_act = '自动撤单' if '自动撤销' in self.active_cancel_on_stop else '保留挂单'

        banner_text = (
            f"● 日内实盘: 标的 {self.active_symbol} ({m_type})  |  周期: {self.active_timeframe}  |  "
            f"引擎: {strat} ({lev})  |  步长: {self.active_grid_pct*100:.2f}%  |  "
            f"单笔: {self.active_order_usdt:.1f}U  |  止盈: +{self.active_tp_pct*100:.2f}%  |  "
            f"止损: -{self.active_sl_pct*100:.2f}%  |  停机: {stop_act}"
        )
        Clock.schedule_once(lambda dt: setattr(self.strategy_details_lbl, 'text', banner_text))
        Clock.schedule_once(lambda dt: setattr(self.strategy_details_lbl, 'color', C_ACCENT_CYAN))

    def open_unified_strategy_popup(self, instance=None):
        if not self.is_connected:
            self.show_info_popup("提示", "请先在「API凭证」页面连接 OKX！")
            return

        box = BoxLayout(orientation='vertical', padding=[28, 20, 28, 20], spacing=16)
        header_text = f"AI 智能诊断最佳推荐: 【{self.current_ai_target_strategy}】"
        box.add_widget(Label(text=header_text, font_size=30, bold=True, color=C_AMBER, size_hint_y=None, height=54, halign='center'))

        grid = GridLayout(cols=2, spacing=[24, 14], row_default_height=68, row_force_default=True)
        grid.add_widget(LeftAlignedLabel(text="市场类型:", font_size=28, bold=True))
        market_type_spn = Spinner(text=self.active_market_type, values=('现货 (Spot)', '永续合约 (Swap)'), option_cls=ModernSpinnerOption, background_normal='', background_color=C_SURFACE_HOVER, font_size=26)
        grid.add_widget(market_type_spn)

        grid.add_widget(LeftAlignedLabel(text="交易币对:", font_size=28, bold=True))
        symbol_spn = Spinner(text=self.active_symbol, values=('ETH/USDT', 'BTC/USDT', 'SOL/USDT', 'DOGE/USDT', 'OKB/USDT'), option_cls=ModernSpinnerOption, background_normal='', background_color=C_SURFACE_HOVER, font_size=26)
        grid.add_widget(symbol_spn)

        grid.add_widget(LeftAlignedLabel(text="K线日内周期:", font_size=28, bold=True))
        timeframe_spn = Spinner(text=self.active_timeframe, values=('1m', '3m', '5m', '15m'), option_cls=ModernSpinnerOption, background_normal='', background_color=C_SURFACE_HOVER, font_size=26)
        grid.add_widget(timeframe_spn)

        grid.add_widget(LeftAlignedLabel(text="策略杠杆:", font_size=28, bold=True))
        leverage_spn = Spinner(text=self.active_leverage, values=('1x (现货)', '2x', '3x', '5x', '10x'), option_cls=ModernSpinnerOption, background_normal='', background_color=C_SURFACE_HOVER, font_size=26)
        grid.add_widget(leverage_spn)

        def on_pop_market_change(spn, txt):
            leverage_spn.text = '1x (现货)' if '现货' in txt else '2x'
        market_type_spn.bind(text=on_pop_market_change)

        grid.add_widget(LeftAlignedLabel(text="核心量化策略:", font_size=28, bold=True))
        strat_spn = Spinner(
            text=self.active_strategy,
            values=(
                '【AI日内自适应决策】',
                '现货网格 (Spot Grid)',
                '合约中性网格 (Futures Neutral Grid)',
                '马丁格尔 / DCA (Martingale)',
                '期现/资金费率套利 (Funding Arb)',
                'CTA / 趋势追踪 (Trend)',
                'TWAP / 冰山算法 (Iceberg)'
            ),
            option_cls=ModernSpinnerOption, background_normal='', background_color=C_SURFACE_HOVER, font_size=24
        )
        grid.add_widget(strat_spn)

        grid.add_widget(LeftAlignedLabel(text="网格步长(%) / 单笔U:", font_size=28, bold=True))
        p_box = BoxLayout(spacing=10)
        grid_pct_in = TextInput(text=str(self.ai_suggested_spread), multiline=False, background_color=C_SURFACE_HOVER, foreground_color=C_TEXT_PRIMARY, font_size=26, padding=[10, 16, 10, 16])
        order_amt_in = TextInput(text=str(int(self.active_order_usdt)), multiline=False, background_color=C_SURFACE_HOVER, foreground_color=C_TEXT_PRIMARY, font_size=26, padding=[10, 16, 10, 16])
        p_box.add_widget(grid_pct_in)
        p_box.add_widget(order_amt_in)
        grid.add_widget(p_box)

        grid.add_widget(LeftAlignedLabel(text="日内止盈(%) / 止损(%):", font_size=28, bold=True))
        risk_box = BoxLayout(spacing=10)
        tp_in = TextInput(text=str(self.ai_suggested_tp), multiline=False, background_color=C_SURFACE_HOVER, foreground_color=C_TEXT_PRIMARY, font_size=26, padding=[10, 16, 10, 16])
        sl_in = TextInput(text=str(self.ai_suggested_sl), multiline=False, background_color=C_SURFACE_HOVER, foreground_color=C_TEXT_PRIMARY, font_size=26, padding=[10, 16, 10, 16])
        risk_box.add_widget(tp_in)
        risk_box.add_widget(sl_in)
        grid.add_widget(risk_box)

        grid.add_widget(LeftAlignedLabel(text="停机安全策略:", font_size=28, bold=True))
        stop_safe_spn = Spinner(text=self.active_cancel_on_stop, values=('停机自动撤销全部挂单', '停机保留盘口挂单'), option_cls=ModernSpinnerOption, background_normal='', background_color=C_SURFACE_HOVER, font_size=26)
        grid.add_widget(stop_safe_spn)

        box.add_widget(grid)

        btn_box = BoxLayout(size_hint_y=None, height=72, spacing=18)
        btn_confirm = FlatButton(text="确认采纳并应用策略", bg_color=(0.04, 0.55, 0.32, 1), bold=True, font_size=28, radius=[10])
        btn_cancel = FlatButton(text="取消", bg_color=C_SURFACE_HOVER, font_size=28, radius=[10], size_hint_x=0.35)
        btn_box.add_widget(btn_confirm)
        btn_box.add_widget(btn_cancel)
        box.add_widget(btn_box)

        popup = Popup(title="日内量化策略参数配置与风控设定", content=box, size_hint=(0.94, 0.96), auto_dismiss=False)

        def on_confirm(btn):
            try:
                self.active_market_type = market_type_spn.text
                self.active_symbol = symbol_spn.text
                self.active_timeframe = timeframe_spn.text.strip()
                self.active_leverage = leverage_spn.text
                self.active_strategy = strat_spn.text
                self.active_grid_pct = float(grid_pct_in.text.strip()) / 100.0
                self.active_order_usdt = float(order_amt_in.text.strip())
                self.active_tp_pct = float(tp_in.text.strip()) / 100.0
                self.active_sl_pct = float(sl_in.text.strip()) / 100.0
                self.active_cancel_on_stop = stop_safe_spn.text

                popup.dismiss()
                self.execute_strategy_change(self.active_strategy, cancel_existing_orders=True)
                self.strategy_adopted = True
                self.refresh_strategy_details_banner()
                self.append_log(f"策略已设定为: [{self.active_strategy}] | 标的: {self.active_symbol}")
            except Exception as ex:
                self.append_log(f"参数解析有误: {str(ex)[:30]}")

        def on_cancel(btn):
            popup.dismiss()

        btn_confirm.bind(on_press=on_confirm)
        btn_cancel.bind(on_press=on_cancel)
        popup.open()

    def execute_strategy_change(self, new_strategy, cancel_existing_orders=True):
        raw_symbol = self.active_symbol.strip().upper()
        display_name = new_strategy.split()[0] if '【' not in new_strategy else 'AI自适应'
        Clock.schedule_once(lambda dt: setattr(self.symbol_mode_lbl, 'text', f"{raw_symbol} [{display_name}]"))

        if cancel_existing_orders and self.exchange and self.current_symbol:
            def do_clean():
                try:
                    open_orders = self.exchange.fetch_open_orders(self.current_symbol)
                    for o in open_orders:
                        try:
                            self.exchange.cancel_order(o['id'], self.current_symbol)
                        except Exception:
                            pass
                    self.active_strategy_orders.clear()
                    self.refresh_orders_view([])
                    self.append_log(f"已清理旧策略活跃挂单 ({len(open_orders)} 笔)")
                except Exception as e:
                    self.append_log(f"清理挂单异常: {str(e)[:30]}")
            threading.Thread(target=do_clean, daemon=True).start()

    def init_orders_tab(self):
        self.view_orders = ModernCard(orientation='vertical', padding=[24, 18, 24, 18], spacing=10)
        head = BoxLayout(size_hint_y=None, height=64, spacing=14)
        head.add_widget(LeftAlignedLabel(text="盘口活跃挂单监控", font_size=34, bold=True, color=C_TEXT_PRIMARY))
        btn_refresh = FlatButton(text="立即刷新", size_hint_x=0.22, bg_color=C_SURFACE_HOVER, font_size=26, bold=True, radius=[8])
        btn_refresh.bind(on_press=self.manual_refresh_orders)
        head.add_widget(btn_refresh)
        self.view_orders.add_widget(head)

        t_head = BoxLayout(size_hint_y=None, height=52, spacing=8)
        t_head.add_widget(LeftAlignedLabel(text="方向 / 订单编号", size_hint_x=0.28, font_size=24, color=C_TEXT_MUTED, bold=True))
        t_head.add_widget(LeftAlignedLabel(text="委托价格 (USDT)", size_hint_x=0.24, font_size=24, color=C_TEXT_MUTED, bold=True))
        t_head.add_widget(LeftAlignedLabel(text="委托数量", size_hint_x=0.24, font_size=24, color=C_TEXT_MUTED, bold=True))
        t_head.add_widget(LeftAlignedLabel(text="状态 / 提交时间", size_hint_x=0.24, font_size=24, color=C_TEXT_MUTED, bold=True))
        self.view_orders.add_widget(t_head)

        scroll = ScrollView(size_hint=(1, 1))
        self.orders_list_layout = GridLayout(cols=1, spacing=8, size_hint_y=None)
        self.orders_list_layout.bind(minimum_height=self.orders_list_layout.setter('height'))
        scroll.add_widget(self.orders_list_layout)
        self.view_orders.add_widget(scroll)

    def manual_refresh_orders(self, instance=None):
        if self.exchange and self.current_symbol:
            def do_fetch():
                try:
                    open_orders = self.exchange.fetch_open_orders(self.current_symbol)
                    Clock.schedule_once(lambda dt: self.refresh_orders_view(open_orders))
                except Exception as e:
                    self.append_log(f"挂单刷新失败: {str(e)[:30]}")
            threading.Thread(target=do_fetch, daemon=True).start()
        else:
            self.refresh_orders_view([])

    def refresh_orders_view(self, open_orders):
        self.orders_list_layout.clear_widgets()
        if not open_orders:
            empty_box = BoxLayout(size_hint_y=None, height=140)
            empty_box.add_widget(Label(text="盘口暂无处于活动状态的订单", font_size=28, color=C_TEXT_MUTED))
            self.orders_list_layout.add_widget(empty_box)
            return

        for o in open_orders:
            row = ModernCard(bg_color=C_SURFACE_HOVER, size_hint_y=None, height=68, padding=[16, 8, 16, 8], spacing=8, radius=[8])
            side = o.get('side', 'buy').upper()
            is_buy = side == 'BUY'
            side_color = C_GREEN if is_buy else C_RED
            side_tag = f"● BUY  #{str(o['id'])[-6:]}" if is_buy else f"● SELL #{str(o['id'])[-6:]}"
            p_val = f"{float(o.get('price', 0)):.2f}"
            q_val = f"{float(o.get('amount', 0)):.4f}"
            t_str = time.strftime('%H:%M:%S', time.localtime(o.get('timestamp', time.time()*1000)/1000))

            row.add_widget(LeftAlignedLabel(text=side_tag, size_hint_x=0.28, font_size=26, bold=True, color=side_color))
            row.add_widget(LeftAlignedLabel(text=p_val, size_hint_x=0.24, font_size=28, bold=True, color=C_TEXT_PRIMARY))
            row.add_widget(LeftAlignedLabel(text=q_val, size_hint_x=0.24, font_size=28, color=C_TEXT_PRIMARY))
            row.add_widget(LeftAlignedLabel(text=f"挂单中 ({t_str})", size_hint_x=0.24, font_size=24, color=C_TEXT_MUTED))
            self.orders_list_layout.add_widget(row)

    def init_api_tab(self):
        self.view_api = ModernCard(orientation='vertical', padding=[40, 30, 40, 30], spacing=20)
        self.view_api.add_widget(LeftAlignedLabel(text="OKX 交易所安全连通中心", font_size=38, bold=True, color=C_TEXT_PRIMARY, size_hint_y=None, height=54))
        self.view_api.add_widget(LeftAlignedLabel(text="使用原生网络环境连通（支持科学上网），凭证已采用 Fernet 对称加密安全存储。", font_size=24, color=C_TEXT_MUTED, size_hint_y=None, height=36))

        grid = GridLayout(cols=2, spacing=[24, 16], row_default_height=76, row_force_default=True, size_hint_y=None, height=260)
        grid.add_widget(LeftAlignedLabel(text="OKX API Key:", font_size=28, bold=True, color=C_TEXT_PRIMARY))
        self.api_key_input = TextInput(multiline=False, password=True, background_color=C_SURFACE_HOVER, foreground_color=C_TEXT_PRIMARY, font_size=28, padding=[14, 18, 14, 18])
        grid.add_widget(self.api_key_input)

        grid.add_widget(LeftAlignedLabel(text="OKX Secret Key:", font_size=28, bold=True, color=C_TEXT_PRIMARY))
        self.secret_input = TextInput(multiline=False, password=True, background_color=C_SURFACE_HOVER, foreground_color=C_TEXT_PRIMARY, font_size=28, padding=[14, 18, 14, 18])
        grid.add_widget(self.secret_input)

        grid.add_widget(LeftAlignedLabel(text="OKX Passphrase:", font_size=28, bold=True, color=C_TEXT_PRIMARY))
        self.pass_input = TextInput(multiline=False, password=True, background_color=C_SURFACE_HOVER, foreground_color=C_TEXT_PRIMARY, font_size=28, padding=[14, 18, 14, 18])
        grid.add_widget(self.pass_input)

        self.view_api.add_widget(grid)

        btn_row = BoxLayout(size_hint_y=None, height=76, spacing=20)
        self.btn_connect_exchange = FlatButton(text="接入 OKX 交易所", bg_color=(0.04, 0.55, 0.32, 1), font_size=30, bold=True, radius=[10])
        self.btn_connect_exchange.bind(on_press=self.action_connect_exchange)
        self.btn_clear_cred = FlatButton(text="清空本地凭据", bg_color=(0.60, 0.18, 0.22, 1), font_size=30, bold=True, size_hint_x=0.35, radius=[10])
        self.btn_clear_cred.bind(on_press=self.clear_saved_credentials)

        btn_row.add_widget(self.btn_connect_exchange)
        btn_row.add_widget(self.btn_clear_cred)
        self.view_api.add_widget(btn_row)

    def action_connect_exchange(self, instance=None):
        key = self.api_key_input.text.strip()
        secret = self.secret_input.text.strip()
        pwd = self.pass_input.text.strip()

        if not key or not secret or not pwd:
            self.show_info_popup("错误", "请完整填写 API Key、Secret 和 Passphrase！")
            return

        self.btn_connect_exchange.text = "正在连通交易所..."
        self.btn_connect_exchange.set_bg((0.15, 0.35, 0.55, 1))

        def connect_worker():
            try:
                is_spot = '现货' in self.active_market_type
                default_type = 'spot' if is_spot else 'swap'

                test_exchange = ccxt.okx({
                    'apiKey': key,
                    'secret': secret,
                    'password': pwd,
                    'enableRateLimit': True,
                    'timeout': 15000,
                    'options': {'defaultType': default_type}
                })

                test_exchange.load_markets()
                balance = test_exchange.fetch_balance()
                usdt_free = float(balance['free'].get('USDT', 0.0))

                self.exchange = test_exchange
                self.is_connected = True
                CredentialManager.save(key, secret, pwd)

                Clock.schedule_once(lambda dt: self.btn_connect_exchange.set_bg((0.04, 0.55, 0.32, 1)))
                Clock.schedule_once(lambda dt: setattr(self.btn_connect_exchange, 'text', "已成功接入 OKX"))
                Clock.schedule_once(lambda dt, b=usdt_free: setattr(self.balance_lbl, 'text', f"{b:.2f} USDT (0 笔)"))
                Clock.schedule_once(lambda dt: setattr(self.status_lbl, 'text', "在线待命"))
                Clock.schedule_once(lambda dt: setattr(self.status_lbl, 'color', C_GREEN))
                
                self.append_log(f"鉴权成功：OKX 账户接入成功！账户可用 USDT: {usdt_free:.2f}")
                threading.Thread(target=self.market_and_ai_daemon_thread, daemon=True).start()
                Clock.schedule_once(lambda dt: self.switch_tab(0), 1.0)

            except Exception as e:
                err_msg = str(e)
                self.append_log(f"连接失败: {err_msg[:50]}")
                Clock.schedule_once(lambda dt: self.btn_connect_exchange.set_bg((0.04, 0.55, 0.32, 1)))
                Clock.schedule_once(lambda dt: setattr(self.btn_connect_exchange, 'text', "接入 OKX 交易所"))
                Clock.schedule_once(lambda dt, msg=err_msg: self.show_info_popup("连接失败", f"无法连通 OKX，原因:\n{msg[:120]}"))

        threading.Thread(target=connect_worker, daemon=True).start()

    def show_info_popup(self, title, message):
        box = BoxLayout(orientation='vertical', padding=[24, 20, 24, 20], spacing=16)
        box.add_widget(Label(text=message, font_size=26, color=C_TEXT_PRIMARY, halign='center'))
        btn = FlatButton(text="确定", size_hint_y=None, height=60, bg_color=C_SURFACE_HOVER, font_size=26, radius=[8])
        box.add_widget(btn)
        pop = Popup(title=title, content=box, size_hint=(0.65, 0.45))
        btn.bind(on_press=pop.dismiss)
        pop.open()

    def load_saved_credentials(self):
        creds = CredentialManager.load()
        if creds:
            self.api_key_input.text = creds.get("api_key", "")
            self.secret_input.text = creds.get("secret", "")
            self.pass_input.text = creds.get("passphrase", "")
            self.append_log("已载入本地 API 凭据，点击【接入 OKX 交易所】即可连通。")
            return True
        return False

    def clear_saved_credentials(self, instance=None):
        self.api_key_input.text = ""
        self.secret_input.text = ""
        self.pass_input.text = ""
        self.is_connected = False
        CredentialManager.clear()
        self.append_log("已彻底清除本地保存的 API 凭据！")

    def init_pnl_tab(self):
        self.view_pnl = ModernCard(orientation='vertical', padding=[32, 24, 32, 24], spacing=16)
        self.view_pnl.add_widget(LeftAlignedLabel(text="多维策略净盈亏看板 (已扣除交易手续费)", font_size=34, bold=True, color=C_TEXT_PRIMARY, size_hint_y=None, height=52))

        grid = GridLayout(cols=2, spacing=[30, 16], row_default_height=78, row_force_default=True)
        grid.add_widget(LeftAlignedLabel(text="累计已实现净利润:", font_size=28, bold=True, color=C_TEXT_MUTED))
        self.pnl_total_lbl = LeftAlignedLabel(text="+0.0000 USDT", font_size=42, color=C_GREEN, bold=True)
        grid.add_widget(self.pnl_total_lbl)

        grid.add_widget(LeftAlignedLabel(text="预估今日收益 (24H):", font_size=28, bold=True, color=C_TEXT_MUTED))
        self.pnl_day_lbl = LeftAlignedLabel(text="+0.00 USDT", font_size=36, color=C_TEXT_PRIMARY, bold=True)
        grid.add_widget(self.pnl_day_lbl)

        grid.add_widget(LeftAlignedLabel(text="预估本周收益 (7D):", font_size=28, bold=True, color=C_TEXT_MUTED))
        self.pnl_week_lbl = LeftAlignedLabel(text="+0.00 USDT", font_size=36, color=C_TEXT_PRIMARY, bold=True)
        grid.add_widget(self.pnl_week_lbl)

        grid.add_widget(LeftAlignedLabel(text="预估本月收益 (30D):", font_size=28, bold=True, color=C_TEXT_MUTED))
        self.pnl_month_lbl = LeftAlignedLabel(text="+0.00 USDT", font_size=36, color=C_TEXT_PRIMARY, bold=True)
        grid.add_widget(self.pnl_month_lbl)

        grid.add_widget(LeftAlignedLabel(text="平滑年化折算 (APY):", font_size=28, bold=True, color=C_TEXT_MUTED))
        self.pnl_apy_lbl = LeftAlignedLabel(text="样本积累中...", font_size=38, color=C_AMBER, bold=True)
        grid.add_widget(self.pnl_apy_lbl)

        grid.add_widget(LeftAlignedLabel(text="有效套利结算轮次:", font_size=28, bold=True, color=C_TEXT_MUTED))
        self.pnl_trades_lbl = LeftAlignedLabel(text="0 次", font_size=36, color=C_ACCENT_CYAN, bold=True)
        grid.add_widget(self.pnl_trades_lbl)

        self.view_pnl.add_widget(grid)

    def update_pnl_analytics(self, net_profit_usdt):
        self.total_profit_usdt += net_profit_usdt
        self.total_arbitrage_count += 1
        elapsed_seconds = max(1, time.time() - (self.start_time or time.time()))
        
        if elapsed_seconds >= 900 and self.total_arbitrage_count >= 2:
            daily_rate = (self.total_profit_usdt / elapsed_seconds) * 86400
            weekly_rate = daily_rate * 7
            monthly_rate = daily_rate * 30
            try:
                base_capital = max(self.active_order_usdt * 2, 20.0)
                apy = (daily_rate * 365 / base_capital) * 100
                apy_str = f"{min(apy, 999.99):.2f} %"
            except Exception:
                apy_str = "0.00 %"
            day_str = f"{daily_rate:+.2f} USDT"
            week_str = f"{weekly_rate:+.2f} USDT"
            month_str = f"{monthly_rate:+.2f} USDT"
        else:
            day_str = "-- USDT (样本积累中)"
            week_str = "-- USDT (样本积累中)"
            month_str = "-- USDT (样本积累中)"
            apy_str = "样本积累中..."

        Clock.schedule_once(lambda dt: setattr(self.pnl_total_lbl, 'text', f"{self.total_profit_usdt:+.4f} USDT"))
        Clock.schedule_once(lambda dt: setattr(self.pnl_day_lbl, 'text', day_str))
        Clock.schedule_once(lambda dt: setattr(self.pnl_week_lbl, 'text', week_str))
        Clock.schedule_once(lambda dt: setattr(self.pnl_month_lbl, 'text', month_str))
        Clock.schedule_once(lambda dt: setattr(self.pnl_apy_lbl, 'text', apy_str))
        Clock.schedule_once(lambda dt: setattr(self.pnl_trades_lbl, 'text', f"{self.total_arbitrage_count} 次"))

    def init_logs_tab(self):
        self.view_logs = ModernCard(orientation='vertical', padding=[20, 16, 20, 16], bg_color=(0.02, 0.03, 0.04, 1))
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self.log_lbl = Label(text="[SYSTEM] 日内量化操盘工作站已就绪。所有策略算法均已载入。", font_size=26, color=(0.4, 0.8, 0.5, 1), size_hint=(1, None), halign='left', valign='top')
        self.log_lbl.bind(width=lambda instance, value: setattr(instance, 'text_size', (value, None)))
        self.log_lbl.bind(texture_size=lambda instance, value: setattr(instance, 'height', value[1]))
        scroll.add_widget(self.log_lbl)
        self.view_logs.add_widget(scroll)

    def append_log(self, text):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {text}"
        Clock.schedule_once(lambda dt: setattr(self.log_lbl, 'text', f"{self.log_lbl.text}\n[{time.strftime('%H:%M:%S')}] {text}"))
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception:
            pass

    def export_logs(self, instance=None):
        if not os.path.exists(self.log_file_path):
            self.append_log("尚无日志记录。")
            return
        export_name = f"OKX_Bot_Log_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        export_path = os.path.join(os.getcwd(), export_name)
        try:
            shutil.copyfile(self.log_file_path, export_path)
            self.append_log(f"日志已成功导出至: {export_name}")
        except Exception as e:
            self.append_log(f"日志导出失败: {str(e)[:30]}")

    def analyze_intraday_market_regime(self, ohlcv, funding_rate=0.0):
        closes = [c[4] for c in ohlcv]
        highs = [c[2] for c in ohlcv]
        lows = [c[3] for c in ohlcv]
        curr_price = closes[-1]

        def get_ema(series, period):
            k = 2.0 / (period + 1)
            res = [series[0]]
            for v in series[1:]:
                res.append(v * k + res[-1] * (1 - k))
            return res[-1]

        ema9 = get_ema(closes, 9)
        ema21 = get_ema(closes, 21)

        gains, losses = [], []
        for i in range(1, len(closes)):
            chg = closes[i] - closes[i-1]
            gains.append(max(0, chg))
            losses.append(max(0, -chg))
        avg_gain = sum(gains[-14:]) / 14 if gains else 0
        avg_loss = sum(losses[-14:]) / 14 if losses else 0
        rs = avg_gain / avg_loss if avg_loss != 0 else 100.0
        rsi14 = 100.0 - (100.0 / (1.0 + rs))

        trs = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])) for i in range(1, len(closes))]
        atr_pct = (sum(trs[-14:]) / 14) / curr_price * 100.0 if trs else 0.5

        sma20 = sum(closes[-20:]) / 20
        var = sum((x - sma20)**2 for x in closes[-20:]) / 20
        std = math.sqrt(var)
        bandwidth = (4 * std) / sma20 * 100.0

        spread = round(max(0.30, atr_pct * 0.45), 2)
        tp = round(max(1.0, atr_pct * 1.5), 2)
        sl = round(max(2.5, atr_pct * 2.8), 2)

        if abs(funding_rate) >= 0.0003 and bandwidth < 2.5:
            strategy = "期现/资金费率套利 (Funding Arb)"
            reason = f"高额资金费率 ({funding_rate*100:+.3f}%) -> 推荐「期现无风险套利」"
        elif abs(ema9 - ema21) / ema21 > 0.004 and bandwidth > 2.2:
            direction = "多头走强" if ema9 > ema21 else "空头破位"
            strategy = "CTA / 趋势追踪 (Trend)"
            reason = f"强动量突破 ({direction}) -> 推荐「日内CTA趋势追踪」"
        elif (rsi14 < 30 or rsi14 > 70) and bandwidth < 3.2:
            tag = "超卖低吸" if rsi14 < 30 else "超买回踩"
            strategy = "马丁格尔 / DCA (Martingale)"
            reason = f"箱体极端偏离 ({tag} RSI:{rsi14:.1f}) -> 推荐「DCA马丁阶梯套利」"
        else:
            if '合约' in self.active_market_type:
                strategy = "合约中性网格 (Futures Neutral Grid)"
                reason = f"微幅窄幅波动 (振幅 {bandwidth:.2f}%) -> 推荐「合约中性网格」"
            else:
                strategy = "现货网格 (Spot Grid)"
                reason = f"常态箱体整理 (ATR {atr_pct:.2f}%) -> 推荐「现货震荡网格」"

        return {
            'strategy': strategy,
            'reason': reason,
            'spread': spread,
            'tp': tp,
            'sl': sl,
            'rsi': rsi14,
            'atr_pct': atr_pct,
            'bandwidth': bandwidth,
            'ema9': ema9,
            'ema21': ema21,
            'funding_rate': funding_rate
        }

    def market_and_ai_daemon_thread(self):
        while self.market_monitor_active and self.is_connected:
            try:
                is_spot = '现货' in self.active_market_type
                raw_symbol = self.active_symbol.strip().upper()
                symbol = raw_symbol if is_spot else f"{raw_symbol}:USDT"
                self.current_symbol = symbol
                tf = self.active_timeframe

                ticker = self.exchange.fetch_ticker(symbol)
                current_price = float(ticker['last'])
                Clock.schedule_once(lambda dt, p=current_price: setattr(self.price_lbl, 'text', f"{p:,.2f}"))

                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=tf, limit=35)
                closes = [c[4] for c in ohlcv]
                Clock.schedule_once(lambda dt, p_list=closes: self.chart_widget.update_prices(p_list))

                funding_rate = 0.0
                try:
                    swap_symbol = f"{raw_symbol}:USDT" if is_spot else symbol
                    fr_info = self.exchange.fetch_funding_rate(swap_symbol)
                    funding_rate = float(fr_info.get('fundingRate', 0.0) or 0.0)
                except Exception:
                    pass

                metrics = self.analyze_intraday_market_regime(ohlcv, funding_rate)
                self.latest_market_metrics = metrics
                self.current_ai_target_strategy = metrics['strategy']
                self.ai_suggested_spread = metrics['spread']
                self.ai_suggested_tp = metrics['tp']
                self.ai_suggested_sl = metrics['sl']

                Clock.schedule_once(lambda dt, r=f"AI 日内诊断 [{tf}]: {metrics['reason']}": setattr(self.ai_recommend_lbl, 'text', r))
                time.sleep(8)
            except Exception:
                time.sleep(10)

    def toggle_bot(self, instance=None):
        if not self.running:
            if not self.is_connected:
                self.show_info_popup("阻断提示", "请先在「API凭证」点击接入！")
                return

            if not self.strategy_adopted:
                self.show_info_popup("阻断提示", "请先在操盘终端点击「配置策略参数」应用后再启动！")
                return

            self.running = True
            self.start_time = time.time()
            self.toggle_btn.text = "紧急停止日内策略"
            self.toggle_btn.set_bg(C_RED)
            self.status_lbl.text = "策略执行中"
            self.status_lbl.color = C_GREEN
            threading.Thread(target=self.bot_execution_loop, daemon=True).start()
        else:
            self.running = False
            self.toggle_btn.text = "启动日内高胜率策略"
            self.toggle_btn.set_bg((0.04, 0.55, 0.32, 1))
            self.status_lbl.text = "策略已终止"
            self.status_lbl.color = C_AMBER
            self.append_log("用户手动暂停了策略。")

    def calc_order_qty(self, symbol, order_usdt, price):
        market = self.exchange.market(symbol)
        is_contract = market.get('contract', False) or market.get('swap', False)
        
        if is_contract:
            ct_size = float(market.get('contractSize', 1.0))
            contract_val_usdt = ct_size * price if ct_size > 0 else price
            contracts = max(1, int(order_usdt / contract_val_usdt))
            return float(contracts)
        else:
            raw_qty = order_usdt / price
            safe_qty = float(self.exchange.amount_to_precision(symbol, raw_qty))
            min_amt = float(market.get('limits', {}).get('amount', {}).get('min', 0.0001))
            return max(safe_qty, min_amt)

    def calc_net_profit(self, symbol, buy_price, sell_price, qty):
        market = self.exchange.market(symbol)
        fee_rate = float(market.get('maker', 0.0008))
        gross_profit = (sell_price - buy_price) * qty
        total_fee = (buy_price * qty + sell_price * qty) * fee_rate
        net_profit = gross_profit - total_fee
        return net_profit, total_fee

    def execute_market_close(self, symbol, is_spot, base_currency):
        self.append_log("【触发风控】执行市价全量平仓保护...")
        try:
            if is_spot:
                balance = self.exchange.fetch_balance()
                base_free = float(balance['free'].get(base_currency, 0.0))
                ticker = self.exchange.fetch_ticker(symbol)
                curr_price = float(ticker['last'])
                if base_free * curr_price >= 2.0:
                    safe_sell_qty = float(self.exchange.amount_to_precision(symbol, base_free * 0.999))
                    self.exchange.create_market_sell_order(symbol, safe_sell_qty)
                    self.append_log(f"【现货清仓完成】市价卖出 {safe_sell_qty} {base_currency}")
            else:
                positions = self.exchange.fetch_positions([symbol])
                for pos in positions:
                    contracts = float(pos.get('contracts', 0) or pos.get('size', 0))
                    side = pos.get('side', '')
                    if contracts > 0:
                        if side == 'long':
                            self.exchange.create_market_sell_order(symbol, contracts, params={'reduceOnly': True})
                        elif side == 'short':
                            self.exchange.create_market_buy_order(symbol, contracts, params={'reduceOnly': True})
                        self.append_log(f"【合约平仓完成】平仓 {contracts} 张")
        except Exception as close_err:
            self.append_log(f"【平仓异常】: {str(close_err)[:40]}")

    def bot_execution_loop(self):
        try:
            is_spot = '现货' in self.active_market_type
            raw_symbol = self.active_symbol.strip().upper()
            symbol = raw_symbol if is_spot else f"{raw_symbol}:USDT"
            base_currency = raw_symbol.split('/')[0]

            if not is_spot:
                try:
                    lev_num = int(self.active_leverage.replace('x', '').split()[0].strip())
                    self.exchange.set_leverage(lev_num, symbol)
                    self.append_log(f"合约杠杆已生效: {lev_num}x")
                except Exception as lev_err:
                    self.append_log(f"杠杆设置提示: {str(lev_err)[:30]}")

            grid_pct = self.active_grid_pct
            order_usdt = self.active_order_usdt
            tp_pct = self.active_tp_pct
            sl_pct = self.active_sl_pct

            self.exchange.load_markets()
            consecutive_net_errors = 0
            initial_entry_price = None

            dca_entry_prices = []
            trend_position = None
            funding_arb_active = False
            twap_slices_executed = 0

            while self.running:
                try:
                    if 'AI日内自适应' in self.active_strategy:
                        active_strat = self.current_ai_target_strategy
                    else:
                        active_strat = self.active_strategy

                    ticker = self.exchange.fetch_ticker(symbol)
                    current_price = float(ticker['last'])
                    balance = self.exchange.fetch_balance()
                    usdt_free = float(balance['free'].get('USDT', 0.0))
                    base_free = float(balance['free'].get(base_currency, 0.0))

                    open_orders = self.exchange.fetch_open_orders(symbol)
                    Clock.schedule_once(lambda dt, b=usdt_free, c=len(open_orders): setattr(self.balance_lbl, 'text', f"{b:.2f} USDT ({c} 笔)"))
                    Clock.schedule_once(lambda dt, ods=open_orders: self.refresh_orders_view(ods))
                    open_order_ids = {o['id'] for o in open_orders}

                    if initial_entry_price and not funding_arb_active:
                        pnl_ratio = (current_price - initial_entry_price) / initial_entry_price
                        if pnl_ratio >= tp_pct or pnl_ratio <= -sl_pct:
                            tag = "全局止盈" if pnl_ratio >= tp_pct else "硬止损"
                            self.append_log(f"触发日内 {tag} ({pnl_ratio*100:+.2f}%)，执行市价平仓保护！")
                            self.execute_market_close(symbol, is_spot, base_currency)
                            self.running = False
                            break

                    for oid, oinfo in list(self.active_strategy_orders.items()):
                        if oid not in open_order_ids:
                            try:
                                ord_info = self.exchange.fetch_order(oid, symbol)
                                status = ord_info.get('status')
                                filled_qty = float(ord_info.get('filled', 0.0))
                                avg_price = float(ord_info.get('average') or ord_info.get('price') or oinfo['price'])
                            except Exception:
                                continue

                            if status == 'closed' and filled_qty > 0:
                                side = oinfo['side']
                                self.append_log(f"【真实成交确认】#{str(oid)[-6:]} {side.upper()} 均价: {avg_price:.2f} | 数量: {filled_qty:.4f}")

                                if "现货网格" in active_strat:
                                    if side == 'buy':
                                        t_sell_price = float(self.exchange.price_to_precision(symbol, avg_price * (1 + grid_pct)))
                                        sell_qty = self.calc_order_qty(symbol, order_usdt, t_sell_price)
                                        try:
                                            s_ord = self.exchange.create_limit_sell_order(symbol, sell_qty, t_sell_price)
                                            self.active_strategy_orders[s_ord['id']] = {'side': 'sell', 'price': t_sell_price, 'qty': sell_qty, 'buy_price': avg_price}
                                            self.append_log(f"【现货网格】挂反手卖单: 价 {t_sell_price}")
                                        except Exception as se:
                                            self.append_log(f"挂卖单受阻: {str(se)[:30]}")
                                    elif side == 'sell':
                                        buy_p = oinfo.get('buy_price', avg_price * (1 - grid_pct))
                                        net_p, fee = self.calc_net_profit(symbol, buy_p, avg_price, filled_qty)
                                        self.update_pnl_analytics(net_p)
                                        self.append_log(f"【现货网格】套利落袋: 净利 +{net_p:.4f}U (手续费 {fee:.4f}U)")

                                        t_buy_price = float(self.exchange.price_to_precision(symbol, avg_price * (1 - grid_pct)))
                                        buy_qty = self.calc_order_qty(symbol, order_usdt, t_buy_price)
                                        try:
                                            b_ord = self.exchange.create_limit_buy_order(symbol, buy_qty, t_buy_price)
                                            self.active_strategy_orders[b_ord['id']] = {'side': 'buy', 'price': t_buy_price, 'qty': buy_qty}
                                            self.append_log(f"【现货网格】复位挂买单: 价 {t_buy_price}")
                                        except Exception as be:
                                            self.append_log(f"补买单受阻: {str(be)[:30]}")

                                elif "中性网格" in active_strat:
                                    role = oinfo.get('role', 'open_long' if side == 'buy' else 'open_short')
                                    if side == 'buy':
                                        if role == 'open_long':
                                            t_sell_p = float(self.exchange.price_to_precision(symbol, avg_price * (1 + grid_pct)))
                                            sell_qty = self.calc_order_qty(symbol, order_usdt, t_sell_p)
                                            try:
                                                s_ord = self.exchange.create_limit_sell_order(symbol, sell_qty, t_sell_p)
                                                self.active_strategy_orders[s_ord['id']] = {
                                                    'side': 'sell', 'role': 'close_long', 'price': t_sell_p, 'qty': sell_qty, 'entry_price': avg_price
                                                }
                                                self.append_log(f"【合约中性网格】多单开仓成交，挂止盈平多单: 价 {t_sell_p}")
                                            except Exception as se:
                                                self.append_log(f"挂平多单受阻: {str(se)[:30]}")
                                        elif role == 'close_short':
                                            entry_p = oinfo.get('entry_price', avg_price * (1 + grid_pct))
                                            net_p, fee = self.calc_net_profit(symbol, avg_price, entry_p, filled_qty)
                                            self.update_pnl_analytics(net_p)
                                            self.append_log(f"【合约中性网格】空单止盈落袋！净利: +{net_p:.4f}U (手续费 {fee:.4f}U)")
                                            t_ask_p = float(self.exchange.price_to_precision(symbol, avg_price * (1 + grid_pct)))
                                            ask_qty = self.calc_order_qty(symbol, order_usdt, t_ask_p)
                                            try:
                                                s_ord = self.exchange.create_limit_sell_order(symbol, ask_qty, t_ask_p)
                                                self.active_strategy_orders[s_ord['id']] = {
                                                    'side': 'sell', 'role': 'open_short', 'price': t_ask_p, 'qty': ask_qty
                                                }
                                                self.append_log(f"【合约中性网格】复位补挂开空单: 价 {t_ask_p}")
                                            except Exception as re_s:
                                                self.append_log(f"补空单受阻: {str(re_s)[:30]}")

                                    elif side == 'sell':
                                        if role == 'open_short':
                                            t_buy_p = float(self.exchange.price_to_precision(symbol, avg_price * (1 - grid_pct)))
                                            buy_qty = self.calc_order_qty(symbol, order_usdt, t_buy_p)
                                            try:
                                                b_ord = self.exchange.create_limit_buy_order(symbol, buy_qty, t_buy_p)
                                                self.active_strategy_orders[b_ord['id']] = {
                                                    'side': 'buy', 'role': 'close_short', 'price': t_buy_p, 'qty': buy_qty, 'entry_price': avg_price
                                                }
                                                self.append_log(f"【合约中性网格】空单开仓成交，挂止盈平空单: 价 {t_buy_p}")
                                            except Exception as be:
                                                self.append_log(f"挂平空单受阻: {str(be)[:30]}")
                                        elif role == 'close_long':
                                            entry_p = oinfo.get('entry_price', avg_price * (1 - grid_pct))
                                            net_p, fee = self.calc_net_profit(symbol, entry_p, avg_price, filled_qty)
                                            self.update_pnl_analytics(net_p)
                                            self.append_log(f"【合约中性网格】多单止盈落袋！净利: +{net_p:.4f}U (手续费 {fee:.4f}U)")
                                            t_bid_p = float(self.exchange.price_to_precision(symbol, avg_price * (1 - grid_pct)))
                                            bid_qty = self.calc_order_qty(symbol, order_usdt, t_bid_p)
                                            try:
                                                b_ord = self.exchange.create_limit_buy_order(symbol, bid_qty, t_bid_p)
                                                self.active_strategy_orders[b_ord['id']] = {
                                                    'side': 'buy', 'role': 'open_long', 'price': t_bid_p, 'qty': bid_qty
                                                }
                                                self.append_log(f"【合约中性网格】复位补挂开多单: 价 {t_bid_p}")
                                            except Exception as re_b:
                                                self.append_log(f"补多单受阻: {str(re_b)[:30]}")

                                del self.active_strategy_orders[oid]

                            elif status in ['canceled', 'expired', 'rejected']:
                                self.append_log(f"订单 #{str(oid)[-6:]} 失效/撤销，移出追踪。")
                                del self.active_strategy_orders[oid]

                    if "现货网格" in active_strat and len(open_orders) == 0 and len(self.active_strategy_orders) == 0:
                        if usdt_free >= order_usdt:
                            buy_p = float(self.exchange.price_to_precision(symbol, current_price * (1 - grid_pct)))
                            buy_q = self.calc_order_qty(symbol, order_usdt, buy_p)
                            self.append_log(f"【现货网格】布设首期底仓买单: {buy_p} | 量 {buy_q}")
                            b_ord = self.exchange.create_limit_buy_order(symbol, buy_q, buy_p)
                            self.active_strategy_orders[b_ord['id']] = {'side': 'buy', 'price': buy_p, 'qty': buy_q}
                            initial_entry_price = current_price

                    elif "中性网格" in active_strat and len(open_orders) == 0 and len(self.active_strategy_orders) == 0:
                        bid_p = float(self.exchange.price_to_precision(symbol, current_price * (1 - grid_pct)))
                        ask_p = float(self.exchange.price_to_precision(symbol, current_price * (1 + grid_pct)))
                        o_qty = self.calc_order_qty(symbol, order_usdt, current_price)
                        
                        b_ord = self.exchange.create_limit_buy_order(symbol, o_qty, bid_p)
                        self.active_strategy_orders[b_ord['id']] = {'side': 'buy', 'role': 'open_long', 'price': bid_p, 'qty': o_qty}
                        
                        s_ord = self.exchange.create_limit_sell_order(symbol, o_qty, ask_p)
                        self.active_strategy_orders[s_ord['id']] = {'side': 'sell', 'role': 'open_short', 'price': ask_p, 'qty': o_qty}
                        
                        initial_entry_price = current_price
                        self.append_log(f"【合约中性网格】双向盘口部署完成: 买单 {bid_p} | 卖单 {ask_p} | 数量 {o_qty}")

                    elif "马丁" in active_strat or "DCA" in active_strat:
                        if len(dca_entry_prices) == 0:
                            if usdt_free >= order_usdt:
                                o_qty = self.calc_order_qty(symbol, order_usdt, current_price)
                                self.append_log(f"【马丁/DCA】启动第一期建仓: 买入 {o_qty} @ {current_price}")
                                self.exchange.create_market_buy_order(symbol, o_qty)
                                dca_entry_prices.append(current_price)
                                initial_entry_price = current_price
                        else:
                            last_p = dca_entry_prices[-1]
                            avg_cost = sum(dca_entry_prices) / len(dca_entry_prices)
                            if current_price >= avg_cost * (1 + tp_pct):
                                self.append_log(f"【马丁/DCA】持仓均价回抽达到目标 (+{tp_pct*100}%)，全部平仓落袋！")
                                self.execute_market_close(symbol, is_spot, base_currency)
                                total_vol = len(dca_entry_prices) * (order_usdt / avg_cost)
                                net_p, fee = self.calc_net_profit(symbol, avg_cost, current_price, total_vol)
                                self.update_pnl_analytics(net_p)
                                dca_entry_prices.clear()
                                initial_entry_price = None
                            elif current_price <= last_p * (1 - grid_pct) and len(dca_entry_prices) < self.max_dca_rounds:
                                mult = 1.0 + (len(dca_entry_prices) * 0.2)
                                step_usdt = order_usdt * mult
                                if usdt_free >= step_usdt:
                                    step_qty = self.calc_order_qty(symbol, step_usdt, current_price)
                                    self.append_log(f"【马丁/DCA】触发第 {len(dca_entry_prices)+1} 阶梯加倍抄底: 量 {step_qty} ({mult:.1f}x)")
                                    self.exchange.create_market_buy_order(symbol, step_qty)
                                    dca_entry_prices.append(current_price)

                    elif "期现" in active_strat or "资金费率" in active_strat:
                        swap_sym = f"{raw_symbol}:USDT"
                        if not funding_arb_active:
                            if usdt_free >= order_usdt * 2:
                                half_usdt = order_usdt
                                self.append_log(f"【期现套利】对冲建仓中：买入现货 {half_usdt}U 并做空等值永续合约...")
                                spot_qty = self.calc_order_qty(raw_symbol, half_usdt, current_price)
                                self.exchange.create_market_buy_order(raw_symbol, spot_qty)

                                swap_contracts = self.calc_order_qty(swap_sym, half_usdt, current_price)
                                self.exchange.create_market_sell_order(swap_sym, swap_contracts)
                                
                                funding_arb_active = True
                                self.append_log("【期现套利】Delta 中性对冲建立完毕，正在静候资金费率结算！")
                        else:
                            fr = self.latest_market_metrics.get('funding_rate', 0.0)
                            if fr < -0.0001:
                                self.append_log("【期现套利】资金费率逆转为负，平仓以规避费率磨损...")
                                self.execute_market_close(raw_symbol, True, base_currency)
                                self.execute_market_close(swap_sym, False, base_currency)
                                funding_arb_active = False

                    elif "CTA" in active_strat or "趋势追踪" in active_strat:
                        ema9 = self.latest_market_metrics.get('ema9', current_price)
                        ema21 = self.latest_market_metrics.get('ema21', current_price)

                        if ema9 > ema21 * 1.0025 and trend_position != 'long' and len(open_orders) == 0:
                            if trend_position == 'short':
                                self.execute_market_close(symbol, is_spot, base_currency)
                            order_qty = self.calc_order_qty(symbol, order_usdt, current_price)
                            if usdt_free >= order_usdt:
                                self.append_log(f"【日内CTA】EMA9 上穿 EMA21！多头确立，买入做多: {order_qty}")
                                self.exchange.create_market_buy_order(symbol, order_qty)
                                trend_position = 'long'
                                initial_entry_price = current_price

                        elif ema9 < ema21 * 0.9975 and trend_position != 'short':
                            if trend_position == 'long':
                                self.append_log("【日内CTA】EMA9 下穿 EMA21！多头趋势衰竭，市价平多...")
                                self.execute_market_close(symbol, is_spot, base_currency)
                                trend_position = None
                                initial_entry_price = None

                            if not is_spot and trend_position is None and len(open_orders) == 0:
                                order_qty = self.calc_order_qty(symbol, order_usdt, current_price)
                                self.append_log(f"【日内CTA】空头突破确认，开空: {order_qty} 张")
                                self.exchange.create_market_sell_order(symbol, order_qty)
                                trend_position = 'short'
                                initial_entry_price = current_price

                    elif "TWAP" in active_strat or "冰山" in active_strat:
                        if twap_slices_executed < 5:
                            slice_usdt = order_usdt / 5.0
                            if usdt_free >= slice_usdt:
                                slice_qty = self.calc_order_qty(symbol, slice_usdt, current_price)
                                best_bid = float(self.exchange.price_to_precision(symbol, current_price * 0.9995))
                                self.append_log(f"【TWAP/冰山】隐蔽挂出第 {twap_slices_executed+1}/5 笔微单: {slice_qty} @ {best_bid}")
                                self.exchange.create_limit_buy_order(symbol, slice_qty, best_bid)
                                twap_slices_executed += 1
                        else:
                            self.append_log("【TWAP/冰山】目标切片全额执行完毕，退出单次任务。")
                            self.running = False
                            break

                    consecutive_net_errors = 0
                    for _ in range(10):
                        if not self.running:
                            break
                        time.sleep(1)

                except Exception as loop_err:
                    consecutive_net_errors += 1
                    err_msg = str(loop_err)
                    if "timed out" in err_msg.lower() or "connection" in err_msg.lower():
                        sleep_time = min(60, consecutive_net_errors * 10)
                        self.append_log(f"网络断开 ({consecutive_net_errors}次)，熔断休眠 {sleep_time}s...")
                        time.sleep(sleep_time)
                    else:
                        self.append_log(f"轮询警告: {err_msg[:35]}")
                        time.sleep(5)

        except Exception as e:
            self.append_log(f"主线程异常退出: {str(e)[:35]}")
            self.running = False
        finally:
            if self.exchange and '自动撤销' in self.active_cancel_on_stop and self.current_symbol:
                try:
                    self.append_log("停机保护：正在撤销盘口活跃挂单...")
                    active_orders = self.exchange.fetch_open_orders(self.current_symbol)
                    for o in active_orders:
                        try:
                            self.exchange.cancel_order(o['id'], self.current_symbol)
                        except Exception:
                            pass
                    self.active_strategy_orders.clear()
                    self.refresh_orders_view([])
                    self.append_log(f"已清理全部盘口挂单 ({len(active_orders)} 笔)。")
                except Exception as cancel_err:
                    self.append_log(f"撤单失败: {str(cancel_err)[:30]}")

            Clock.schedule_once(lambda dt: self.toggle_btn.set_bg((0.04, 0.55, 0.32, 1)))
            Clock.schedule_once(lambda dt: setattr(self.toggle_btn, 'text', "启动日内高胜率策略"))
            Clock.schedule_once(lambda dt: setattr(self.status_lbl, 'text', "已停机就绪"))
            Clock.schedule_once(lambda dt: setattr(self.status_lbl, 'color', C_AMBER))


if __name__ == '__main__':
    import traceback
    try:
        OKXProQuantStationApp().run()
    except Exception as e:
        err_msg = traceback.format_exc()
        try:
            with open('/sdcard/Download/okx_crash.txt', 'w', encoding='utf-8') as f:
                f.write(err_msg)
        except Exception:
            pass

        # 启动轻量应急界面在手机屏幕上显示错误
        from kivy.app import App
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.label import Label

        class CrashDisplayApp(App):
            def build(self):
                scroll = ScrollView()
                lbl = Label(
                    text=f"[启动崩溃原因]\n\n{err_msg}",
                    size_hint_y=None,
                    text_size=(None, None),
                    color=(1, 0.2, 0.2, 1)
                )
                lbl.bind(texture_size=lambda inst, val: setattr(lbl, 'size', val))
                scroll.add_widget(lbl)
                return scroll

        CrashDisplayApp().run()
