# -*- coding: utf-8 -*-
"""
主窗口模块 v2.0
现代深色主题GUI：工具栏、选项卡、实时检测、统计面板、Matplotlib图表、多种滤波
"""

import os
import cv2
import numpy as np

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QComboBox, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QSplitter, QGroupBox,
    QMessageBox, QStatusBar, QAction, QToolBar, QTabWidget,
    QCheckBox, QSpinBox, QProgressBar, QScrollArea,
    QSizePolicy, QColorDialog, QApplication, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor

# 实时检测防抖延迟（毫秒）
_REALTIME_DEBOUNCE_MS = 600

from ..core import ImageProcessor, CenterlineDetector, DataExporter
from ..utils import convert_cv_to_pixmap, get_supported_formats
from .widgets import ImageLabel, MatplotlibCanvas

# ─────────────────────────────────────────────
#  全局深色主题样式表
# ─────────────────────────────────────────────
_DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #dcdcf0;
    font-family: "Microsoft YaHei UI", "Segoe UI", Arial;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #32325a;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 6px;
    font-weight: bold;
    color: #9090c0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
}
QPushButton {
    background-color: #272750;
    color: #d8d8f8;
    border: 1px solid #44447a;
    border-radius: 5px;
    padding: 5px 14px;
    min-height: 26px;
}
QPushButton:hover { background-color: #383878; border-color: #6060b0; }
QPushButton:pressed { background-color: #1c1c40; }
QPushButton:disabled { color: #555570; border-color: #2a2a50; }
QPushButton#detectBtn {
    background-color: #1a4d30;
    border-color: #2a7a4a;
    color: #a0ffc8;
    font-weight: bold;
    min-height: 32px;
}
QPushButton#detectBtn:hover { background-color: #246640; }
QPushButton#openBtn {
    background-color: #1a2d50;
    border-color: #2a4a8c;
    color: #a0c8ff;
}
QPushButton#openBtn:hover { background-color: #243a68; }
QSlider::groove:horizontal {
    height: 5px;
    background: #272750;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 14px; height: 14px;
    background: #5858c8;
    border-radius: 7px;
    margin: -5px 0;
}
QSlider::sub-page:horizontal { background: #4040a0; border-radius: 3px; }
QComboBox {
    background-color: #272750;
    border: 1px solid #44447a;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 26px;
}
QComboBox QAbstractItemView {
    background-color: #272750;
    border: 1px solid #44447a;
    selection-background-color: #4040a0;
}
QTableWidget {
    background-color: #14142a;
    border: 1px solid #32325a;
    gridline-color: #272750;
    alternate-background-color: #1e1e38;
}
QHeaderView::section {
    background-color: #272750;
    color: #9090d0;
    border: none;
    padding: 5px;
    font-weight: bold;
    border-bottom: 2px solid #4040aa;
}
QTabWidget::pane { border: 1px solid #32325a; background: #1a1a2e; }
QTabBar::tab {
    background: #272750; color: #9090c0;
    border: 1px solid #32325a; border-bottom: none;
    padding: 6px 18px; border-radius: 4px 4px 0 0;
}
QTabBar::tab:selected { background: #383878; color: #ffffff; }
QStatusBar {
    background-color: #111122;
    color: #8888b0;
    border-top: 1px solid #32325a;
}
QProgressBar {
    border: 1px solid #32325a;
    border-radius: 4px;
    background: #272750;
    text-align: center;
    max-height: 14px;
    min-width: 120px;
}
QProgressBar::chunk { background: #4040b0; border-radius: 4px; }
QToolBar {
    background: #111122;
    border-bottom: 1px solid #32325a;
    spacing: 2px;
    padding: 3px;
}
QToolBar QToolButton {
    background: #272750;
    border: 1px solid #44447a;
    border-radius: 4px;
    padding: 4px 10px;
    color: #c0c0e8;
}
QToolBar QToolButton:hover { background: #383878; }
QScrollBar:vertical {
    border: none; background: #1a1a2e; width: 8px; border-radius: 4px;
}
QScrollBar::handle:vertical { background: #32325a; border-radius: 4px; }
QCheckBox::indicator {
    width: 15px; height: 15px;
    border: 1px solid #44447a; border-radius: 3px; background: #272750;
}
QCheckBox::indicator:checked { background: #4040aa; border-color: #5858cc; }
QSpinBox {
    background: #272750; border: 1px solid #44447a;
    border-radius: 4px; padding: 3px; min-height: 24px;
}
QFrame[frameShape="4"] { border: none; border-top: 1px solid #32325a; max-height: 1px; }
QScrollArea { border: none; }
"""


class _DetectionWorker(QThread):
    """后台检测线程，避免界面卡顿"""

    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, image: np.ndarray, method: str):
        super().__init__()
        self._image = image.copy()
        self._method = method

    def run(self):
        try:
            detector = CenterlineDetector()
            points = detector.detect(self._image, self._method)
            self.finished.emit(points)
        except Exception as exc:
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    """主窗口类 v2.0"""

    def __init__(self):
        """初始化主窗口"""
        super().__init__()

        # 核心模块
        self.image_processor = ImageProcessor()
        self.centerline_detector = CenterlineDetector()
        self.data_exporter = DataExporter()

        # 状态
        self.current_file = None
        self.centerline_color = (0, 255, 0)  # BGR 格式
        self._worker = None

        self.init_ui()
        self.setStyleSheet(_DARK_STYLE)

    # ─────────────────────────────────────────────
    #  界面构建
    # ─────────────────────────────────────────────

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("激光中心线检测软件  v2.0")
        self.setGeometry(60, 60, 1600, 960)

        self._create_menu_bar()
        self._create_toolbar()

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(6, 4, 6, 4)
        root.setSpacing(6)

        left = self._create_view_tabs()
        right = self._create_control_panel()
        right.setFixedWidth(310)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)

        root.addWidget(splitter)

        # 状态栏
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_lbl = QLabel("就绪 — 请打开图像文件")
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        self._info_lbl = QLabel("")
        sb.addWidget(self._status_lbl, 1)
        sb.addPermanentWidget(self._progress)
        sb.addPermanentWidget(self._info_lbl)

    def _create_menu_bar(self):
        """创建菜单栏"""
        mb = self.menuBar()

        # 文件菜单
        fm = mb.addMenu("文件(&F)")
        for name, shortcut, slot in [
            ("打开图像(&O)", "Ctrl+O", self.open_image),
            ("保存结果图像(&S)", "Ctrl+S", self.save_result_image),
            (None, None, None),
            ("导出 CSV(&E)", "Ctrl+E", self.export_csv),
            ("导出 Excel(&X)", "Ctrl+Shift+E", self.export_excel),
            (None, None, None),
            ("退出(&Q)", "Ctrl+Q", self.close),
        ]:
            if name is None:
                fm.addSeparator()
            else:
                act = QAction(name, self)
                act.setShortcut(shortcut)
                act.triggered.connect(slot)
                fm.addAction(act)

        # 视图菜单
        vm = mb.addMenu("视图(&V)")
        for name, shortcut, slot in [
            ("放大 (+)", "Ctrl+=", self.zoom_in),
            ("缩小 (-)", "Ctrl+-", self.zoom_out),
            ("重置缩放", "Ctrl+0", self.zoom_reset),
        ]:
            act = QAction(name, self)
            act.setShortcut(shortcut)
            act.triggered.connect(slot)
            vm.addAction(act)

        # 帮助菜单
        hm = mb.addMenu("帮助(&H)")
        about = QAction("关于(&A)", self)
        about.triggered.connect(self.show_about)
        hm.addAction(about)

    def _create_toolbar(self):
        """创建工具栏"""
        tb = QToolBar("主工具栏")
        tb.setMovable(False)
        self.addToolBar(tb)

        for label, slot in [
            ("📂 打开图像", self.open_image),
            ("💾 保存结果", self.save_result_image),
            ("📊 导出CSV", self.export_csv),
            (None, None),
            ("🔍 检测中心线", self.detect_centerline),
            ("↩ 重置", self.reset_image),
            (None, None),
            ("🔎+", self.zoom_in),
            ("🔎-", self.zoom_out),
        ]:
            if label is None:
                tb.addSeparator()
            else:
                act = QAction(label, self)
                act.triggered.connect(slot)
                tb.addAction(act)

    def _create_view_tabs(self) -> QTabWidget:
        """创建主内容选项卡"""
        self._tabs = QTabWidget()

        # ── 选项卡 1：图像视图 ──
        img_tab = QWidget()
        img_layout = QHBoxLayout(img_tab)
        img_layout.setContentsMargins(4, 4, 4, 4)
        img_layout.setSpacing(4)

        orig_grp = QGroupBox("原始图像")
        orig_lay = QVBoxLayout(orig_grp)
        orig_lay.setContentsMargins(4, 10, 4, 4)
        self.original_image_label = ImageLabel()
        orig_lay.addWidget(self.original_image_label)

        result_grp = QGroupBox("检测结果")
        result_lay = QVBoxLayout(result_grp)
        result_lay.setContentsMargins(4, 10, 4, 4)
        self.result_image_label = ImageLabel()
        result_lay.addWidget(self.result_image_label)

        img_split = QSplitter(Qt.Horizontal)
        img_split.addWidget(orig_grp)
        img_split.addWidget(result_grp)
        img_layout.addWidget(img_split)

        # ── 选项卡 2：坐标曲线图表 ──
        plot_tab = QWidget()
        plot_layout = QVBoxLayout(plot_tab)
        plot_layout.setContentsMargins(6, 6, 6, 6)
        self.matplotlib_canvas = MatplotlibCanvas()
        plot_layout.addWidget(self.matplotlib_canvas)

        self._tabs.addTab(img_tab, "📷  图像视图")
        self._tabs.addTab(plot_tab, "📈  坐标曲线")

        return self._tabs

    def _create_control_panel(self) -> QScrollArea:
        """创建右侧控制面板"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(10)

        # ── 预处理 ──
        preproc_grp = QGroupBox("图像预处理")
        preproc_lay = QVBoxLayout(preproc_grp)
        preproc_lay.setSpacing(6)

        # 滤波类型
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("滤波方式:"))
        self._filter_combo = QComboBox()
        self._filter_combo.addItem("高斯滤波", "gaussian")
        self._filter_combo.addItem("中值滤波", "median")
        self._filter_combo.addItem("双边滤波", "bilateral")
        filter_row.addWidget(self._filter_combo)
        preproc_lay.addLayout(filter_row)

        # 核大小
        k_row = QHBoxLayout()
        k_row.addWidget(QLabel("核大小:"))
        self._kernel_slider = QSlider(Qt.Horizontal)
        self._kernel_slider.setRange(1, 21)
        self._kernel_slider.setValue(5)
        self._kernel_slider.setTickInterval(2)
        self._kernel_lbl = QLabel("5")
        self._kernel_lbl.setMinimumWidth(22)
        self._kernel_slider.valueChanged.connect(self._on_kernel_changed)
        k_row.addWidget(self._kernel_slider)
        k_row.addWidget(self._kernel_lbl)
        preproc_lay.addLayout(k_row)

        # 阈值（0 = Otsu自动）
        t_row = QHBoxLayout()
        t_row.addWidget(QLabel("阈值:"))
        self._thresh_slider = QSlider(Qt.Horizontal)
        self._thresh_slider.setRange(0, 255)
        self._thresh_slider.setValue(0)
        self._thresh_lbl = QLabel("自动")
        self._thresh_lbl.setMinimumWidth(36)
        self._thresh_slider.valueChanged.connect(self._on_thresh_changed)
        t_row.addWidget(self._thresh_slider)
        t_row.addWidget(self._thresh_lbl)
        preproc_lay.addLayout(t_row)

        # CLAHE 增强
        self._clahe_chk = QCheckBox("CLAHE 自适应对比度增强")
        preproc_lay.addWidget(self._clahe_chk)

        self._preprocess_btn = QPushButton("应用预处理")
        self._preprocess_btn.clicked.connect(self.apply_preprocessing)
        preproc_lay.addWidget(self._preprocess_btn)

        layout.addWidget(preproc_grp)

        # ── 检测设置 ──
        detect_grp = QGroupBox("检测算法与显示")
        detect_lay = QVBoxLayout(detect_grp)
        detect_lay.setSpacing(6)

        self._algo_combo = QComboBox()
        self._algo_combo.addItem("灰度重心法  (通用)", CenterlineDetector.METHOD_GRAY_CENTROID)
        self._algo_combo.addItem("高斯拟合法  (高精度)", CenterlineDetector.METHOD_GAUSSIAN_FITTING)
        self._algo_combo.addItem("极值法  (高速)", CenterlineDetector.METHOD_MAX_VALUE)
        self._algo_combo.addItem("Steger亚像素法  (最高精度)", CenterlineDetector.METHOD_STEGER)
        detect_lay.addWidget(self._algo_combo)

        vis_row = QHBoxLayout()
        vis_row.addWidget(QLabel("线宽:"))
        self._thick_spin = QSpinBox()
        self._thick_spin.setRange(1, 8)
        self._thick_spin.setValue(2)
        vis_row.addWidget(self._thick_spin)

        self._color_btn = QPushButton("● 绿色")
        self._color_btn.setStyleSheet("color: #00ff00;")
        self._color_btn.clicked.connect(self._choose_color)
        vis_row.addWidget(self._color_btn)
        detect_lay.addLayout(vis_row)

        self._realtime_chk = QCheckBox("实时检测（参数变化自动执行）")
        detect_lay.addWidget(self._realtime_chk)

        self._detect_btn = QPushButton("🔍  检测中心线")
        self._detect_btn.setObjectName("detectBtn")
        self._detect_btn.clicked.connect(self.detect_centerline)
        detect_lay.addWidget(self._detect_btn)

        self._reset_btn = QPushButton("↩  重置图像")
        self._reset_btn.clicked.connect(self.reset_image)
        detect_lay.addWidget(self._reset_btn)

        layout.addWidget(detect_grp)

        # ── 统计信息 ──
        stats_grp = QGroupBox("检测统计")
        stats_lay = QVBoxLayout(stats_grp)
        stats_lay.setSpacing(3)
        self._stat_labels = {}
        for key, text in [
            ("points", "检测点数"),
            ("ymin", "Y 最小值"),
            ("ymax", "Y 最大值"),
            ("ymean", "Y 均值"),
            ("ystd", "Y 标准差"),
        ]:
            lbl = QLabel(f"{text}: —")
            lbl.setStyleSheet("color: #9090c0; font-size: 12px;")
            stats_lay.addWidget(lbl)
            self._stat_labels[key] = (text, lbl)
        layout.addWidget(stats_grp)

        # ── 坐标数据表格 ──
        table_grp = QGroupBox("中心线坐标数据")
        table_lay = QVBoxLayout(table_grp)
        table_lay.setContentsMargins(4, 10, 4, 4)
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(3)
        self.data_table.setHorizontalHeaderLabels(["序号", "X坐标", "Y坐标"])
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.setMinimumHeight(180)
        table_lay.addWidget(self.data_table)

        copy_btn = QPushButton("复制全部到剪贴板")
        copy_btn.clicked.connect(self._copy_table)
        table_lay.addWidget(copy_btn)
        layout.addWidget(table_grp)

        layout.addStretch()
        scroll.setWidget(panel)
        return scroll

    # ─────────────────────────────────────────────
    #  槽函数 & 逻辑
    # ─────────────────────────────────────────────

    def _on_kernel_changed(self, value):
        """核大小滑块改变（确保奇数）"""
        if value % 2 == 0:
            value += 1
            self._kernel_slider.setValue(value)
        self._kernel_lbl.setText(str(value))
        self._schedule_realtime()

    def _on_thresh_changed(self, value):
        """阈值滑块改变"""
        self._thresh_lbl.setText("自动" if value == 0 else str(value))
        self._schedule_realtime()

    def _schedule_realtime(self):
        """防抖实时检测调度"""
        if not self._realtime_chk.isChecked():
            return
        if not hasattr(self, '_rt_timer'):
            self._rt_timer = QTimer(self)
            self._rt_timer.setSingleShot(True)
            self._rt_timer.timeout.connect(self._realtime_run)
        self._rt_timer.start(_REALTIME_DEBOUNCE_MS)

    def _realtime_run(self):
        """实时检测：静默应用预处理并检测"""
        if self.image_processor.gray_image is not None:
            self.apply_preprocessing(silent=True)
            self.detect_centerline(silent=True)

    # ── 文件操作 ──

    def open_image(self):
        """打开图像文件"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图像文件", "", get_supported_formats()
        )
        if not path:
            return
        if self.image_processor.load_image(path):
            self.current_file = path
            img = self.image_processor.get_image('original')
            self.original_image_label.setPixmap(convert_cv_to_pixmap(img))
            self.result_image_label.clear()
            self.data_table.setRowCount(0)
            self.matplotlib_canvas.clear_plot()
            self._update_stats(None)
            h, w = img.shape[:2]
            self._set_status(f"已加载: {os.path.basename(path)}")
            self._info_lbl.setText(f"  {w} × {h} px")
        else:
            QMessageBox.warning(self, "错误", "无法加载图像文件！\n请检查文件格式是否受支持。")

    def apply_preprocessing(self, silent=False):
        """应用图像预处理"""
        if self.image_processor.gray_image is None:
            if not silent:
                QMessageBox.warning(self, "警告", "请先加载图像！")
            return

        # 从灰度图开始重置
        self.image_processor.reset()

        # CLAHE 增强
        if self._clahe_chk.isChecked():
            self.image_processor.apply_clahe()

        # 滤波
        k = self._kernel_slider.value()
        ftype = self._filter_combo.currentData()
        if ftype == "gaussian":
            self.image_processor.apply_gaussian_filter(k)
        elif ftype == "median":
            self.image_processor.apply_median_filter(k)
        elif ftype == "bilateral":
            self.image_processor.apply_bilateral_filter(k)

        # 阈值
        t = self._thresh_slider.value()
        if t == 0:
            self.image_processor.apply_threshold_otsu()
        else:
            self.image_processor.apply_threshold(t)

        if not silent:
            self._set_status("预处理已应用")

    def detect_centerline(self, silent=False):
        """检测激光中心线（后台线程）"""
        if self.image_processor.processed_image is None:
            if not silent:
                QMessageBox.warning(self, "警告", "请先加载图像！")
            return

        if self._worker and self._worker.isRunning():
            return  # 避免重复启动

        method = self._algo_combo.currentData()
        self._set_status("正在检测中心线…")
        self._progress.setVisible(True)
        self._detect_btn.setEnabled(False)

        self._worker = _DetectionWorker(
            self.image_processor.processed_image, method
        )
        self._worker.finished.connect(self._on_detect_done)
        self._worker.error.connect(self._on_detect_error)
        self._worker.start()

    def _on_detect_done(self, points):
        """检测完成回调"""
        self._progress.setVisible(False)
        self._detect_btn.setEnabled(True)

        if not points:
            self._set_status("未检测到中心线，请调整预处理参数")
            return

        # 在原图上绘制中心线（同步到主线程的 centerline_detector）
        self.centerline_detector.centerline_points = points
        result = self.centerline_detector.draw_centerline(
            self.image_processor.get_image('original').copy(),
            color=self.centerline_color,
            thickness=self._thick_spin.value()
        )
        self.result_image_label.setPixmap(convert_cv_to_pixmap(result))

        # 更新表格 / 统计 / 图表
        self._fill_table(points)
        self._update_stats(points)
        self.matplotlib_canvas.plot_centerline(points)

        self._set_status(f"检测完成 — 共 {len(points)} 个点")
        self._tabs.setCurrentIndex(0)

    def _on_detect_error(self, msg):
        """检测出错回调"""
        self._progress.setVisible(False)
        self._detect_btn.setEnabled(True)
        self._set_status(f"检测失败: {msg}")

    def _fill_table(self, points):
        """填充坐标数据表格"""
        self.data_table.setRowCount(len(points))
        for i, (x, y) in enumerate(points):
            self.data_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.data_table.setItem(i, 1, QTableWidgetItem(str(x)))
            self.data_table.setItem(i, 2, QTableWidgetItem(f"{y:.3f}"))

    def _update_stats(self, points):
        """更新统计信息面板"""
        if not points:
            for key, (text, lbl) in self._stat_labels.items():
                lbl.setText(f"{text}: —")
            return
        ys = np.array([p[1] for p in points])
        values = {
            "points": str(len(points)),
            "ymin": f"{ys.min():.3f}",
            "ymax": f"{ys.max():.3f}",
            "ymean": f"{ys.mean():.3f}",
            "ystd": f"{ys.std():.3f}",
        }
        for key, (text, lbl) in self._stat_labels.items():
            lbl.setText(f"{text}: {values[key]}")

    def reset_image(self):
        """重置为原始灰度图"""
        if self.image_processor.gray_image is None:
            return
        self.image_processor.reset()
        self.result_image_label.clear()
        self.data_table.setRowCount(0)
        self.matplotlib_canvas.clear_plot()
        self._update_stats(None)
        self._set_status("已重置")

    def save_result_image(self):
        """保存结果图像"""
        if self.result_image_label.pixmap() is None:
            QMessageBox.warning(self, "警告", "没有可保存的结果图像！")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存结果图像", "",
            "PNG 图像 (*.png);;JPEG 图像 (*.jpg);;所有文件 (*.*)"
        )
        if path:
            result = self.centerline_detector.draw_centerline(
                self.image_processor.get_image('original').copy(),
                color=self.centerline_color,
                thickness=self._thick_spin.value()
            )
            if cv2.imwrite(path, result):
                self._set_status(f"图像已保存: {os.path.basename(path)}")
            else:
                QMessageBox.warning(self, "错误", "保存图像失败！")

    def export_csv(self):
        """导出CSV文件"""
        points = self.centerline_detector.get_centerline_points()
        if not points:
            QMessageBox.warning(self, "警告", "没有可导出的数据，请先检测中心线！")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", "", "CSV 文件 (*.csv);;所有文件 (*.*)"
        )
        if path:
            if self.data_exporter.export_to_csv(points, path):
                self._set_status(f"CSV 已导出: {os.path.basename(path)}")
            else:
                QMessageBox.warning(self, "错误", "导出 CSV 失败！")

    def export_excel(self):
        """导出Excel文件"""
        points = self.centerline_detector.get_centerline_points()
        if not points:
            QMessageBox.warning(self, "警告", "没有可导出的数据，请先检测中心线！")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 Excel", "", "Excel 文件 (*.xlsx);;所有文件 (*.*)"
        )
        if path:
            if self.data_exporter.export_to_excel(points, path):
                self._set_status(f"Excel 已导出: {os.path.basename(path)}")
            else:
                QMessageBox.warning(self, "错误", "导出 Excel 失败！\n请确认已安装 openpyxl：pip install openpyxl")

    def _choose_color(self):
        """选择中心线颜色"""
        b, g, r = self.centerline_color
        initial = QColor(r, g, b)
        color = QColorDialog.getColor(initial, self, "选择中心线颜色")
        if color.isValid():
            self.centerline_color = (color.blue(), color.green(), color.red())
            self._color_btn.setStyleSheet(f"color: {color.name()};")
            self._color_btn.setText(f"● {color.name()}")

    def _copy_table(self):
        """将坐标数据复制到剪贴板"""
        points = self.centerline_detector.get_centerline_points()
        if not points:
            return
        lines = ["序号\tX坐标\tY坐标"] + [
            f"{i + 1}\t{x}\t{y:.3f}" for i, (x, y) in enumerate(points)
        ]
        QApplication.clipboard().setText("\n".join(lines))
        self._set_status(f"已复制 {len(points)} 行数据到剪贴板")

    def zoom_in(self):
        """放大图像"""
        for lbl in (self.original_image_label, self.result_image_label):
            lbl._zoom_factor = min(lbl._zoom_factor * 1.2, 6.0)
            lbl._update_scaled_pixmap()

    def zoom_out(self):
        """缩小图像"""
        for lbl in (self.original_image_label, self.result_image_label):
            lbl._zoom_factor = max(lbl._zoom_factor / 1.2, 0.1)
            lbl._update_scaled_pixmap()

    def zoom_reset(self):
        """重置缩放比例"""
        for lbl in (self.original_image_label, self.result_image_label):
            lbl._zoom_factor = 1.0
            lbl._update_scaled_pixmap()

    def _set_status(self, msg: str):
        """更新状态栏文字"""
        self._status_lbl.setText(msg)

    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self, "关于  激光中心线检测软件 v2.0",
            "<h3>激光中心线检测软件  v2.0</h3>"
            "<p>基于 <b>Python 3 + PyQt5 + OpenCV + Matplotlib</b> 开发</p>"
            "<hr>"
            "<p><b>支持的检测算法：</b></p>"
            "<ul>"
            "<li><b>灰度重心法</b> — 灰度加权平均，鲁棒性强，适合大多数场景</li>"
            "<li><b>高斯拟合法</b> — 对灰度分布进行高斯曲线拟合，精度高</li>"
            "<li><b>极值法</b> — 取每列最大灰度值，速度最快</li>"
            "<li><b>Steger 亚像素法</b> — 基于 Hessian 矩阵特征值分析，亚像素精度</li>"
            "</ul>"
            "<p><b>新功能 v2.0：</b></p>"
            "<ul>"
            "<li>中值滤波 / 双边滤波 / CLAHE 对比度增强</li>"
            "<li>Otsu 自动阈值分割</li>"
            "<li>后台线程检测，界面不卡顿</li>"
            "<li>实时检测模式</li>"
            "<li>Matplotlib 坐标曲线可视化</li>"
            "<li>鼠标滚轮缩放图像</li>"
            "<li>检测统计信息面板</li>"
            "<li>支持导出 CSV 和 Excel（含统计工作表）</li>"
            "<li>自定义中心线颜色与线宽</li>"
            "</ul>"
        )
