# -*- coding: utf-8 -*-
"""
laserline.io.loader — 图像加载器
支持单张加载和目录批量扫描，正确处理含中文字符的路径。
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

import cv2
import numpy as np

# 支持的图像扩展名
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}

# Qt 文件对话框过滤器字符串
QT_FILTER = (
    "图像文件 (*.jpg *.jpeg *.png *.bmp *.tiff *.tif);;"
    "所有文件 (*.*)"
)


class ImageLoader:
    """图像加载器，支持含中文路径。"""

    @staticmethod
    def load(path: str) -> Optional[np.ndarray]:
        """
        加载单张图像，返回 BGR ndarray；失败返回 None。

        Args:
            path: 图像文件路径（支持中文路径）
        """
        try:
            raw = np.fromfile(path, dtype=np.uint8)
            img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
            return img
        except Exception as exc:
            print(f"[ImageLoader] 加载失败 {path}: {exc}")
            return None

    @staticmethod
    def load_gray(path: str) -> Optional[np.ndarray]:
        """加载并转为灰度图。"""
        bgr = ImageLoader.load(path)
        if bgr is None:
            return None
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def scan_directory(directory: str) -> List[str]:
        """
        扫描目录，返回所有支持格式的图像路径列表（已排序）。

        Args:
            directory: 目录路径
        """
        paths = []
        for name in sorted(os.listdir(directory)):
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                paths.append(os.path.join(directory, name))
        return paths

    @staticmethod
    def save(path: str, image: np.ndarray) -> bool:
        """
        保存图像到指定路径（支持中文路径）。

        Args:
            path: 输出路径
            image: BGR 图像

        Returns:
            bool: 是否成功
        """
        try:
            ext = os.path.splitext(path)[1].lower()
            success, buf = cv2.imencode(ext, image)
            if success:
                buf.tofile(path)
                return True
            return False
        except Exception as exc:
            print(f"[ImageLoader] 保存失败 {path}: {exc}")
            return False
