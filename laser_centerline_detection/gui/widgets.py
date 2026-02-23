# -*- coding: utf-8 -*-
"""
自定义控件模块
包含可缩放图像标签和Matplotlib嵌入画布
"""

import numpy as np
from PyQt5.QtWidgets import QLabel, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap

try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    _MATPLOTLIB_OK = True
except Exception:
    _MATPLOTLIB_OK = False


class ImageLabel(QLabel):
    """
    可显示图像的标签控件
    支持自适应缩放和鼠标滚轮缩放
    """

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        """初始化图像标签"""
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            "QLabel { background-color: #12122a; border: 1px solid #2a2a50; }"
        )
        self.setMinimumSize(300, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.original_pixmap = None
        self._zoom_factor = 1.0

    def setPixmap(self, pixmap: QPixmap):
        """设置图像并重置缩放比例"""
        self.original_pixmap = pixmap
        self._zoom_factor = 1.0
        self._update_scaled_pixmap()

    def _update_scaled_pixmap(self):
        """根据当前缩放比例更新显示图像"""
        if self.original_pixmap:
            target = self.size() * self._zoom_factor
            scaled = self.original_pixmap.scaled(
                target, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            super().setPixmap(scaled)

    def resizeEvent(self, event):
        """窗口大小改变时自动更新缩放"""
        super().resizeEvent(event)
        self._update_scaled_pixmap()

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        self.clicked.emit()
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        """鼠标滚轮缩放"""
        if event.angleDelta().y() > 0:
            self._zoom_factor = min(self._zoom_factor * 1.15, 6.0)
        else:
            self._zoom_factor = max(self._zoom_factor / 1.15, 0.1)
        self._update_scaled_pixmap()
        event.accept()


if _MATPLOTLIB_OK:
    class MatplotlibCanvas(FigureCanvas):
        """Matplotlib画布，嵌入PyQt5，用于显示中心线坐标曲线"""

        def __init__(self, parent=None):
            """初始化画布"""
            self.fig = Figure(figsize=(6, 4), tight_layout=True)
            self.fig.patch.set_facecolor('#12122a')
            self.axes = self.fig.add_subplot(111)
            self._setup_axes()
            super().__init__(self.fig)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.setMinimumHeight(250)

        def _setup_axes(self):
            """设置坐标轴样式"""
            ax = self.axes
            ax.set_facecolor('#1a1a3a')
            ax.tick_params(colors='#b0b0d0', labelsize=8)
            for spine in ax.spines.values():
                spine.set_color('#3a3a6a')
            ax.set_xlabel('X 坐标 (像素)', color='#c0c0e0', fontsize=9)
            ax.set_ylabel('Y 坐标 (像素)', color='#c0c0e0', fontsize=9)
            ax.set_title('激光中心线坐标分布', color='#ffffff', fontsize=10, pad=8)
            ax.grid(True, alpha=0.25, color='#3a3a6a', linestyle='--')

        def plot_centerline(self, points):
            """
            绘制中心线坐标曲线

            Args:
                points: [(x, y), ...] 坐标点列表
            """
            if not points:
                return
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            self.axes.clear()
            self._setup_axes()
            self.axes.plot(xs, ys, '-', color='#00e676', linewidth=1.5, alpha=0.9,
                           label=f'中心线 ({len(points)} 点)')
            self.axes.fill_between(xs, ys, alpha=0.12, color='#00e676')
            self.axes.invert_yaxis()
            self.axes.legend(loc='upper right', fontsize=8,
                             facecolor='#1a1a3a', edgecolor='#3a3a6a',
                             labelcolor='#c0c0e0')
            self.draw()

        def clear_plot(self):
            """清空画布"""
            self.axes.clear()
            self._setup_axes()
            self.draw()

else:
    class MatplotlibCanvas(QLabel):
        """Matplotlib不可用时的占位控件"""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setText("⚠ matplotlib 未正确安装，无法显示图表\n请运行: pip install matplotlib")
            self.setAlignment(Qt.AlignCenter)
            self.setStyleSheet("color: #888; font-size: 13px;")

        def plot_centerline(self, points):
            pass

        def clear_plot(self):
            pass
