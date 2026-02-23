# -*- coding: utf-8 -*-
"""
laserline.ui.batch_dialog — 批量处理对话框
允许用户选择一个目录，批量检测所有图像并导出汇总报告。
"""

from __future__ import annotations

import os
from typing import List

import pandas as pd
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QProgressBar, QTextEdit,
    QComboBox, QMessageBox
)

from ..detection.engine import Algorithm, DetectionEngine, PreprocessConfig
from ..io.loader import ImageLoader
from ..io.exporter import DataExporter


class _BatchWorker(QThread):
    """后台批量检测线程"""
    progress = pyqtSignal(int, int, str)    # current, total, filename
    finished = pyqtSignal(list)             # list of DetectionResult

    def __init__(self, paths: List[str], algorithm: str,
                 preprocess_cfg: PreprocessConfig):
        super().__init__()
        self._paths = paths
        self._algo  = Algorithm(algorithm)
        self._cfg   = preprocess_cfg

    def run(self):
        engine  = DetectionEngine()
        results = []
        total   = len(self._paths)
        for i, path in enumerate(self._paths, 1):
            self.progress.emit(i, total, os.path.basename(path))
            img = ImageLoader.load(path)
            if img is None:
                continue
            gray = engine.preprocess(img, self._cfg)
            result = engine.run(gray, self._algo, image_path=path)
            results.append(result)
        self.finished.emit(results)


class BatchDialog(QDialog):
    """批量处理对话框"""

    def __init__(self, preprocess_cfg: PreprocessConfig,
                 default_algo: str = "gray_centroid",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量处理")
        self.setMinimumWidth(520)
        self._cfg  = preprocess_cfg
        self._worker: _BatchWorker | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── 目录选择 ──
        layout.addWidget(QLabel("图像目录："))
        dir_row = QHBoxLayout()
        self.edit_dir = QLineEdit()
        self.edit_dir.setPlaceholderText("选择包含图像文件的目录…")
        self.btn_dir = QPushButton("浏览…")
        self.btn_dir.clicked.connect(self._browse_dir)
        dir_row.addWidget(self.edit_dir)
        dir_row.addWidget(self.btn_dir)
        layout.addLayout(dir_row)

        # ── 算法选择 ──
        algo_row = QHBoxLayout()
        algo_row.addWidget(QLabel("检测算法："))
        self.combo_algo = QComboBox()
        names = Algorithm.display_names()
        for algo in Algorithm:
            self.combo_algo.addItem(names[algo.value], algo.value)
        for i in range(self.combo_algo.count()):
            if self.combo_algo.itemData(i) == default_algo:
                self.combo_algo.setCurrentIndex(i)
                break
        algo_row.addWidget(self.combo_algo)
        algo_row.addStretch()
        layout.addLayout(algo_row)

        # ── 输出目录 ──
        layout.addWidget(QLabel("报告输出目录："))
        out_row = QHBoxLayout()
        self.edit_out = QLineEdit()
        self.edit_out.setPlaceholderText("默认为图像目录下的 batch_results/")
        self.btn_out = QPushButton("浏览…")
        self.btn_out.clicked.connect(self._browse_out)
        out_row.addWidget(self.edit_out)
        out_row.addWidget(self.btn_out)
        layout.addLayout(out_row)

        # ── 进度条 ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # ── 日志 ──
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMaximumHeight(140)
        self.log_box.setStyleSheet(
            "background:#0a0a1a; color:#80c080; font-size:11px; font-family:monospace;"
        )
        layout.addWidget(self.log_box)

        # ── 按钮 ──
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("开始处理")
        self.btn_start.setMinimumHeight(32)
        self.btn_start.clicked.connect(self._start)
        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.close)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择图像目录")
        if d:
            self.edit_dir.setText(d)

    def _browse_out(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            self.edit_out.setText(d)

    def _log(self, msg: str):
        self.log_box.append(msg)
        self.log_box.verticalScrollBar().setValue(
            self.log_box.verticalScrollBar().maximum()
        )

    def _start(self):
        src_dir = self.edit_dir.text().strip()
        if not src_dir or not os.path.isdir(src_dir):
            QMessageBox.warning(self, "警告", "请选择有效的图像目录！")
            return

        paths = ImageLoader.scan_directory(src_dir)
        if not paths:
            QMessageBox.information(self, "提示", "所选目录中没有支持的图像文件。")
            return

        out_dir = self.edit_out.text().strip() or os.path.join(src_dir, "batch_results")
        os.makedirs(out_dir, exist_ok=True)
        self._out_dir = out_dir
        self._src_dir = src_dir

        algo = self.combo_algo.currentData()
        self.progress_bar.setRange(0, len(paths))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.btn_start.setEnabled(False)
        self._log(f"开始处理 {len(paths)} 张图像，算法：{algo}")

        self._worker = _BatchWorker(paths, algo, self._cfg)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, cur: int, total: int, name: str):
        self.progress_bar.setValue(cur)
        self._log(f"[{cur}/{total}] {name}")

    def _on_finished(self, results):
        self.btn_start.setEnabled(True)
        self.progress_bar.setVisible(False)

        exporter = DataExporter()
        total_pts = sum(r.count for r in results)
        self._log(f"\n✓ 完成！共处理 {len(results)} 张图像，合计 {total_pts} 个检测点。")

        # 导出汇总 Excel
        rows = []
        for r in results:
            rows.append({
                "文件名":   os.path.basename(r.image_path),
                "算法":    r.algorithm,
                "检测点数": r.count,
                "Y最小值":  round(r.y_min, 4) if r.y_min is not None else "",
                "Y最大值":  round(r.y_max, 4) if r.y_max is not None else "",
                "Y均值":   round(r.y_mean, 4) if r.y_mean is not None else "",
                "Y标准差":  round(r.y_std, 4) if r.y_std is not None else "",
                "耗时ms":  r.elapsed_ms,
            })
        summary_path = os.path.join(self._out_dir, "batch_summary.xlsx")
        try:
            pd.DataFrame(rows).to_excel(summary_path, index=False)
            self._log(f"汇总报告已保存：{summary_path}")
        except Exception as exc:
            self._log(f"保存汇总失败：{exc}")

        # 各图像单独导出 CSV
        for r in results:
            if not r.is_valid():
                continue
            name = os.path.splitext(os.path.basename(r.image_path))[0]
            csv_path = os.path.join(self._out_dir, f"{name}_centerline.csv")
            exporter.to_csv(r.points, csv_path)

        self._log(f"所有 CSV 已保存至：{self._out_dir}")
        QMessageBox.information(self, "完成",
                                f"批量处理完成！\n结果保存在：{self._out_dir}")
