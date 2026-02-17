# -*- coding: utf-8 -*-
"""
数据导出模块
将中心线坐标数据导出为CSV文件
"""

import pandas as pd
from typing import List, Tuple


class DataExporter:
    """数据导出器类"""
    
    def __init__(self):
        """初始化导出器"""
        pass
    
    def export_to_csv(self, centerline_points: List[Tuple[int, float]], 
                     file_path: str) -> bool:
        """
        将中心线坐标导出为CSV文件
        
        Args:
            centerline_points: 中心线坐标点列表 [(x, y), ...]
            file_path: 输出文件路径
            
        Returns:
            bool: 是否成功导出
        """
        try:
            if not centerline_points:
                return False
            
            # 转换为DataFrame
            df = pd.DataFrame(centerline_points, columns=['X坐标', 'Y坐标'])
            
            # 添加序号列
            df.insert(0, '序号', range(1, len(df) + 1))
            
            # 导出为CSV
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            return True
        except Exception as e:
            print(f"导出CSV失败: {str(e)}")
            return False
    
    def get_dataframe(self, centerline_points: List[Tuple[int, float]]) -> pd.DataFrame:
        """
        将中心线坐标转换为DataFrame
        
        Args:
            centerline_points: 中心线坐标点列表
            
        Returns:
            pd.DataFrame: 数据框
        """
        if not centerline_points:
            return pd.DataFrame(columns=['序号', 'X坐标', 'Y坐标'])
        
        df = pd.DataFrame(centerline_points, columns=['X坐标', 'Y坐标'])
        df.insert(0, '序号', range(1, len(df) + 1))
        
        return df
