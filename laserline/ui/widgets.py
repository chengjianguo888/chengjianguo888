# -*- coding: utf-8 -*-
"""
laserline.ui.widgets — 可复用 UI 控件

• ZoomImageLabel  — 支持鼠标滚轮缩放与拖拽平移的图像标签
• PlotCanvas      — 嵌入 Qt 的 Matplotlib 画布（可显示坐标曲线/直方图）
• ParameterGroup  — 带标题的参数分组控件
"""

from __future__ import annotations

import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QPixmap, QCursor
from PyQt5.QtWidgets import (
    QLabel, QSizePolicy, QGroupBox, QVBoxLayout
)

try:
    import matplotlib
    matplotlib.use("Qt5Agg")
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
    _MPL_OK = True
except Exception:
    _MPL_OK = False


# ─────────────────────────────────────────────────────────
class ZoomImageLabel(QLabel):
    """
    支持鼠标滚轮缩放和拖拽平移的图像显示控件。
    双击可重置到适合窗口大小。
    """

    zoom_changed = pyqtSignal(float)   # 缩放比例变更信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            "background:#0d0d1e; border:1px solid #2a2a5a;"
        )
        self.setMinimumSize(200, 150)
        self.setAcceptDrops(True)

        self._pix: QPixmap | None = None
        self._zoom = 1.0
        self._drag_start: QPoint | None = None

    # ── 公开 API ──────────────────────────────────

    def set_image(self, pixmap: QPixmap) -> None:
        """设置要显示的图像并重置缩放。"""
        self._pix = pixmap
        self._zoom = 1.0
        self._repaint()

    def clear_image(self) -> None:
        self._pix = None
        self.clear()

    def zoom_factor(self) -> float:
        return self._zoom

    def set_zoom(self, factor: float) -> None:
        self._zoom = max(0.05, min(factor, 8.0))
        self._repaint()
        self.zoom_changed.emit(self._zoom)

    def reset_zoom(self) -> None:
        self._zoom = 1.0
        self._offset = QPoint(0, 0)
        self._repaint()

    # ── 内部绘制 ──────────────────────────────────

    def _repaint(self) -> None:
        if self._pix is None:
            return
        w = int(self._pix.width()  * self._zoom)
        h = int(self._pix.height() * self._zoom)
        scaled = self._pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        super().setPixmap(scaled)

    # ── 事件处理 ──────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._repaint()

    def wheelEvent(self, event):
        if self._pix is None:
            return
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        self.set_zoom(self._zoom * factor)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.reset_zoom()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._pix is not None:
            self._drag_start = event.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        self.setCursor(QCursor(Qt.ArrowCursor))
        super().mouseReleaseEvent(event)


# ─────────────────────────────────────────────────────────
if _MPL_OK:
    class PlotCanvas(FigureCanvasQTAgg):
        """嵌入 Qt 的 Matplotlib 画布，深色风格。"""

        # 配色常量
        BG_FIGURE  = "#0d0d1e"
        BG_AXES    = "#13132a"
        COLOR_LINE = "#00e5a0"
        COLOR_HIST = "#5080ff"
        COLOR_TEXT = "#c0c0e0"
        COLOR_GRID = "#252550"

        def __init__(self, parent=None):
            fig = Figure(figsize=(6, 3.5), tight_layout=True)
            fig.patch.set_facecolor(self.BG_FIGURE)
            super().__init__(fig)
            self.setParent(parent)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.setMinimumHeight(220)
            self._ax = fig.add_subplot(111)
            self._style_axes(self._ax)
            self._draw_placeholder()

        def _style_axes(self, ax) -> None:
            ax.set_facecolor(self.BG_AXES)
            ax.tick_params(colors=self.COLOR_TEXT, labelsize=8)
            for sp in ax.spines.values():
                sp.set_color("#333366")
            ax.grid(True, color=self.COLOR_GRID, linestyle="--", alpha=0.5)

        def _draw_placeholder(self) -> None:
            ax = self._ax
            ax.clear()
            self._style_axes(ax)
            ax.text(0.5, 0.5, "（加载图像后显示坐标曲线）",
                    transform=ax.transAxes, ha="center", va="center",
                    color="#505080", fontsize=11)
            self.draw()

        def plot_centerline(self, points, title: str = "激光中心线 Y 坐标分布") -> None:
            """绘制中心线折线图。"""
            ax = self._ax
            ax.clear()
            self._style_axes(ax)
            if not points:
                self._draw_placeholder()
                return
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            ax.plot(xs, ys, "-", color=self.COLOR_LINE,
                    linewidth=1.2, alpha=0.9, label=f"{len(points)} 个点")
            ax.fill_between(xs, ys, alpha=0.12, color=self.COLOR_LINE)
            ax.invert_yaxis()
            ax.set_xlabel("X (像素)", color=self.COLOR_TEXT, fontsize=9)
            ax.set_ylabel("Y (像素)", color=self.COLOR_TEXT, fontsize=9)
            ax.set_title(title, color="#ffffff", fontsize=10, pad=6)
            ax.legend(loc="upper right", fontsize=8,
                      facecolor=self.BG_AXES, edgecolor="#333366",
                      labelcolor=self.COLOR_TEXT)
            self.draw()

        def plot_histogram(self, points, bins: int = 50) -> None:
            """绘制 Y 坐标直方图。"""
            ax = self._ax
            ax.clear()
            self._style_axes(ax)
            if not points:
                self._draw_placeholder()
                return
            ys = [p[1] for p in points]
            ax.hist(ys, bins=bins, color=self.COLOR_HIST, alpha=0.75,
                    edgecolor=self.BG_AXES)
            ax.set_xlabel("Y 坐标", color=self.COLOR_TEXT, fontsize=9)
            ax.set_ylabel("频次", color=self.COLOR_TEXT, fontsize=9)
            ax.set_title("Y 坐标分布直方图", color="#ffffff", fontsize=10, pad=6)
            self.draw()

        def clear_plot(self) -> None:
            self._draw_placeholder()

else:
    class PlotCanvas(QLabel):
        """Matplotlib 不可用时的占位控件"""
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setText("matplotlib 未安装，无法显示图表")
            self.setAlignment(Qt.AlignCenter)
            self.setStyleSheet("color:#555; font-size:12px;")
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.setMinimumHeight(220)

        def plot_centerline(self, *a, **kw): pass
        def plot_histogram(self, *a, **kw): pass
        def clear_plot(self): pass


# ─────────────────────────────────────────────────────────
class ParameterGroup(QGroupBox):
    """带标题的参数分组容器，自动提供垂直布局。"""

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 14, 8, 8)
        self._layout.setSpacing(6)

    def inner_layout(self) -> QVBoxLayout:
        return self._layout
