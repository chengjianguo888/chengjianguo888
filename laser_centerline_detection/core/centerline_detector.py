# -*- coding: utf-8 -*-
"""
激光中心线检测算法模块
实现三种检测算法：灰度重心法、高斯拟合法、极值法
"""

import cv2
import numpy as np
from scipy.optimize import curve_fit
from typing import List, Tuple, Optional


class CenterlineDetector:
    """激光中心线检测器类"""
    
    # 算法类型常量
    METHOD_GRAY_CENTROID = "gray_centroid"
    METHOD_GAUSSIAN_FITTING = "gaussian_fitting"
    METHOD_MAX_VALUE = "max_value"
    
    def __init__(self):
        """初始化检测器"""
        self.centerline_points = []
        
    def detect(self, image: np.ndarray, method: str = METHOD_GRAY_CENTROID) -> List[Tuple[int, float]]:
        """
        检测激光中心线
        
        Args:
            image: 输入图像（灰度图）
            method: 检测方法
            
        Returns:
            List[Tuple[int, float]]: 中心线坐标点列表 [(x, y), ...]
        """
        if image is None or len(image.shape) > 2:
            return []
        
        if method == self.METHOD_GRAY_CENTROID:
            self.centerline_points = self._gray_centroid_method(image)
        elif method == self.METHOD_GAUSSIAN_FITTING:
            self.centerline_points = self._gaussian_fitting_method(image)
        elif method == self.METHOD_MAX_VALUE:
            self.centerline_points = self._max_value_method(image)
        else:
            self.centerline_points = self._gray_centroid_method(image)
        
        return self.centerline_points
    
    def _gray_centroid_method(self, image: np.ndarray) -> List[Tuple[int, float]]:
        """
        灰度重心法
        计算每列像素灰度值的加权平均位置
        
        Args:
            image: 输入灰度图像
            
        Returns:
            List[Tuple[int, float]]: 中心线坐标点
        """
        height, width = image.shape
        centerline = []
        
        for col in range(width):
            column_data = image[:, col].astype(np.float64)
            
            # 过滤低灰度值（噪声）
            threshold = np.max(column_data) * 0.1
            column_data[column_data < threshold] = 0
            
            # 计算灰度加权重心
            total_intensity = np.sum(column_data)
            if total_intensity > 0:
                weighted_sum = np.sum(column_data * np.arange(height))
                centroid_y = weighted_sum / total_intensity
                centerline.append((col, centroid_y))
        
        return centerline
    
    def _gaussian_fitting_method(self, image: np.ndarray) -> List[Tuple[int, float]]:
        """
        高斯拟合法
        对每列像素灰度分布进行高斯曲线拟合
        
        Args:
            image: 输入灰度图像
            
        Returns:
            List[Tuple[int, float]]: 中心线坐标点
        """
        height, width = image.shape
        centerline = []
        
        def gaussian(x, amplitude, mean, stddev):
            """高斯函数"""
            return amplitude * np.exp(-((x - mean) ** 2) / (2 * stddev ** 2))
        
        for col in range(width):
            column_data = image[:, col].astype(np.float64)
            
            # 找到峰值位置作为初始估计
            max_idx = np.argmax(column_data)
            max_val = column_data[max_idx]
            
            if max_val < 10:  # 跳过低强度列
                continue
            
            try:
                # 设置初始参数：振幅、均值、标准差
                x_data = np.arange(height)
                initial_guess = [max_val, max_idx, 3.0]
                
                # 拟合高斯曲线
                params, _ = curve_fit(
                    gaussian, 
                    x_data, 
                    column_data,
                    p0=initial_guess,
                    maxfev=1000
                )
                
                # 提取均值作为中心位置
                center_y = params[1]
                
                # 确保中心点在有效范围内
                if 0 <= center_y < height:
                    centerline.append((col, center_y))
                    
            except Exception:
                # 如果拟合失败，使用极值法作为备选
                centerline.append((col, float(max_idx)))
        
        return centerline
    
    def _max_value_method(self, image: np.ndarray) -> List[Tuple[int, float]]:
        """
        极值法
        取每列最大灰度值位置作为中心点
        
        Args:
            image: 输入灰度图像
            
        Returns:
            List[Tuple[int, float]]: 中心线坐标点
        """
        height, width = image.shape
        centerline = []
        
        for col in range(width):
            column_data = image[:, col]
            max_idx = np.argmax(column_data)
            max_val = column_data[max_idx]
            
            # 只保留有效的激光点（高于阈值）
            if max_val > 10:
                centerline.append((col, float(max_idx)))
        
        return centerline
    
    def get_centerline_points(self) -> List[Tuple[int, float]]:
        """
        获取中心线坐标点
        
        Returns:
            List[Tuple[int, float]]: 中心线坐标点列表
        """
        return self.centerline_points
    
    def draw_centerline(self, image: np.ndarray, color: Tuple[int, int, int] = (0, 255, 0), 
                       thickness: int = 2) -> np.ndarray:
        """
        在图像上绘制中心线
        
        Args:
            image: 输入图像
            color: 中心线颜色 (B, G, R)
            thickness: 线条粗细
            
        Returns:
            np.ndarray: 绘制了中心线的图像
        """
        if len(self.centerline_points) == 0:
            return image
        
        # 如果是灰度图，转换为彩色图
        if len(image.shape) == 2:
            result_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            result_image = image.copy()
        
        # 绘制中心线点
        for x, y in self.centerline_points:
            cv2.circle(result_image, (int(x), int(y)), thickness, color, -1)
        
        return result_image
