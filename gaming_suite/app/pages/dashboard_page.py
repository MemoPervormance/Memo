import platform
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QGridLayout, QFrame, QScrollArea, QPushButton)
from PyQt6.QtGui import (QPainter, QColor, QPen, QLinearGradient,
                         QBrush, QFont, QRadialGradient)
from PyQt6.QtCore import Qt, QTimer, QRectF, QPropertyAnimation, pyqtProperty

from app.components.glass_card import GlassCard
from app.components.glow_label import GlowLabel
from app.components.stat_widget import ArcGauge
from app.components.neon_button import NeonButton
from app.core.app_state import get_state

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False


class QuickStatCard(GlassCard):
    """Single stat card: icon, value, label."""

    def __init__(self, icon: str, label: str, unit: str = "",
                 accent: str = "#00C8FF", parent=None):
        super().__init__(parent, accent=accent, glow=True)
        self._icon = icon
        self._label = label
        self._unit = unit
        self._value = "—"
        self.setFixedHeight(90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(8)
        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI Emoji", 18))
        icon_lbl.setStyleSheet("background: transparent;")
        top.addWidget(icon_lbl)
        top.addStretch()

        self._val_lbl = QLabel("—")
        self._val_lbl.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self._val_lbl.setStyleSheet(f"color: {accent}; background: transparent;")
        top.addWidget(self._val_lbl)

        layout.addLayout(top)

        lbl = QLabel(label)
        lbl.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px; background: transparent;")
        layout.addWidget(lbl)

    def set_value(self, v: str):
        self._val_lbl.setText(v)


class MiniBarGraph(QWidget):
    """Animated mini bar chart for FPS history."""

    def __init__(self, color: str = "#00C8FF", bars: int = 20, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._bars = bars
        self._values = [0.0] * bars
        self.setMinimumHeight(50)

    def push_value(self, v: float):
        self._values = self._values[1:] + [max(0.0, min(100.0, v))]
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        bar_w = max(4, (w - self._bars * 2) // self._bars)
        spacing = (w - bar_w * self._bars) // max(1, self._bars - 1)

        for i, v in enumerate(self._values):
            bh = int(h * v / 100.0)
            x = i * (bar_w + 2)
            y = h - bh
            alpha = int(80 + 175 * (i / self._bars))
            p.setBrush(QColor(self._color.red(), self._color.green(),
                              self._color.blue(), alpha))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(x, y, bar_w, bh, 2, 2)
        p.end()


class ProfileWidget(GlassCard):
    """Current profile display + quick-switch buttons."""

    def __init__(self, parent=None):
        super().__init__(parent, accent="#9B5CF6")
        self._state = get_state()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        lbl = GlowLabel("ACTIVE PROFILE", self, color="#9B5CF6",
                         font_size=11, glow_layers=2)
        lbl.setFixedHeight(20)
        header.addWidget(lbl)
        header.addStretch()

        self._profile_lbl = QLabel(self._state.current_profile)
        self._profile_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._profile_lbl.setStyleSheet("color: #FFFFFF; background: transparent;")
        header.addWidget(self._profile_lbl)
        layout.addLayout(header)

        # quick profile buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        for name in ["Competitive", "Max FPS", "Balanced"]:
            btn = NeonButton(name, self, variant="secondary", accent="#9B5CF6")
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda _, n=name: self._switch(n))
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        self._state.profile_changed.connect(self._on_profile_change)

    def _switch(self, name: str):
        self._state.load_profile(name)

    def _on_profile_change(self, name: str):
        self._profile_lbl.setText(name)


class DashboardPage(QWidget):
    """Main dashboard with system stats and quick overview."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = get_state()

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(20, 16, 20, 24)
        cl.setSpacing(16)
        scroll.setWidget(content)

        # ── header ─────────────────────────────────
        hdr = QHBoxLayout()
        title = GlowLabel("INFINITY HUB", self, color="#00C8FF",
                           font_size=28, glow_layers=5)
        title.setFixedHeight(50)
        hdr.addWidget(title)
        hdr.addStretch()
        sub = QLabel("GAMING OPTIMIZATION SUITE", self)
        sub.setStyleSheet("color: rgba(255,255,255,0.3); font-size: 11px; letter-spacing: 3px; background: transparent;")
        sub.setAlignment(Qt.AlignmentFlag.AlignBottom)
        hdr.addWidget(sub, alignment=Qt.AlignmentFlag.AlignBottom)
        cl.addLayout(hdr)

        # ── quick stat cards ────────────────────────
        stat_row = QHBoxLayout()
        stat_row.setSpacing(12)
        self._cpu_card  = QuickStatCard("⚡", "CPU USAGE",  "%", "#00C8FF")
        self._ram_card  = QuickStatCard("💾", "RAM USAGE",  "%", "#00FFD4")
        self._gpu_card  = QuickStatCard("🎮", "GPU USAGE",  "%", "#9B5CF6")
        self._fps_card  = QuickStatCard("📊", "ESTIMATED FPS", "", "#FF2D78")
        for c in (self._cpu_card, self._ram_card, self._gpu_card, self._fps_card):
            stat_row.addWidget(c)
        cl.addLayout(stat_row)

        # ── gauges + history ─────────────────────────
        gauges_row = QHBoxLayout()
        gauges_row.setSpacing(12)

        gauge_card = GlassCard(self, accent="#00C8FF")
        gauge_lay = QVBoxLayout(gauge_card)
        gauge_lay.setContentsMargins(14, 12, 14, 12)
        gauge_lay.setSpacing(6)
        gauge_hdr = GlowLabel("SYSTEM MONITORS", gauge_card, color="#00C8FF",
                               font_size=11, glow_layers=2)
        gauge_hdr.setFixedHeight(20)
        gauge_lay.addWidget(gauge_hdr)

        gauge_inner = QHBoxLayout()
        gauge_inner.setSpacing(10)
        self._cpu_gauge  = ArcGauge("CPU",  "%", "#00C8FF")
        self._ram_gauge  = ArcGauge("RAM",  "%", "#00FFD4")
        self._gpu_gauge  = ArcGauge("GPU",  "%", "#9B5CF6")
        self._temp_gauge = ArcGauge("TEMP", "°", "#FF6B35")
        for g in (self._cpu_gauge, self._ram_gauge, self._gpu_gauge, self._temp_gauge):
            gauge_inner.addWidget(g)
        gauge_lay.addLayout(gauge_inner)
        gauges_row.addWidget(gauge_card, stretch=2)

        # FPS history
        hist_card = GlassCard(self, accent="#FF2D78")
        hist_lay = QVBoxLayout(hist_card)
        hist_lay.setContentsMargins(14, 12, 14, 12)
        hist_lay.setSpacing(6)
        hist_hdr = GlowLabel("FRAMETIME HISTORY", hist_card, color="#FF2D78",
                              font_size=11, glow_layers=2)
        hist_hdr.setFixedHeight(20)
        hist_lay.addWidget(hist_hdr)
        self._fps_graph = MiniBarGraph(color="#FF2D78", bars=24)
        hist_lay.addWidget(self._fps_graph, stretch=1)
        gauges_row.addWidget(hist_card, stretch=1)

        cl.addLayout(gauges_row)

        # ── profile widget ──────────────────────────
        self._profile_widget = ProfileWidget(self)
        cl.addWidget(self._profile_widget)

        # ── system info card ────────────────────────
        sysinfo_card = GlassCard(self, accent="#00FFD4")
        sysinfo_lay = QVBoxLayout(sysinfo_card)
        sysinfo_lay.setContentsMargins(16, 12, 16, 12)
        sysinfo_lay.setSpacing(8)
        si_hdr = GlowLabel("SYSTEM INFORMATION", sysinfo_card, color="#00FFD4",
                            font_size=11, glow_layers=2)
        si_hdr.setFixedHeight(20)
        sysinfo_lay.addWidget(si_hdr)

        grid = QGridLayout()
        grid.setSpacing(8)
        infos = self._get_system_info()
        for i, (key, val) in enumerate(infos):
            k_lbl = QLabel(key)
            k_lbl.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 12px; background: transparent;")
            v_lbl = QLabel(val)
            v_lbl.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 600; background: transparent;")
            grid.addWidget(k_lbl, i // 2, (i % 2) * 2)
            grid.addWidget(v_lbl, i // 2, (i % 2) * 2 + 1)
        sysinfo_lay.addLayout(grid)
        cl.addWidget(sysinfo_card)

        cl.addStretch()

        # ── timer for stats ─────────────────────────
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_stats)
        self._timer.start(1500)
        self._fps_timer = QTimer(self)
        self._fps_timer.timeout.connect(self._update_fps_history)
        self._fps_timer.start(500)

    def _get_system_info(self) -> list:
        rows = [("OS", platform.system() + " " + platform.release()),
                ("Architecture", platform.machine())]
        if PSUTIL_OK:
            try:
                cpu = platform.processor()
                rows.append(("CPU", cpu[:40] if cpu else "Unknown"))
                vm = psutil.virtual_memory()
                rows.append(("RAM Total", f"{vm.total // (1024**3)} GB"))
                rows.append(("CPU Cores", f"{psutil.cpu_count(logical=False)}P / {psutil.cpu_count()}L"))
                disks = psutil.disk_partitions()
                if disks:
                    u = psutil.disk_usage(disks[0].mountpoint)
                    rows.append(("Drive C:", f"{u.used // (1024**3)}/{u.total // (1024**3)} GB"))
            except Exception:
                pass
        return rows

    def _update_stats(self):
        if not PSUTIL_OK:
            return
        try:
            cpu = psutil.cpu_percent(interval=None)
            vm  = psutil.virtual_memory()
            self._cpu_card.set_value(f"{int(cpu)}%")
            self._ram_card.set_value(f"{int(vm.percent)}%")
            self._gpu_card.set_value("—")
            self._cpu_gauge.set_value(cpu)
            self._ram_gauge.set_value(vm.percent)
        except Exception:
            pass

    def _update_fps_history(self):
        import random
        # Placeholder — real FPS requires game hook
        v = random.uniform(40, 90)
        self._fps_graph.push_value(v)
        self._fps_card.set_value(f"{int(v)}")
