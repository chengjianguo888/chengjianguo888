# -*- coding: utf-8 -*-
"""
laserline.io.exporter — 数据导出器
支持 CSV / Excel / JSON 三种格式。
"""

from __future__ import annotations

import json
from typing import List, Tuple

import numpy as np
import pandas as pd


class DataExporter:
    """将中心线坐标导出为多种格式。"""

    # ─── 内部工具 ────────────────────────────────

    @staticmethod
    def _build_df(points: List[Tuple[int, float]]) -> pd.DataFrame:
        """将坐标列表构建为 DataFrame。"""
        df = pd.DataFrame(points, columns=["X坐标", "Y坐标"])
        df.insert(0, "序号", range(1, len(df) + 1))
        return df

    @staticmethod
    def _stats_df(points: List[Tuple[int, float]]) -> pd.DataFrame:
        """生成统计信息 DataFrame。"""
        ys = np.array([p[1] for p in points])
        rows = [
            ("检测点数", len(points)),
            ("Y 最小值", round(float(ys.min()), 4)),
            ("Y 最大值", round(float(ys.max()), 4)),
            ("Y 均值",   round(float(ys.mean()), 4)),
            ("Y 标准差", round(float(ys.std()), 4)),
            ("Y 极差",   round(float(ys.max() - ys.min()), 4)),
        ]
        return pd.DataFrame(rows, columns=["统计项", "数值"])

    # ─── 公开接口 ────────────────────────────────

    def to_csv(self, points: List[Tuple[int, float]], path: str) -> bool:
        """
        导出为 CSV（UTF-8-BOM，可直接用 Excel 打开）。

        Args:
            points: 中心线坐标列表
            path: 输出文件路径

        Returns:
            bool: 是否成功
        """
        try:
            self._build_df(points).to_csv(path, index=False, encoding="utf-8-sig")
            return True
        except Exception as exc:
            print(f"[DataExporter] CSV 导出失败: {exc}")
            return False

    def to_excel(self, points: List[Tuple[int, float]], path: str) -> bool:
        """
        导出为 Excel（.xlsx），包含"坐标数据"和"统计信息"两个工作表。

        Args:
            points: 中心线坐标列表
            path: 输出文件路径（.xlsx）

        Returns:
            bool: 是否成功
        """
        try:
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                self._build_df(points).to_excel(
                    writer, sheet_name="坐标数据", index=False
                )
                self._stats_df(points).to_excel(
                    writer, sheet_name="统计信息", index=False
                )
            return True
        except Exception as exc:
            print(f"[DataExporter] Excel 导出失败: {exc}")
            return False

    def to_json(self, points: List[Tuple[int, float]], path: str) -> bool:
        """
        导出为 JSON 格式（包含坐标列表和统计摘要）。

        Args:
            points: 中心线坐标列表
            path: 输出文件路径

        Returns:
            bool: 是否成功
        """
        try:
            ys = np.array([p[1] for p in points])
            data = {
                "count": len(points),
                "statistics": {
                    "y_min":  round(float(ys.min()), 4),
                    "y_max":  round(float(ys.max()), 4),
                    "y_mean": round(float(ys.mean()), 4),
                    "y_std":  round(float(ys.std()), 4),
                },
                "points": [{"x": int(x), "y": round(float(y), 4)} for x, y in points],
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as exc:
            print(f"[DataExporter] JSON 导出失败: {exc}")
            return False
