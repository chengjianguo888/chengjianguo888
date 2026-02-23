# -*- coding: utf-8 -*-
"""
数据导出模块
将中心线坐标数据导出为 CSV / Excel 文件
"""

import pandas as pd
from typing import List, Tuple


class DataExporter:
    """数据导出器类"""

    def __init__(self):
        """初始化导出器"""
        pass

    def _to_dataframe(self, centerline_points: List[Tuple[int, float]]) -> pd.DataFrame:
        """将坐标列表转换为 DataFrame"""
        if not centerline_points:
            return pd.DataFrame(columns=['序号', 'X坐标', 'Y坐标'])
        df = pd.DataFrame(centerline_points, columns=['X坐标', 'Y坐标'])
        df.insert(0, '序号', range(1, len(df) + 1))
        return df

    def export_to_csv(self, centerline_points: List[Tuple[int, float]],
                      file_path: str) -> bool:
        """
        将中心线坐标导出为 CSV 文件

        Args:
            centerline_points: 中心线坐标点列表 [(x, y), ...]
            file_path: 输出文件路径

        Returns:
            bool: 是否成功导出
        """
        try:
            if not centerline_points:
                return False
            df = self._to_dataframe(centerline_points)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            return True
        except Exception as e:
            print(f"导出CSV失败: {str(e)}")
            return False

    def export_to_excel(self, centerline_points: List[Tuple[int, float]],
                        file_path: str) -> bool:
        """
        将中心线坐标导出为 Excel 文件（.xlsx）

        Args:
            centerline_points: 中心线坐标点列表 [(x, y), ...]
            file_path: 输出文件路径

        Returns:
            bool: 是否成功导出
        """
        try:
            if not centerline_points:
                return False
            df = self._to_dataframe(centerline_points)

            # 统计信息
            import numpy as np
            ys = df['Y坐标'].values
            stats = pd.DataFrame({
                '统计项': ['点数', 'Y最小值', 'Y最大值', 'Y均值', 'Y标准差'],
                '数值': [
                    len(centerline_points),
                    round(float(np.min(ys)), 4),
                    round(float(np.max(ys)), 4),
                    round(float(np.mean(ys)), 4),
                    round(float(np.std(ys)), 4),
                ]
            })

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='中心线坐标', index=False)
                stats.to_excel(writer, sheet_name='统计信息', index=False)
            return True
        except Exception as e:
            print(f"导出Excel失败: {str(e)}")
            return False

    def get_dataframe(self, centerline_points: List[Tuple[int, float]]) -> pd.DataFrame:
        """
        将中心线坐标转换为 DataFrame

        Args:
            centerline_points: 中心线坐标点列表

        Returns:
            pd.DataFrame: 数据框
        """
        return self._to_dataframe(centerline_points)
