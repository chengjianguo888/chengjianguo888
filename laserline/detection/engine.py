# -*- coding: utf-8 -*-
"""
laserline.detection.engine — 全新检测引擎

支持四种算法：
  • gray_centroid  — 灰度重心法
  • gaussian_fit   — 高斯拟合法
  • peak           — 极值法
  • steger         — Steger 亚像素法（基于 Hessian 特征值）

批量处理模式支持多帧图像统一流水线。
"""

from __future__ import annotations

import enum
import time
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from scipy.optimize import curve_fit


# ─────────────────────────────────────────────────────
#  公开常量
# ─────────────────────────────────────────────────────

class Algorithm(str, enum.Enum):
    """检测算法枚举"""
    GRAY_CENTROID = "gray_centroid"
    GAUSSIAN_FIT  = "gaussian_fit"
    PEAK          = "peak"
    STEGER        = "steger"

    @classmethod
    def display_names(cls):
        """返回 {value: 显示名称} 字典"""
        return {
            cls.GRAY_CENTROID.value: "灰度重心法",
            cls.GAUSSIAN_FIT.value:  "高斯拟合法",
            cls.PEAK.value:          "极值法",
            cls.STEGER.value:        "Steger 亚像素法",
        }


# ─────────────────────────────────────────────────────
#  结果数据类
# ─────────────────────────────────────────────────────

@dataclass
class DetectionResult:
    """单次检测结果"""
    points: List[Tuple[int, float]] = field(default_factory=list)
    algorithm: str = ""
    elapsed_ms: float = 0.0
    image_path: str = ""

    # ── 统计信息（只读属性）──

    @property
    def count(self) -> int:
        return len(self.points)

    @property
    def y_values(self) -> np.ndarray:
        return np.array([p[1] for p in self.points]) if self.points else np.array([])

    @property
    def y_min(self) -> Optional[float]:
        return float(self.y_values.min()) if self.count else None

    @property
    def y_max(self) -> Optional[float]:
        return float(self.y_values.max()) if self.count else None

    @property
    def y_mean(self) -> Optional[float]:
        return float(self.y_values.mean()) if self.count else None

    @property
    def y_std(self) -> Optional[float]:
        return float(self.y_values.std()) if self.count else None

    def is_valid(self) -> bool:
        return self.count > 0


# ─────────────────────────────────────────────────────
#  预处理参数
# ─────────────────────────────────────────────────────

@dataclass
class PreprocessConfig:
    """图像预处理参数"""
    filter_type: str  = "gaussian"   # "gaussian" | "median" | "bilateral" | "none"
    kernel_size: int  = 5
    threshold: int    = 0            # 0 = Otsu 自动
    clahe: bool       = False
    clahe_clip: float = 2.0
    clahe_tile: int   = 8


@dataclass
class StegerConfig:
    """Steger 亚像素算法专用参数"""
    sigma: float           = 2.0    # 高斯平滑标准差（值越大平滑越强）
    intensity_ratio: float = 0.10   # 有效像素强度比例阈值（相对全图最大值）
    search_radius: int     = 8      # 峰值附近搜索半径（像素）


# ─────────────────────────────────────────────────────
#  核心检测引擎
# ─────────────────────────────────────────────────────

class DetectionEngine:
    """
    激光中心线检测引擎

    使用流程：
        engine = DetectionEngine()
        result = engine.run(gray_image, Algorithm.GRAY_CENTROID)
    """

    # ── 预处理 ──────────────────────────────────────

    def preprocess(self, bgr_or_gray: np.ndarray,
                   cfg: Optional[PreprocessConfig] = None) -> np.ndarray:
        """
        对原始图像进行预处理，返回适合检测的灰度图。

        Args:
            bgr_or_gray: BGR 彩色图或灰度图
            cfg: 预处理参数，None 时使用默认值

        Returns:
            np.ndarray: 处理后的灰度图
        """
        if cfg is None:
            cfg = PreprocessConfig()

        # 转为灰度
        if len(bgr_or_gray.shape) == 3:
            gray = cv2.cvtColor(bgr_or_gray, cv2.COLOR_BGR2GRAY)
        else:
            gray = bgr_or_gray.copy()

        # CLAHE 对比度增强
        if cfg.clahe:
            clahe = cv2.createCLAHE(
                clipLimit=cfg.clahe_clip,
                tileGridSize=(cfg.clahe_tile, cfg.clahe_tile)
            )
            gray = clahe.apply(gray)

        # 空间滤波
        k = cfg.kernel_size if cfg.kernel_size % 2 == 1 else cfg.kernel_size + 1
        if cfg.filter_type == "gaussian":
            gray = cv2.GaussianBlur(gray, (k, k), 0)
        elif cfg.filter_type == "median":
            gray = cv2.medianBlur(gray, k)
        elif cfg.filter_type == "bilateral":
            gray = cv2.bilateralFilter(gray, k, k * 2, k * 2)

        # 阈值分割（0 = Otsu 自动）
        if cfg.threshold == 0:
            _, gray = cv2.threshold(
                gray, 0, 255, cv2.THRESH_TOZERO + cv2.THRESH_OTSU
            )
        elif cfg.threshold > 0:
            _, gray = cv2.threshold(
                gray, cfg.threshold, 255, cv2.THRESH_TOZERO
            )

        return gray

    # ── 主检测接口 ──────────────────────────────────

    def run(self, image: np.ndarray, algorithm: Algorithm = Algorithm.GRAY_CENTROID,
            image_path: str = "",
            steger_cfg: Optional["StegerConfig"] = None) -> DetectionResult:
        """
        对单张灰度图执行中心线检测。

        Args:
            image: 灰度图（单通道）
            algorithm: 检测算法
            image_path: 来源路径（记录用）
            steger_cfg: Steger 算法专用参数（仅当 algorithm=STEGER 时有效），
                        None 时使用默认值

        Returns:
            DetectionResult
        """
        if image is None or image.ndim != 2:
            return DetectionResult(image_path=image_path)

        t0 = time.perf_counter()

        if algorithm == Algorithm.STEGER:
            cfg_s = steger_cfg if steger_cfg is not None else StegerConfig()
            points = self._steger(image,
                                  sigma=cfg_s.sigma,
                                  intensity_ratio=cfg_s.intensity_ratio,
                                  search_radius=cfg_s.search_radius)
        else:
            dispatch = {
                Algorithm.GRAY_CENTROID: self._gray_centroid,
                Algorithm.GAUSSIAN_FIT:  self._gaussian_fit,
                Algorithm.PEAK:          self._peak,
            }
            func = dispatch.get(algorithm, self._gray_centroid)
            points = func(image)

        elapsed = (time.perf_counter() - t0) * 1000

        return DetectionResult(
            points=points,
            algorithm=algorithm.value if isinstance(algorithm, Algorithm) else str(algorithm),
            elapsed_ms=round(elapsed, 2),
            image_path=image_path,
        )

    def run_batch(self, images: List[Tuple[str, np.ndarray]],
                  algorithm: Algorithm = Algorithm.GRAY_CENTROID,
                  preprocess_cfg: Optional[PreprocessConfig] = None
                  ) -> List[DetectionResult]:
        """
        批量检测多张图像。

        Args:
            images: [(path, bgr_or_gray), ...]
            algorithm: 检测算法
            preprocess_cfg: 预处理参数

        Returns:
            List[DetectionResult]
        """
        results = []
        for path, img in images:
            processed = self.preprocess(img, preprocess_cfg)
            result = self.run(processed, algorithm, image_path=path)
            results.append(result)
        return results

    def draw(self, bgr_image: np.ndarray, result: DetectionResult,
             color: Tuple[int, int, int] = (0, 220, 80),
             radius: int = 2) -> np.ndarray:
        """
        在 BGR 图像上叠加绘制检测到的中心线。

        Args:
            bgr_image: 原始 BGR 图像
            result: 检测结果
            color: BGR 颜色
            radius: 点半径

        Returns:
            np.ndarray: 绘制后的 BGR 图像
        """
        out = bgr_image.copy()
        if len(out.shape) == 2:
            out = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
        for x, y in result.points:
            cv2.circle(out, (int(x), int(y)), radius, color, -1)
        return out

    # ── 算法实现 ────────────────────────────────────

    def _gray_centroid(self, image: np.ndarray) -> List[Tuple[int, float]]:
        """
        灰度重心法
        对每列灰度值做加权平均，权重为像素强度。
        抑制低于列峰值10%的像素以减少噪声影响。
        """
        h, w = image.shape
        pts: List[Tuple[int, float]] = []
        col_arr = image.astype(np.float64)
        rows = np.arange(h, dtype=np.float64)

        for x in range(w):
            col = col_arr[:, x].copy()
            thr = col.max() * 0.1
            col[col < thr] = 0.0
            total = col.sum()
            if total > 0:
                y = (col * rows).sum() / total
                pts.append((x, y))
        return pts

    def _gaussian_fit(self, image: np.ndarray) -> List[Tuple[int, float]]:
        """
        高斯拟合法
        对每列灰度分布拟合高斯函数，取均值作为中心位置。
        拟合失败时自动退化为极值法。
        """
        h, w = image.shape
        pts: List[Tuple[int, float]] = []
        x_data = np.arange(h, dtype=np.float64)

        def _gauss(x, amp, mu, sigma):
            return amp * np.exp(-0.5 * ((x - mu) / sigma) ** 2)

        for col_idx in range(w):
            col = image[:, col_idx].astype(np.float64)
            peak_idx = int(col.argmax())
            peak_val = col[peak_idx]
            if peak_val < 10:
                continue
            try:
                p0 = [peak_val, float(peak_idx), 3.0]
                popt, _ = curve_fit(_gauss, x_data, col, p0=p0, maxfev=800)
                mu = float(popt[1])
                if 0 <= mu < h:
                    pts.append((col_idx, mu))
            except Exception:
                pts.append((col_idx, float(peak_idx)))
        return pts

    def _peak(self, image: np.ndarray) -> List[Tuple[int, float]]:
        """
        极值法
        取每列最大灰度值的行号作为中心位置，速度最快。
        """
        h, w = image.shape
        pts: List[Tuple[int, float]] = []
        for x in range(w):
            col = image[:, x]
            idx = int(col.argmax())
            if col[idx] > 10:
                pts.append((x, float(idx)))
        return pts

    def _steger(self, image: np.ndarray,
                sigma: float = 2.0,
                intensity_ratio: float = 0.10,
                search_radius: int = 8) -> List[Tuple[int, float]]:
        """
        Steger 亚像素法
        通过对 Hessian 矩阵特征值分析，计算垂直于激光线方向的二阶导数过零点，
        实现亚像素级别的中心线定位。

        Args:
            sigma: 高斯平滑标准差
            intensity_ratio: 有效像素强度阈值比例（相对全图最大值）
            search_radius: 在峰值行附近的搜索窗口半径
        """
        img_f = image.astype(np.float64)
        smoothed = cv2.GaussianBlur(img_f, (0, 0), sigma)

        Ix  = cv2.Sobel(smoothed, cv2.CV_64F, 1, 0, ksize=3)
        Iy  = cv2.Sobel(smoothed, cv2.CV_64F, 0, 1, ksize=3)
        Ixx = cv2.Sobel(Ix,  cv2.CV_64F, 1, 0, ksize=3)
        Iyy = cv2.Sobel(Iy,  cv2.CV_64F, 0, 1, ksize=3)
        Ixy = cv2.Sobel(Ix,  cv2.CV_64F, 0, 1, ksize=3)

        h, w = image.shape
        thr = float(smoothed.max()) * intensity_ratio
        pts: List[Tuple[int, float]] = []

        for col in range(1, w - 1):
            col_vals = smoothed[:, col]
            if float(col_vals.max()) < thr:
                continue
            peak_row = int(col_vals.argmax())
            r0 = max(1, peak_row - search_radius)
            r1 = min(h - 1, peak_row + search_radius + 1)

            best_y: Optional[float] = None
            best_resp = 0.0

            for row in range(r0, r1):
                hxx = Ixx[row, col]
                hxy = Ixy[row, col]
                hyy = Iyy[row, col]

                trace = hxx + hyy
                half  = trace * 0.5
                det   = hxx * hyy - hxy * hxy
                disc  = (half * half - det)
                if disc < 0:
                    disc = 0.0
                disc = disc ** 0.5

                lam1 = half + disc
                lam2 = half - disc
                lam  = lam1 if abs(lam1) >= abs(lam2) else lam2

                if abs(lam) < 1e-10:
                    continue

                if abs(hxy) > 1e-10:
                    nx, ny = hxy, lam - hxx
                else:
                    nx, ny = (0.0, 1.0) if abs(hxx) < abs(hyy) else (1.0, 0.0)

                norm = (nx * nx + ny * ny) ** 0.5
                if norm < 1e-10:
                    continue
                nx /= norm
                ny /= norm

                denom = nx * nx * hxx + 2.0 * nx * ny * hxy + ny * ny * hyy
                if abs(denom) < 1e-10:
                    continue
                t = -(nx * Ix[row, col] + ny * Iy[row, col]) / denom

                if abs(t) <= 0.5 and abs(lam) > best_resp:
                    best_resp = abs(lam)
                    best_y = row + t * ny

            if best_y is not None and 0.0 <= best_y < h:
                pts.append((col, best_y))

        return pts
