# -*- coding: utf-8 -*-
"""
laserline.tests.test_detection — 检测引擎单元测试
"""

import sys
import os
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from laserline.detection.engine import (
    DetectionEngine, Algorithm, DetectionResult, PreprocessConfig
)


def _make_stripe(width=200, height=100, center_y=50, sigma=3.0) -> np.ndarray:
    """生成一条对角线激光条纹测试图像（灰度）。"""
    img = np.zeros((height, width), dtype=np.uint8)
    for x in range(width):
        cy = center_y + x * 0.1  # 略微倾斜
        cy = min(cy, height - 1)
        for y in range(height):
            d = abs(y - cy)
            v = int(255 * np.exp(-0.5 * (d / sigma) ** 2))
            img[y, x] = min(255, v)
    return img


class TestPreprocessConfig(unittest.TestCase):

    def test_default_values(self):
        cfg = PreprocessConfig()
        self.assertEqual(cfg.filter_type, "gaussian")
        self.assertEqual(cfg.kernel_size, 5)
        self.assertEqual(cfg.threshold, 0)
        self.assertFalse(cfg.clahe)


class TestDetectionResult(unittest.TestCase):

    def test_empty_result(self):
        r = DetectionResult()
        self.assertEqual(r.count, 0)
        self.assertFalse(r.is_valid())
        self.assertIsNone(r.y_min)
        self.assertIsNone(r.y_max)

    def test_filled_result(self):
        pts = [(i, float(50 + i * 0.1)) for i in range(100)]
        r = DetectionResult(points=pts, algorithm="gray_centroid", elapsed_ms=12.3)
        self.assertEqual(r.count, 100)
        self.assertTrue(r.is_valid())
        self.assertIsNotNone(r.y_min)
        self.assertIsNotNone(r.y_mean)
        self.assertIsNotNone(r.y_std)
        self.assertAlmostEqual(r.y_mean, np.mean([p[1] for p in pts]), places=6)


class TestDetectionEngine(unittest.TestCase):

    def setUp(self):
        self.engine = DetectionEngine()
        self.img = _make_stripe()

    # ── 预处理 ──

    def test_preprocess_returns_gray(self):
        bgr = np.stack([self.img] * 3, axis=-1)
        gray = self.engine.preprocess(bgr)
        self.assertEqual(gray.ndim, 2)

    def test_preprocess_gaussian(self):
        cfg = PreprocessConfig(filter_type="gaussian", kernel_size=5)
        out = self.engine.preprocess(self.img, cfg)
        self.assertEqual(out.shape, self.img.shape)

    def test_preprocess_median(self):
        cfg = PreprocessConfig(filter_type="median", kernel_size=5)
        out = self.engine.preprocess(self.img, cfg)
        self.assertEqual(out.shape, self.img.shape)

    def test_preprocess_bilateral(self):
        cfg = PreprocessConfig(filter_type="bilateral", kernel_size=5)
        out = self.engine.preprocess(self.img, cfg)
        self.assertEqual(out.shape, self.img.shape)

    def test_preprocess_clahe(self):
        cfg = PreprocessConfig(clahe=True)
        out = self.engine.preprocess(self.img, cfg)
        self.assertEqual(out.shape, self.img.shape)

    def test_preprocess_otsu(self):
        cfg = PreprocessConfig(threshold=0)
        out = self.engine.preprocess(self.img, cfg)
        self.assertEqual(out.shape, self.img.shape)

    def test_preprocess_fixed_threshold(self):
        cfg = PreprocessConfig(threshold=80)
        out = self.engine.preprocess(self.img, cfg)
        self.assertEqual(out.shape, self.img.shape)

    # ── 算法 ──

    def _assert_algo(self, algo: Algorithm):
        result = self.engine.run(self.img, algo)
        self.assertIsInstance(result, DetectionResult)
        self.assertTrue(result.is_valid(), f"{algo.value} 未检测到任何点")
        self.assertGreater(result.count, 50, f"{algo.value} 检测点数过少")
        self.assertGreater(result.elapsed_ms, 0)
        # Y 坐标应大致在 45~60 范围内（center_y=50 + 倾斜）
        for x, y in result.points:
            self.assertGreater(y, 30, f"{algo.value}: y={y} 偏低")
            self.assertLess(y, 75, f"{algo.value}: y={y} 偏高")

    def test_gray_centroid(self):
        self._assert_algo(Algorithm.GRAY_CENTROID)

    def test_gaussian_fit(self):
        self._assert_algo(Algorithm.GAUSSIAN_FIT)

    def test_peak(self):
        self._assert_algo(Algorithm.PEAK)

    def test_steger(self):
        self._assert_algo(Algorithm.STEGER)

    # ── 边界情况 ──

    def test_run_empty_image(self):
        result = self.engine.run(None, Algorithm.GRAY_CENTROID)
        self.assertFalse(result.is_valid())

    def test_run_3d_image_rejected(self):
        bgr = np.stack([self.img] * 3, axis=-1)
        result = self.engine.run(bgr, Algorithm.GRAY_CENTROID)
        self.assertFalse(result.is_valid())

    def test_run_all_black(self):
        black = np.zeros((50, 50), dtype=np.uint8)
        result = self.engine.run(black, Algorithm.GRAY_CENTROID)
        self.assertEqual(result.count, 0)

    # ── 批量处理 ──

    def test_run_batch(self):
        images = [(f"img_{i}.png", self.img) for i in range(3)]
        results = self.engine.run_batch(images, Algorithm.GRAY_CENTROID)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertTrue(r.is_valid())

    # ── 绘制 ──

    def test_draw(self):
        result = self.engine.run(self.img, Algorithm.GRAY_CENTROID)
        bgr = np.stack([self.img] * 3, axis=-1)
        out = self.engine.draw(bgr, result)
        self.assertEqual(out.shape, bgr.shape)


class TestDataExporter(unittest.TestCase):

    def setUp(self):
        self.pts = [(i, float(50 + i * 0.05)) for i in range(100)]

    def test_csv_export(self):
        from laserline.io.exporter import DataExporter
        exp = DataExporter()
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            ok = exp.to_csv(self.pts, path)
            self.assertTrue(ok)
            self.assertGreater(os.path.getsize(path), 0)
        finally:
            os.unlink(path)

    def test_excel_export(self):
        from laserline.io.exporter import DataExporter
        exp = DataExporter()
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = f.name
        try:
            ok = exp.to_excel(self.pts, path)
            self.assertTrue(ok)
            self.assertGreater(os.path.getsize(path), 0)
        finally:
            os.unlink(path)

    def test_json_export(self):
        import json
        from laserline.io.exporter import DataExporter
        exp = DataExporter()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
        try:
            ok = exp.to_json(self.pts, path)
            self.assertTrue(ok)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["count"], 100)
            self.assertIn("statistics", data)
            self.assertIn("points", data)
        finally:
            os.unlink(path)


class TestImageLoader(unittest.TestCase):

    def test_scan_empty_dir(self):
        from laserline.io.loader import ImageLoader
        with tempfile.TemporaryDirectory() as d:
            paths = ImageLoader.scan_directory(d)
            self.assertEqual(paths, [])

    def test_scan_with_images(self):
        import cv2
        from laserline.io.loader import ImageLoader
        with tempfile.TemporaryDirectory() as d:
            img = np.zeros((10, 10, 3), dtype=np.uint8)
            cv2.imwrite(os.path.join(d, "a.png"), img)
            cv2.imwrite(os.path.join(d, "b.jpg"), img)
            paths = ImageLoader.scan_directory(d)
            self.assertEqual(len(paths), 2)

    def test_save_load_roundtrip(self):
        import cv2
        from laserline.io.loader import ImageLoader
        img = np.random.randint(0, 256, (50, 60, 3), dtype=np.uint8)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name
        try:
            ok = ImageLoader.save(path, img)
            self.assertTrue(ok)
            loaded = ImageLoader.load(path)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.shape, img.shape)
        finally:
            os.unlink(path)


class TestConfig(unittest.TestCase):

    def test_load_defaults(self):
        from laserline import config
        cfg = config.load()
        self.assertIn("algorithm", cfg)
        self.assertIn("filter_type", cfg)
        self.assertIn("kernel_size", cfg)

    def test_save_and_reload(self):
        import json
        import tempfile
        from laserline import config
        orig_path = config._CONFIG_PATH
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".json", delete=False, mode="w"
            ) as f:
                config._CONFIG_PATH = f.name

            cfg = config.load()
            cfg["kernel_size"] = 11
            config.save(cfg)
            reloaded = config.load()
            self.assertEqual(reloaded["kernel_size"], 11)
        finally:
            if os.path.exists(config._CONFIG_PATH):
                os.unlink(config._CONFIG_PATH)
            config._CONFIG_PATH = orig_path


if __name__ == "__main__":
    unittest.main(verbosity=2)
