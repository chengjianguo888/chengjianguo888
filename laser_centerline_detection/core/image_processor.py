# -*- coding: utf-8 -*-
"""
图像预处理模块
提供图像加载、灰度化、滤波、阈值分割等功能
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class ImageProcessor:
    """图像处理器类"""
    
    def __init__(self):
        """初始化图像处理器"""
        self.original_image = None
        self.processed_image = None
        self.gray_image = None
        
    def load_image(self, file_path: str) -> bool:
        """
        加载图像文件
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            bool: 是否成功加载
        """
        try:
            self.original_image = cv2.imread(file_path)
            if self.original_image is None:
                return False
            
            # 转换为灰度图
            if len(self.original_image.shape) == 3:
                self.gray_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
            else:
                self.gray_image = self.original_image.copy()
            
            self.processed_image = self.gray_image.copy()
            return True
        except Exception as e:
            print(f"加载图像失败: {str(e)}")
            return False
    
    def apply_gaussian_filter(self, kernel_size: int = 5) -> np.ndarray:
        """
        应用高斯滤波
        
        Args:
            kernel_size: 高斯核大小（必须是奇数）
            
        Returns:
            np.ndarray: 滤波后的图像
        """
        if self.gray_image is None:
            return None
        
        # 确保kernel_size是奇数
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        self.processed_image = cv2.GaussianBlur(
            self.gray_image, 
            (kernel_size, kernel_size), 
            0
        )
        return self.processed_image
    
    def apply_threshold(self, threshold_value: int = 128) -> np.ndarray:
        """
        应用阈值分割
        
        Args:
            threshold_value: 阈值（0-255）
            
        Returns:
            np.ndarray: 阈值分割后的图像
        """
        if self.processed_image is None:
            return None
        
        _, binary_image = cv2.threshold(
            self.processed_image,
            threshold_value,
            255,
            cv2.THRESH_BINARY
        )
        return binary_image
    
    def select_roi(self, image: np.ndarray, roi: Tuple[int, int, int, int]) -> np.ndarray:
        """
        选择感兴趣区域（ROI）
        
        Args:
            image: 输入图像
            roi: ROI坐标 (x, y, width, height)
            
        Returns:
            np.ndarray: ROI区域图像
        """
        if image is None:
            return None
        
        x, y, w, h = roi
        return image[y:y+h, x:x+w]
    
    def get_image(self, image_type: str = 'processed') -> Optional[np.ndarray]:
        """
        获取指定类型的图像
        
        Args:
            image_type: 图像类型 ('original', 'gray', 'processed')
            
        Returns:
            np.ndarray: 图像数组
        """
        if image_type == 'original':
            return self.original_image
        elif image_type == 'gray':
            return self.gray_image
        elif image_type == 'processed':
            return self.processed_image
        return None
    
    def reset(self):
        """重置图像处理器"""
        if self.gray_image is not None:
            self.processed_image = self.gray_image.copy()
