# -*- coding: utf-8 -*-
"""
laserline.ui.panels — 右侧控制面板组件
拆分为独立模块，方便维护。
"""

from __future__ import annotations

import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QComboBox, QPushButton, QCheckBox, QSpinBox,
    QColorDialog, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QApplication, QSizePolicy
)

from ..detection.engine import Algorithm, PreprocessConfig
from .widgets import ParameterGroup


class PreprocessPanel(QWidget):
    """图像预处理参数面板，发射 changed 信号。"""

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── 滤波类型 ──
        grp_filter = ParameterGroup("滤波设置")
        layout.addWidget(grp_filter)
        inner = grp_filter.inner_layout()

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("类型:"))
        self.combo_filter = QComboBox()
        for text, val in [
            ("高斯滤波", "gaussian"),
            ("中值滤波", "median"),
            ("双边滤波", "bilateral"),
            ("不滤波",   "none"),
        ]:
            self.combo_filter.addItem(text, val)
        row1.addWidget(self.combo_filter)
        inner.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("核大小:"))
        self.sld_kernel = QSlider(Qt.Horizontal)
        self.sld_kernel.setRange(1, 21)
        self.sld_kernel.setValue(5)
        self.sld_kernel.setSingleStep(2)
        self.lbl_kernel = QLabel("5")
        self.lbl_kernel.setMinimumWidth(22)
        self.sld_kernel.valueChanged.connect(self._on_kernel_changed)
        row2.addWidget(self.sld_kernel)
        row2.addWidget(self.lbl_kernel)
        inner.addLayout(row2)

        # ── 阈值 ──
        grp_thr = ParameterGroup("阈值设置")
        layout.addWidget(grp_thr)
        inner2 = grp_thr.inner_layout()

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("阈值:"))
        self.sld_thresh = QSlider(Qt.Horizontal)
        self.sld_thresh.setRange(0, 255)
        self.sld_thresh.setValue(0)
        self.lbl_thresh = QLabel("自动(Otsu)")
        self.lbl_thresh.setMinimumWidth(80)
        self.sld_thresh.valueChanged.connect(self._on_thresh_changed)
        row3.addWidget(self.sld_thresh)
        row3.addWidget(self.lbl_thresh)
        inner2.addLayout(row3)

        self.chk_clahe = QCheckBox("CLAHE 自适应对比度增强")
        inner2.addWidget(self.chk_clahe)

        # 信号连接
        for w in (self.combo_filter, self.chk_clahe):
            if isinstance(w, QComboBox):
                w.currentIndexChanged.connect(self.changed)
            else:
                w.stateChanged.connect(self.changed)

    def _on_kernel_changed(self, v):
        if v % 2 == 0:
            v += 1
            self.sld_kernel.setValue(v)
        self.lbl_kernel.setText(str(v))
        self.changed.emit()

    def _on_thresh_changed(self, v):
        self.lbl_thresh.setText("自动(Otsu)" if v == 0 else str(v))
        self.changed.emit()

    def get_config(self) -> PreprocessConfig:
        return PreprocessConfig(
            filter_type=self.combo_filter.currentData(),
            kernel_size=self.sld_kernel.value(),
            threshold=self.sld_thresh.value(),
            clahe=self.chk_clahe.isChecked(),
        )


class DetectionPanel(QWidget):
    """检测算法与可视化设置面板。"""

    detect_requested = pyqtSignal()
    reset_requested  = pyqtSignal()
    color_changed    = pyqtSignal(list)   # [R, G, B]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── 算法 ──
        grp_algo = ParameterGroup("检测算法")
        layout.addWidget(grp_algo)
        inner = grp_algo.inner_layout()

        self.combo_algo = QComboBox()
        names = Algorithm.display_names()
        for algo in Algorithm:
            self.combo_algo.addItem(names[algo.value], algo.value)
        inner.addWidget(self.combo_algo)

        # ── 可视化 ──
        grp_vis = ParameterGroup("可视化设置")
        layout.addWidget(grp_vis)
        inner2 = grp_vis.inner_layout()

        row_vis = QHBoxLayout()
        row_vis.addWidget(QLabel("线宽:"))
        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 10)
        self.spin_width.setValue(2)
        row_vis.addWidget(self.spin_width)
        row_vis.addStretch()
        self.btn_color = QPushButton("● 颜色")
        self.btn_color.setStyleSheet("color: #00dc50; min-width:60px;")
        self._rgb = [0, 220, 80]
        self.btn_color.clicked.connect(self._pick_color)
        row_vis.addWidget(self.btn_color)
        inner2.addLayout(row_vis)

        # ── 操作按钮 ──
        self.btn_detect = QPushButton("▶  立即检测")
        self.btn_detect.setObjectName("btnDetect")
        self.btn_detect.setMinimumHeight(34)
        self.btn_detect.clicked.connect(self.detect_requested)
        layout.addWidget(self.btn_detect)

        self.btn_reset = QPushButton("↩  重置图像")
        self.btn_reset.clicked.connect(self.reset_requested)
        layout.addWidget(self.btn_reset)

    def _pick_color(self):
        r, g, b = self._rgb
        c = QColorDialog.getColor(QColor(r, g, b), self, "选择中心线颜色")
        if c.isValid():
            self._rgb = [c.red(), c.green(), c.blue()]
            self.btn_color.setStyleSheet(f"color: {c.name()}; min-width:60px;")
            self.color_changed.emit(self._rgb)

    def get_algorithm(self) -> str:
        return self.combo_algo.currentData()

    def get_color_bgr(self) -> tuple:
        r, g, b = self._rgb
        return (b, g, r)

    def get_line_width(self) -> int:
        return self.spin_width.value()


class StatsPanel(QWidget):
    """检测统计信息面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        grp = ParameterGroup("检测统计")
        layout.addWidget(grp)
        inner = grp.inner_layout()

        style = "color:#9090c0; font-size:12px; padding:1px 0;"
        self._labels = {}
        for key, text in [
            ("n",    "检测点数"),
            ("ymin", "Y 最小值"),
            ("ymax", "Y 最大值"),
            ("mean", "Y 均值"),
            ("std",  "Y 标准差"),
            ("ms",   "耗时 (ms)"),
        ]:
            lbl = QLabel(f"{text}: —")
            lbl.setStyleSheet(style)
            inner.addWidget(lbl)
            self._labels[key] = (text, lbl)

    def update(self, result=None):
        if result is None or not result.is_valid():
            for key, (text, lbl) in self._labels.items():
                lbl.setText(f"{text}: —")
            return
        vals = {
            "n":    str(result.count),
            "ymin": f"{result.y_min:.3f}",
            "ymax": f"{result.y_max:.3f}",
            "mean": f"{result.y_mean:.3f}",
            "std":  f"{result.y_std:.3f}",
            "ms":   f"{result.elapsed_ms:.1f}",
        }
        for key, (text, lbl) in self._labels.items():
            lbl.setText(f"{text}: {vals[key]}")


class DataTablePanel(QWidget):
    """坐标数据表格面板，含复制到剪贴板按钮。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        grp = ParameterGroup("中心线坐标数据")
        layout.addWidget(grp)
        inner = grp.inner_layout()

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["序号", "X坐标", "Y坐标"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMinimumHeight(160)
        inner.addWidget(self.table)

        self.btn_copy = QPushButton("复制全部到剪贴板")
        self.btn_copy.clicked.connect(self._copy)
        inner.addWidget(self.btn_copy)

    def fill(self, points):
        self.table.setRowCount(len(points))
        for i, (x, y) in enumerate(points):
            self.table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(i, 1, QTableWidgetItem(str(x)))
            self.table.setItem(i, 2, QTableWidgetItem(f"{y:.4f}"))

    def clear(self):
        self.table.setRowCount(0)

    def _copy(self):
        rows = self.table.rowCount()
        if rows == 0:
            return
        lines = ["序号\tX坐标\tY坐标"]
        for i in range(rows):
            lines.append("\t".join(
                self.table.item(i, j).text() for j in range(3)
            ))
        QApplication.clipboard().setText("\n".join(lines))
