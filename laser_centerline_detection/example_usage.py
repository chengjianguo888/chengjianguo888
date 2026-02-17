#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编程方式使用示例

演示如何在代码中使用激光中心线检测模块
"""

import sys
import os
import tempfile

# 添加父目录到路径以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from laser_centerline_detection.core import ImageProcessor, CenterlineDetector, DataExporter


def main():
    """主函数 - 演示完整的检测流程"""
    
    print("=" * 60)
    print("激光中心线检测 - 编程示例")
    print("=" * 60)
    
    # 1. 初始化处理器
    print("\n步骤 1: 初始化模块")
    processor = ImageProcessor()
    detector = CenterlineDetector()
    exporter = DataExporter()
    print("✓ 模块初始化完成")
    
    # 2. 加载图像
    print("\n步骤 2: 加载图像")
    # 构建可靠的图像路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(script_dir, "sample_images", "test_laser_stripe.png")
    
    if not os.path.exists(image_path):
        print(f"✗ 图像文件不存在: {image_path}")
        print("请确保在 laser_centerline_detection 目录下运行此脚本")
        return
    
    if processor.load_image(image_path):
        print(f"✓ 图像加载成功: {image_path}")
    else:
        print("✗ 图像加载失败")
        return
    
    # 3. 应用预处理
    print("\n步骤 3: 应用预处理")
    kernel_size = 5
    processed_image = processor.apply_gaussian_filter(kernel_size)
    print(f"✓ 已应用高斯滤波 (核大小: {kernel_size})")
    
    # 4. 使用不同算法检测中心线
    print("\n步骤 4: 检测中心线")
    
    # 方法 1: 灰度重心法
    print("\n  方法 1: 灰度重心法")
    points_centroid = detector.detect(
        processed_image, 
        CenterlineDetector.METHOD_GRAY_CENTROID
    )
    print(f"  ✓ 检测到 {len(points_centroid)} 个点")
    
    # 方法 2: 高斯拟合法
    print("\n  方法 2: 高斯拟合法")
    points_gaussian = detector.detect(
        processed_image,
        CenterlineDetector.METHOD_GAUSSIAN_FITTING
    )
    print(f"  ✓ 检测到 {len(points_gaussian)} 个点")
    
    # 方法 3: 极值法
    print("\n  方法 3: 极值法")
    points_max = detector.detect(
        processed_image,
        CenterlineDetector.METHOD_MAX_VALUE
    )
    print(f"  ✓ 检测到 {len(points_max)} 个点")
    
    # 5. 显示检测结果
    print("\n步骤 5: 分析结果")
    
    # 使用灰度重心法的结果进行后续分析
    if points_centroid:
        x_coords = [x for x, y in points_centroid]
        y_coords = [y for x, y in points_centroid]
        
        print(f"  X 坐标范围: {min(x_coords)} - {max(x_coords)}")
        print(f"  Y 坐标范围: {min(y_coords):.2f} - {max(y_coords):.2f}")
        print(f"  平均 Y 坐标: {sum(y_coords)/len(y_coords):.2f}")
        
        # 显示前10个点
        print("\n  前 10 个坐标点:")
        for i, (x, y) in enumerate(points_centroid[:10]):
            print(f"    点 {i+1:3d}: ({x:4d}, {y:7.2f})")
    
    # 6. 保存结果图像
    print("\n步骤 6: 保存结果")
    
    # 在原图上绘制中心线
    original_image = processor.get_image('original')
    result_image = detector.draw_centerline(
        original_image.copy(),
        color=(0, 255, 0),  # 绿色
        thickness=2
    )
    
    # 保存结果图像（使用跨平台临时目录）
    temp_dir = tempfile.gettempdir()
    output_image_path = os.path.join(temp_dir, "laser_detection_result.png")
    import cv2
    if cv2.imwrite(output_image_path, result_image):
        print(f"✓ 结果图像已保存: {output_image_path}")
    
    # 7. 导出数据
    print("\n步骤 7: 导出数据")
    output_csv_path = os.path.join(temp_dir, "laser_centerline_data.csv")
    
    if exporter.export_to_csv(points_centroid, output_csv_path):
        print(f"✓ 数据已导出为 CSV: {output_csv_path}")
        
        # 读取并显示前5行
        print("\n  CSV 文件内容预览:")
        with open(output_csv_path, 'r', encoding='utf-8-sig') as f:
            for i, line in enumerate(f):
                if i >= 6:  # 显示表头 + 前5行数据
                    break
                print(f"    {line.strip()}")
    
    print("\n" + "=" * 60)
    print("检测完成！")
    print("=" * 60)
    
    # 8. 使用 pandas 分析数据
    print("\n额外: 使用 pandas 分析导出的数据")
    try:
        import pandas as pd
        df = pd.read_csv(output_csv_path)
        print("\n数据统计:")
        print(df.describe())
    except Exception as e:
        print(f"无法使用 pandas 分析: {e}")


def simple_example():
    """简单示例 - 最少代码实现检测"""
    
    print("\n" + "=" * 60)
    print("简化示例 - 最少代码")
    print("=" * 60 + "\n")
    
    # 构建图像路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(script_dir, "sample_images", "test_laser_stripe.png")
    
    # 三行代码完成检测
    processor = ImageProcessor()
    processor.load_image(image_path)
    
    detector = CenterlineDetector()
    points = detector.detect(processor.get_image('gray'), CenterlineDetector.METHOD_GRAY_CENTROID)
    
    print(f"检测到 {len(points)} 个中心线点")
    print(f"示例坐标: {points[0] if points else 'N/A'}")


if __name__ == '__main__':
    # 运行完整示例
    main()
    
    # 运行简化示例
    simple_example()
