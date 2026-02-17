# -*- coding: utf-8 -*-
"""
辅助工具函数
提供图像格式转换等功能
"""

import cv2
import numpy as np
from PyQt5.QtGui import QImage, QPixmap


def convert_cv_to_pixmap(cv_image: np.ndarray) -> QPixmap:
    """
    将OpenCV图像转换为QPixmap
    
    Args:
        cv_image: OpenCV图像（numpy数组）
        
    Returns:
        QPixmap: Qt图像对象
    """
    if cv_image is None:
        return QPixmap()
    
    # 处理灰度图
    if len(cv_image.shape) == 2:
        height, width = cv_image.shape
        bytes_per_line = width
        q_image = QImage(cv_image.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
    # 处理彩色图
    else:
        height, width, channel = cv_image.shape
        bytes_per_line = 3 * width
        # OpenCV使用BGR，Qt使用RGB，需要转换
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
    
    return QPixmap.fromImage(q_image)


def get_supported_formats() -> str:
    """
    获取支持的图像格式
    
    Returns:
        str: 格式字符串（用于文件对话框）
    """
    return "图像文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif);;所有文件 (*.*)"
