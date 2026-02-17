# -*- coding: utf-8 -*-
"""
自定义控件模块
"""

from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap


class ImageLabel(QLabel):
    """
    可显示图像的标签控件
    支持自适应缩放
    """
    
    clicked = pyqtSignal()  # 点击信号
    
    def __init__(self, parent=None):
        """初始化图像标签"""
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("QLabel { background-color: #2b2b2b; }")
        self.setMinimumSize(400, 300)
        self.original_pixmap = None
        
    def setPixmap(self, pixmap: QPixmap):
        """
        设置图像
        
        Args:
            pixmap: 图像对象
        """
        self.original_pixmap = pixmap
        self._update_scaled_pixmap()
    
    def _update_scaled_pixmap(self):
        """更新缩放后的图像"""
        if self.original_pixmap:
            scaled_pixmap = self.original_pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            super().setPixmap(scaled_pixmap)
    
    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        self._update_scaled_pixmap()
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        self.clicked.emit()
        super().mousePressEvent(event)
