# -*- coding: utf-8 -*-
"""
主窗口模块
实现完整的GUI界面
"""

import cv2
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QSlider, QComboBox, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QSplitter, QGroupBox,
    QMessageBox, QStatusBar, QMenuBar, QAction
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from ..core import ImageProcessor, CenterlineDetector, DataExporter
from ..utils import convert_cv_to_pixmap, get_supported_formats
from .widgets import ImageLabel


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 初始化核心模块
        self.image_processor = ImageProcessor()
        self.centerline_detector = CenterlineDetector()
        self.data_exporter = DataExporter()
        
        # 当前文件路径
        self.current_file = None
        
        # 初始化UI
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("激光中心线检测软件")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建菜单栏
        self.create_menu_bar()
        
        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧：图像显示区域
        left_widget = self.create_image_display_area()
        
        # 右侧：控制面板和数据展示
        right_widget = self.create_control_panel()
        
        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        
        # 打开文件
        open_action = QAction("打开图像(&O)", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_image)
        file_menu.addAction(open_action)
        
        # 保存结果
        save_action = QAction("保存结果图像(&S)", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_result_image)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        # 导出数据
        export_action = QAction("导出数据(&E)", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_image_display_area(self) -> QWidget:
        """创建图像显示区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 原始图像
        original_group = QGroupBox("原始图像")
        original_layout = QVBoxLayout(original_group)
        self.original_image_label = ImageLabel()
        original_layout.addWidget(self.original_image_label)
        
        # 结果图像
        result_group = QGroupBox("检测结果")
        result_layout = QVBoxLayout(result_group)
        self.result_image_label = ImageLabel()
        result_layout.addWidget(self.result_image_label)
        
        layout.addWidget(original_group)
        layout.addWidget(result_group)
        
        return widget
        
    def create_control_panel(self) -> QWidget:
        """创建控制面板"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 参数控制组
        params_group = QGroupBox("参数控制")
        params_layout = QVBoxLayout(params_group)
        
        # 高斯滤波核大小
        gaussian_layout = QHBoxLayout()
        gaussian_layout.addWidget(QLabel("高斯滤波核大小:"))
        self.gaussian_slider = QSlider(Qt.Horizontal)
        self.gaussian_slider.setMinimum(1)
        self.gaussian_slider.setMaximum(15)
        self.gaussian_slider.setValue(5)
        self.gaussian_slider.setTickPosition(QSlider.TicksBelow)
        self.gaussian_slider.setTickInterval(2)
        self.gaussian_label = QLabel("5")
        self.gaussian_slider.valueChanged.connect(self.on_gaussian_changed)
        gaussian_layout.addWidget(self.gaussian_slider)
        gaussian_layout.addWidget(self.gaussian_label)
        params_layout.addLayout(gaussian_layout)
        
        # 阈值
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("二值化阈值:"))
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(255)
        self.threshold_slider.setValue(128)
        self.threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.threshold_slider.setTickInterval(25)
        self.threshold_label = QLabel("128")
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_label)
        params_layout.addLayout(threshold_layout)
        
        # 算法选择
        algorithm_layout = QHBoxLayout()
        algorithm_layout.addWidget(QLabel("检测算法:"))
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItem("灰度重心法", CenterlineDetector.METHOD_GRAY_CENTROID)
        self.algorithm_combo.addItem("高斯拟合法", CenterlineDetector.METHOD_GAUSSIAN_FITTING)
        self.algorithm_combo.addItem("极值法", CenterlineDetector.METHOD_MAX_VALUE)
        algorithm_layout.addWidget(self.algorithm_combo)
        params_layout.addLayout(algorithm_layout)
        
        # 处理按钮
        button_layout = QHBoxLayout()
        self.process_button = QPushButton("应用滤波")
        self.process_button.clicked.connect(self.apply_preprocessing)
        self.detect_button = QPushButton("检测中心线")
        self.detect_button.clicked.connect(self.detect_centerline)
        button_layout.addWidget(self.process_button)
        button_layout.addWidget(self.detect_button)
        params_layout.addLayout(button_layout)
        
        # 重置按钮
        self.reset_button = QPushButton("重置图像")
        self.reset_button.clicked.connect(self.reset_image)
        params_layout.addWidget(self.reset_button)
        
        layout.addWidget(params_group)
        
        # 数据展示组
        data_group = QGroupBox("中心线坐标数据")
        data_layout = QVBoxLayout(data_group)
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(3)
        self.data_table.setHorizontalHeaderLabels(["序号", "X坐标", "Y坐标"])
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        data_layout.addWidget(self.data_table)
        
        layout.addWidget(data_group)
        
        return widget
    
    def on_gaussian_changed(self, value):
        """高斯滤波滑块变化"""
        # 确保是奇数
        if value % 2 == 0:
            value += 1
            self.gaussian_slider.setValue(value)
        self.gaussian_label.setText(str(value))
    
    def on_threshold_changed(self, value):
        """阈值滑块变化"""
        self.threshold_label.setText(str(value))
    
    def open_image(self):
        """打开图像文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图像文件",
            "",
            get_supported_formats()
        )
        
        if file_path:
            if self.image_processor.load_image(file_path):
                self.current_file = file_path
                # 显示原始图像
                original_image = self.image_processor.get_image('original')
                pixmap = convert_cv_to_pixmap(original_image)
                self.original_image_label.setPixmap(pixmap)
                
                # 清空结果
                self.result_image_label.clear()
                self.data_table.setRowCount(0)
                
                self.status_bar.showMessage(f"已加载: {file_path}")
            else:
                QMessageBox.warning(self, "错误", "无法加载图像文件！")
    
    def apply_preprocessing(self):
        """应用预处理"""
        if self.image_processor.gray_image is None:
            QMessageBox.warning(self, "警告", "请先加载图像！")
            return
        
        # 应用高斯滤波
        kernel_size = self.gaussian_slider.value()
        self.image_processor.apply_gaussian_filter(kernel_size)
        
        self.status_bar.showMessage("已应用预处理")
    
    def detect_centerline(self):
        """检测激光中心线"""
        if self.image_processor.processed_image is None:
            QMessageBox.warning(self, "警告", "请先加载图像！")
            return
        
        # 获取选择的算法
        method = self.algorithm_combo.currentData()
        
        # 检测中心线
        self.status_bar.showMessage("正在检测中心线...")
        centerline_points = self.centerline_detector.detect(
            self.image_processor.processed_image,
            method
        )
        
        if not centerline_points:
            QMessageBox.warning(self, "警告", "未检测到激光中心线！")
            self.status_bar.showMessage("检测失败")
            return
        
        # 在原图上绘制中心线
        original_image = self.image_processor.get_image('original')
        result_image = self.centerline_detector.draw_centerline(
            original_image.copy(),
            color=(0, 255, 0),
            thickness=2
        )
        
        # 显示结果
        pixmap = convert_cv_to_pixmap(result_image)
        self.result_image_label.setPixmap(pixmap)
        
        # 更新数据表格
        self.update_data_table(centerline_points)
        
        self.status_bar.showMessage(f"检测完成，共检测到 {len(centerline_points)} 个点")
    
    def update_data_table(self, centerline_points):
        """更新数据表格"""
        self.data_table.setRowCount(len(centerline_points))
        
        for i, (x, y) in enumerate(centerline_points):
            self.data_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.data_table.setItem(i, 1, QTableWidgetItem(str(x)))
            self.data_table.setItem(i, 2, QTableWidgetItem(f"{y:.2f}"))
    
    def reset_image(self):
        """重置图像"""
        if self.image_processor.gray_image is None:
            return
        
        self.image_processor.reset()
        self.result_image_label.clear()
        self.data_table.setRowCount(0)
        self.status_bar.showMessage("已重置图像")
    
    def save_result_image(self):
        """保存结果图像"""
        if self.result_image_label.pixmap() is None:
            QMessageBox.warning(self, "警告", "没有可保存的结果图像！")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存结果图像",
            "",
            "PNG图像 (*.png);;JPEG图像 (*.jpg);;所有文件 (*.*)"
        )
        
        if file_path:
            # 获取结果图像
            original_image = self.image_processor.get_image('original')
            result_image = self.centerline_detector.draw_centerline(
                original_image.copy(),
                color=(0, 255, 0),
                thickness=2
            )
            
            if cv2.imwrite(file_path, result_image):
                QMessageBox.information(self, "成功", "结果图像已保存！")
                self.status_bar.showMessage(f"已保存: {file_path}")
            else:
                QMessageBox.warning(self, "错误", "保存图像失败！")
    
    def export_data(self):
        """导出数据为CSV"""
        centerline_points = self.centerline_detector.get_centerline_points()
        
        if not centerline_points:
            QMessageBox.warning(self, "警告", "没有可导出的数据！")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出数据",
            "",
            "CSV文件 (*.csv);;所有文件 (*.*)"
        )
        
        if file_path:
            if self.data_exporter.export_to_csv(centerline_points, file_path):
                QMessageBox.information(self, "成功", "数据已导出！")
                self.status_bar.showMessage(f"已导出: {file_path}")
            else:
                QMessageBox.warning(self, "错误", "导出数据失败！")
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            "<h3>激光中心线检测软件</h3>"
            "<p>版本: 1.0</p>"
            "<p>本软件用于激光条纹中心线检测</p>"
            "<p>支持三种检测算法：</p>"
            "<ul>"
            "<li>灰度重心法</li>"
            "<li>高斯拟合法</li>"
            "<li>极值法</li>"
            "</ul>"
        )
