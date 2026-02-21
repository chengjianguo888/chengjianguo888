# -*- coding: utf-8 -*-
"""
laserline.ui.mainwindow — 主窗口

全新架构：
  • Model-View 分离：DetectionEngine 负责纯计算，UI 只负责展示
  • 选项卡：单张检测  /  坐标曲线  /  Y直方图  /  批量处理
  • 工具栏快速操作
  • 后台 QThread 检测，界面不卡顿
  • 配置自动持久化
"""

from __future__ import annotations

import os

import cv2
import numpy as np
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QTabWidget, QLabel, QStatusBar,
    QToolBar, QAction, QMessageBox, QFileDialog,
    QProgressBar, QApplication, QScrollArea
)

from ..detection.engine import Algorithm, DetectionEngine, DetectionResult
from ..io.loader import ImageLoader, QT_FILTER
from ..io.exporter import DataExporter
from .. import config
from .widgets import ZoomImageLabel, PlotCanvas
from .panels import PreprocessPanel, DetectionPanel, StatsPanel, DataTablePanel
from .batch_dialog import BatchDialog


# ─────────────────────────────────────────────────────────
#  深色主题样式表
# ─────────────────────────────────────────────────────────
_STYLE = """
* { font-family: "Microsoft YaHei UI", "Segoe UI", "Noto Sans CJK SC", Arial; font-size:13px; }
QMainWindow, QDialog, QWidget { background:#0e0e20; color:#d8d8f0; }
QGroupBox {
    border:1px solid #2e2e60; border-radius:6px;
    margin-top:10px; padding-top:4px;
    font-weight:bold; color:#8888cc;
}
QGroupBox::title { subcontrol-origin:margin; left:10px; padding:0 6px; }
QPushButton {
    background:#1e1e42; color:#c8c8f0;
    border:1px solid #3e3e80; border-radius:5px;
    padding:5px 14px; min-height:26px;
}
QPushButton:hover  { background:#2e2e60; border-color:#5858b0; }
QPushButton:pressed{ background:#141430; }
QPushButton:disabled{ color:#44446a; border-color:#242450; }
QPushButton#btnDetect {
    background:#0f3320; border-color:#1a6640;
    color:#80ffb8; font-weight:bold; min-height:34px;
}
QPushButton#btnDetect:hover{ background:#1a4430; }
QSlider::groove:horizontal{ height:5px; background:#1e1e42; border-radius:3px; }
QSlider::handle:horizontal{
    width:14px; height:14px; background:#5050cc;
    border-radius:7px; margin:-5px 0;
}
QSlider::sub-page:horizontal{ background:#3838a0; border-radius:3px; }
QComboBox{
    background:#1e1e42; border:1px solid #3e3e80;
    border-radius:4px; padding:4px 8px; min-height:26px;
}
QComboBox QAbstractItemView{
    background:#1e1e42; border:1px solid #3e3e80;
    selection-background-color:#3838a0;
}
QTableWidget{ background:#0a0a18; border:1px solid #2e2e60; gridline-color:#1e1e42; }
QTableWidget::item:alternate{ background:#121228; }
QHeaderView::section{
    background:#1e1e42; color:#8888cc; border:none;
    padding:5px; font-weight:bold;
    border-bottom:2px solid #3838a0;
}
QTabWidget::pane{ border:1px solid #2e2e60; background:#0e0e20; }
QTabBar::tab{
    background:#1e1e42; color:#8888cc;
    border:1px solid #2e2e60; border-bottom:none;
    padding:6px 18px; border-radius:4px 4px 0 0;
}
QTabBar::tab:selected{ background:#2e2e60; color:#fff; }
QStatusBar{ background:#080814; color:#666688; border-top:1px solid #2e2e60; }
QProgressBar{
    border:1px solid #2e2e60; border-radius:4px;
    background:#1e1e42; text-align:center;
    max-height:14px; min-width:100px;
}
QProgressBar::chunk{ background:#3838b0; border-radius:4px; }
QToolBar{
    background:#080814; border-bottom:1px solid #2e2e60;
    spacing:2px; padding:3px;
}
QToolBar QToolButton{
    background:#1e1e42; border:1px solid #3e3e80;
    border-radius:4px; padding:4px 10px; color:#b8b8e0;
}
QToolBar QToolButton:hover{ background:#2e2e60; }
QScrollBar:vertical{
    border:none; background:#0e0e20; width:8px; border-radius:4px;
}
QScrollBar::handle:vertical{ background:#2e2e60; border-radius:4px; }
QCheckBox::indicator{
    width:15px; height:15px;
    border:1px solid #3e3e80; border-radius:3px; background:#1e1e42;
}
QCheckBox::indicator:checked{ background:#3838aa; border-color:#5050cc; }
QSpinBox{
    background:#1e1e42; border:1px solid #3e3e80;
    border-radius:4px; padding:3px; min-height:24px;
}
QLineEdit{
    background:#1e1e42; border:1px solid #3e3e80;
    border-radius:4px; padding:4px; min-height:26px;
}
QTextEdit{ background:#0a0a18; border:1px solid #2e2e60; color:#c0e0c0; }
"""


# ─────────────────────────────────────────────────────────
#  后台检测线程
# ─────────────────────────────────────────────────────────
class _Worker(QThread):
    """在后台线程运行检测，避免 UI 卡顿。"""
    done  = pyqtSignal(object)   # DetectionResult
    error = pyqtSignal(str)

    def __init__(self, engine: DetectionEngine, gray: np.ndarray,
                 algorithm: Algorithm, image_path: str = ""):
        super().__init__()
        self._engine    = engine
        self._gray      = gray.copy()
        self._algorithm = algorithm
        self._path      = image_path

    def run(self):
        try:
            result = self._engine.run(self._gray, self._algorithm, self._path)
            self.done.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


# ─────────────────────────────────────────────────────────
#  主窗口
# ─────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    """激光中心线检测软件 — 全新主窗口"""

    _REALTIME_DELAY_MS = 700   # 实时检测防抖延迟

    def __init__(self):
        super().__init__()

        # ── 核心组件 ──
        self._engine    = DetectionEngine()
        self._exporter  = DataExporter()
        self._cfg       = config.load()
        self._worker: _Worker | None = None

        # ── 状态 ──
        self._original_bgr: np.ndarray | None = None
        self._processed_gray: np.ndarray | None = None
        self._result: DetectionResult | None    = None
        self._current_path: str = ""

        # ── 实时检测定时器 ──
        self._rt_timer = QTimer(self)
        self._rt_timer.setSingleShot(True)
        self._rt_timer.timeout.connect(self._run_detection)

        self._build_ui()
        self.setStyleSheet(_STYLE)
        self._restore_state()

    # ─────────────────────────────────────────────────────
    #  界面构建
    # ─────────────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle("LaserLine — 激光中心线检测软件")
        self.setMinimumSize(1100, 720)
        self.resize(1440, 900)

        self._build_menu()
        self._build_toolbar()

        # 中央区域
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        left  = self._build_left_panel()
        right = self._build_right_panel()
        right.setFixedWidth(320)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        root.addWidget(splitter)

        # 状态栏
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._lbl_status = QLabel("就绪 — 请打开图像文件（Ctrl+O）")
        self._lbl_info   = QLabel("")
        self._pbar = QProgressBar()
        self._pbar.setRange(0, 0)
        self._pbar.setVisible(False)
        sb.addWidget(self._lbl_status, 1)
        sb.addPermanentWidget(self._pbar)
        sb.addPermanentWidget(self._lbl_info)

    def _build_menu(self):
        mb = self.menuBar()

        # 文件
        fm = mb.addMenu("文件(&F)")
        for label, shortcut, slot in [
            ("打开图像(&O)",        "Ctrl+O",        self._open_image),
            ("打开目录批量处理(&B)","Ctrl+B",         self._open_batch),
            (None, None, None),
            ("保存结果图像(&S)",    "Ctrl+S",         self._save_result),
            (None, None, None),
            ("导出 CSV(&E)",        "Ctrl+E",         self._export_csv),
            ("导出 Excel(&X)",      "Ctrl+Shift+E",   self._export_excel),
            ("导出 JSON(&J)",       "Ctrl+Shift+J",   self._export_json),
            (None, None, None),
            ("退出(&Q)",            "Ctrl+Q",          self.close),
        ]:
            if label is None:
                fm.addSeparator()
            else:
                a = QAction(label, self)
                if shortcut:
                    a.setShortcut(shortcut)
                a.triggered.connect(slot)
                fm.addAction(a)

        # 视图
        vm = mb.addMenu("视图(&V)")
        for label, shortcut, slot in [
            ("放大 (+)",   "Ctrl+=",  self._zoom_in),
            ("缩小 (-)",   "Ctrl+-",  self._zoom_out),
            ("重置缩放",   "Ctrl+0",  self._zoom_reset),
        ]:
            a = QAction(label, self)
            a.setShortcut(shortcut)
            a.triggered.connect(slot)
            vm.addAction(a)

        # 帮助
        hm = mb.addMenu("帮助(&H)")
        a = QAction("关于(&A)", self)
        a.triggered.connect(self._about)
        hm.addAction(a)

    def _build_toolbar(self):
        tb = QToolBar("工具栏")
        tb.setMovable(False)
        self.addToolBar(tb)
        for label, slot in [
            ("📂 打开图像",     self._open_image),
            ("📁 批量处理",     self._open_batch),
            (None, None),
            ("▶ 检测中心线",    self._run_detection),
            ("↩ 重置",          self._reset),
            (None, None),
            ("💾 保存图像",     self._save_result),
            ("📊 导出CSV",      self._export_csv),
            ("📋 导出Excel",    self._export_excel),
            (None, None),
            ("🔎+",             self._zoom_in),
            ("🔎-",             self._zoom_out),
        ]:
            if label is None:
                tb.addSeparator()
            else:
                a = QAction(label, self)
                a.triggered.connect(slot)
                tb.addAction(a)

    def _build_left_panel(self) -> QTabWidget:
        """左侧：选项卡（图像视图 / 坐标曲线 / Y直方图）"""
        self._tabs = QTabWidget()

        # ── 选项卡 0：图像视图 ──
        img_tab = QWidget()
        img_lay = QHBoxLayout(img_tab)
        img_lay.setContentsMargins(4, 4, 4, 4)
        img_lay.setSpacing(4)

        from PyQt5.QtWidgets import QGroupBox
        orig_grp = QGroupBox("原始图像")
        orig_grp_lay = QVBoxLayout(orig_grp)
        self._lbl_original = ZoomImageLabel()
        orig_grp_lay.addWidget(self._lbl_original)

        res_grp = QGroupBox("检测结果")
        res_grp_lay = QVBoxLayout(res_grp)
        self._lbl_result = ZoomImageLabel()
        res_grp_lay.addWidget(self._lbl_result)

        img_split = QSplitter(Qt.Horizontal)
        img_split.addWidget(orig_grp)
        img_split.addWidget(res_grp)
        img_lay.addWidget(img_split)

        # ── 选项卡 1：坐标曲线 ──
        plot_tab = QWidget()
        plot_lay = QVBoxLayout(plot_tab)
        plot_lay.setContentsMargins(6, 6, 6, 6)
        self._canvas_line = PlotCanvas()
        plot_lay.addWidget(self._canvas_line)

        # ── 选项卡 2：Y 直方图 ──
        hist_tab = QWidget()
        hist_lay = QVBoxLayout(hist_tab)
        hist_lay.setContentsMargins(6, 6, 6, 6)
        self._canvas_hist = PlotCanvas()
        hist_lay.addWidget(self._canvas_hist)

        self._tabs.addTab(img_tab,  "📷  图像视图")
        self._tabs.addTab(plot_tab, "📈  坐标曲线")
        self._tabs.addTab(hist_tab, "📊  Y 分布直方图")

        return self._tabs

    def _build_right_panel(self) -> QScrollArea:
        """右侧：可滚动控制面板"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(10)

        # 各子面板
        self._preprocess_panel = PreprocessPanel()
        self._preprocess_panel.changed.connect(self._on_param_changed)
        lay.addWidget(self._preprocess_panel)

        self._detection_panel = DetectionPanel()
        self._detection_panel.detect_requested.connect(self._run_detection)
        self._detection_panel.reset_requested.connect(self._reset)
        lay.addWidget(self._detection_panel)

        self._stats_panel = StatsPanel()
        lay.addWidget(self._stats_panel)

        self._table_panel = DataTablePanel()
        lay.addWidget(self._table_panel)

        lay.addStretch()
        scroll.setWidget(panel)
        return scroll

    # ─────────────────────────────────────────────────────
    #  配置持久化
    # ─────────────────────────────────────────────────────

    def _restore_state(self):
        """从配置文件恢复上次的参数设置。"""
        c = self._cfg
        # 算法
        combo = self._detection_panel.combo_algo
        for i in range(combo.count()):
            if combo.itemData(i) == c.get("algorithm"):
                combo.setCurrentIndex(i)
                break
        # 滤波
        combo_f = self._preprocess_panel.combo_filter
        for i in range(combo_f.count()):
            if combo_f.itemData(i) == c.get("filter_type"):
                combo_f.setCurrentIndex(i)
                break
        self._preprocess_panel.sld_kernel.setValue(c.get("kernel_size", 5))
        self._preprocess_panel.sld_thresh.setValue(c.get("threshold", 0))
        self._preprocess_panel.chk_clahe.setChecked(c.get("clahe", False))
        # 线宽
        self._detection_panel.spin_width.setValue(c.get("line_width", 2))
        # 颜色
        rgb = c.get("line_color", [0, 220, 80])
        self._detection_panel._rgb = rgb
        self._detection_panel.btn_color.setStyleSheet(
            f"color: {QColor(*rgb).name()}; min-width:60px;"
        )

    def _save_state(self):
        """保存当前参数到配置文件。"""
        self._cfg.update({
            "algorithm":   self._detection_panel.get_algorithm(),
            "filter_type": self._preprocess_panel.combo_filter.currentData(),
            "kernel_size": self._preprocess_panel.sld_kernel.value(),
            "threshold":   self._preprocess_panel.sld_thresh.value(),
            "clahe":       self._preprocess_panel.chk_clahe.isChecked(),
            "line_width":  self._detection_panel.get_line_width(),
            "line_color":  self._detection_panel._rgb,
            "last_dir":    os.path.dirname(self._current_path) if self._current_path else "",
        })
        config.save(self._cfg)

    def closeEvent(self, event):
        self._save_state()
        super().closeEvent(event)

    # ─────────────────────────────────────────────────────
    #  文件操作
    # ─────────────────────────────────────────────────────

    def _open_image(self):
        last = self._cfg.get("last_dir", "")
        path, _ = QFileDialog.getOpenFileName(
            self, "打开图像", last, QT_FILTER
        )
        if not path:
            return

        bgr = ImageLoader.load(path)
        if bgr is None:
            QMessageBox.warning(self, "错误", f"无法加载图像：\n{path}")
            return

        self._original_bgr  = bgr
        self._current_path  = path
        self._processed_gray = None
        self._result         = None

        # 显示原图
        self._lbl_original.set_image(self._bgr_to_pixmap(bgr))
        self._lbl_result.clear_image()
        self._table_panel.clear()
        self._stats_panel.update(None)
        self._canvas_line.clear_plot()
        self._canvas_hist.clear_plot()

        h, w = bgr.shape[:2]
        self._set_status(f"已加载: {os.path.basename(path)}")
        self._lbl_info.setText(f"  {w} × {h} px")

    def _open_batch(self):
        if self._worker and self._worker.isRunning():
            QMessageBox.information(self, "提示", "请等待当前检测完成后再启动批量处理。")
            return
        cfg = self._preprocess_panel.get_config()
        algo = self._detection_panel.get_algorithm()
        dlg = BatchDialog(cfg, algo, self)
        dlg.exec_()

    def _save_result(self):
        if self._result is None or not self._result.is_valid():
            QMessageBox.warning(self, "警告", "请先执行检测！")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存结果图像", "",
            "PNG 图像 (*.png);;JPEG 图像 (*.jpg);;所有文件 (*.*)"
        )
        if not path:
            return
        result_bgr = self._make_result_image()
        if ImageLoader.save(path, result_bgr):
            self._set_status(f"图像已保存: {os.path.basename(path)}")
        else:
            QMessageBox.warning(self, "错误", "保存图像失败！")

    # ─────────────────────────────────────────────────────
    #  检测流程
    # ─────────────────────────────────────────────────────

    def _on_param_changed(self):
        """预处理参数变化时触发实时检测（防抖）。"""
        if self._original_bgr is None:
            return
        self._rt_timer.start(self._REALTIME_DELAY_MS)

    def _run_detection(self):
        """执行检测（主入口，可从工具栏/按钮/实时定时器调用）。"""
        if self._original_bgr is None:
            QMessageBox.warning(self, "警告", "请先打开一张图像！")
            return
        if self._worker and self._worker.isRunning():
            return

        # 预处理
        cfg = self._preprocess_panel.get_config()
        self._processed_gray = self._engine.preprocess(self._original_bgr, cfg)

        algo_val = self._detection_panel.get_algorithm()
        algorithm = Algorithm(algo_val)

        self._set_status("正在检测中心线…")
        self._pbar.setVisible(True)
        self._detection_panel.btn_detect.setEnabled(False)

        self._worker = _Worker(
            self._engine, self._processed_gray, algorithm, self._current_path
        )
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, result: DetectionResult):
        self._pbar.setVisible(False)
        self._detection_panel.btn_detect.setEnabled(True)
        self._result = result

        if not result.is_valid():
            self._set_status("未检测到中心线，请调整预处理参数后重试")
            return

        # 更新结果图像
        result_bgr = self._make_result_image()
        self._lbl_result.set_image(self._bgr_to_pixmap(result_bgr))

        # 统计 & 表格
        self._stats_panel.update(result)
        self._table_panel.fill(result.points)

        # 图表
        self._canvas_line.plot_centerline(result.points)
        self._canvas_hist.plot_histogram(result.points)

        algo_name = Algorithm.display_names().get(result.algorithm, result.algorithm)
        self._set_status(
            f"✓ 检测完成 [{algo_name}] — {result.count} 个点  |  耗时 {result.elapsed_ms:.1f} ms"
        )

        # 自动切换到图像视图
        self._tabs.setCurrentIndex(0)

    def _on_error(self, msg: str):
        self._pbar.setVisible(False)
        self._detection_panel.btn_detect.setEnabled(True)
        self._set_status(f"检测出错: {msg}")

    def _reset(self):
        if self._original_bgr is None:
            return
        self._processed_gray = None
        self._result         = None
        self._lbl_result.clear_image()
        self._table_panel.clear()
        self._stats_panel.update(None)
        self._canvas_line.clear_plot()
        self._canvas_hist.clear_plot()
        self._set_status("已重置")

    # ─────────────────────────────────────────────────────
    #  导出
    # ─────────────────────────────────────────────────────

    def _check_result(self) -> bool:
        if self._result is None or not self._result.is_valid():
            QMessageBox.warning(self, "警告", "请先执行检测！")
            return False
        return True

    def _export_csv(self):
        if not self._check_result():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", "", "CSV 文件 (*.csv);;所有文件 (*.*)"
        )
        if path:
            if self._exporter.to_csv(self._result.points, path):
                self._set_status(f"CSV 已导出: {os.path.basename(path)}")
            else:
                QMessageBox.warning(self, "错误", "导出 CSV 失败！")

    def _export_excel(self):
        if not self._check_result():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 Excel", "", "Excel 文件 (*.xlsx);;所有文件 (*.*)"
        )
        if path:
            if self._exporter.to_excel(self._result.points, path):
                self._set_status(f"Excel 已导出: {os.path.basename(path)}")
            else:
                QMessageBox.warning(self, "错误", "导出 Excel 失败！\n请确认 openpyxl 已安装。")

    def _export_json(self):
        if not self._check_result():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 JSON", "", "JSON 文件 (*.json);;所有文件 (*.*)"
        )
        if path:
            if self._exporter.to_json(self._result.points, path):
                self._set_status(f"JSON 已导出: {os.path.basename(path)}")
            else:
                QMessageBox.warning(self, "错误", "导出 JSON 失败！")

    # ─────────────────────────────────────────────────────
    #  缩放操作
    # ─────────────────────────────────────────────────────

    def _zoom_in(self):
        for lbl in (self._lbl_original, self._lbl_result):
            lbl.set_zoom(lbl.zoom_factor() * 1.2)

    def _zoom_out(self):
        for lbl in (self._lbl_original, self._lbl_result):
            lbl.set_zoom(lbl.zoom_factor() / 1.2)

    def _zoom_reset(self):
        for lbl in (self._lbl_original, self._lbl_result):
            lbl.reset_zoom()

    # ─────────────────────────────────────────────────────
    #  工具函数
    # ─────────────────────────────────────────────────────

    def _bgr_to_pixmap(self, bgr: np.ndarray):
        from PyQt5.QtGui import QImage, QPixmap
        h, w = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        qi  = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        return QPixmap.fromImage(qi)

    def _gray_to_pixmap(self, gray: np.ndarray):
        from PyQt5.QtGui import QImage, QPixmap
        h, w = gray.shape
        qi   = QImage(gray.data, w, h, w, QImage.Format_Grayscale8)
        return QPixmap.fromImage(qi)

    def _make_result_image(self) -> np.ndarray:
        """在原图上叠加绘制中心线，返回 BGR 图像。"""
        if self._result is None or self._original_bgr is None:
            return self._original_bgr.copy() if self._original_bgr is not None else np.zeros((1, 1, 3), np.uint8)
        color_bgr = self._detection_panel.get_color_bgr()
        radius    = self._detection_panel.get_line_width()
        return self._engine.draw(self._original_bgr, self._result,
                                 color=color_bgr, radius=radius)

    def _set_status(self, msg: str):
        self._lbl_status.setText(msg)

    def _about(self):
        QMessageBox.about(
            self,
            "关于  LaserLine",
            "<h3>LaserLine — 激光条纹中心线检测软件</h3>"
            "<p>全新独立开发版本，基于 <b>Python · PyQt5 · OpenCV · Matplotlib</b></p>"
            "<hr>"
            "<b>核心功能</b>"
            "<ul>"
            "<li>四种检测算法：灰度重心法、高斯拟合法、极值法、Steger 亚像素法</li>"
            "<li>四种预处理：高斯/中值/双边滤波 + CLAHE 对比度增强</li>"
            "<li>Otsu 自动阈值分割</li>"
            "<li>后台线程检测，界面完全不卡顿</li>"
            "<li>坐标折线图 + Y 分布直方图</li>"
            "<li>批量目录处理，自动生成汇总 Excel 报告</li>"
            "<li>导出 CSV / Excel（含统计页）/ JSON 三种格式</li>"
            "<li>配置自动持久化</li>"
            "<li>滚轮缩放、双击重置</li>"
            "</ul>"
        )
