#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本 - 验证激光中心线检测软件安装是否正确

使用方法:
    python test_installation.py
"""

import sys
import os

# 确保可以导入项目模块
# 如果在 laser_centerline_detection 目录下运行，需要添加父目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def test_imports():
    """测试模块导入"""
    print("=" * 60)
    print("测试 1: 检查依赖包")
    print("=" * 60)
    
    required_packages = [
        ('cv2', 'opencv-python'),
        ('numpy', 'numpy'),
        ('scipy', 'scipy'),
        ('pandas', 'pandas'),
        ('matplotlib', 'matplotlib'),
        ('PyQt5', 'PyQt5')
    ]
    
    all_ok = True
    for module_name, package_name in required_packages:
        try:
            __import__(module_name)
            print(f"✓ {package_name:20s} 已安装")
        except ImportError:
            print(f"✗ {package_name:20s} 未安装")
            all_ok = False
    
    if not all_ok:
        print("\n请运行以下命令安装缺失的依赖:")
        print("pip install -r requirements.txt")
        return False
    
    print("\n所有依赖包已正确安装!\n")
    return True


def test_core_modules():
    """测试核心模块"""
    print("=" * 60)
    print("测试 2: 检查核心模块")
    print("=" * 60)
    
    try:
        from laser_centerline_detection.core import ImageProcessor, CenterlineDetector, DataExporter
        print("✓ 核心模块导入成功")
        
        # 测试实例化
        processor = ImageProcessor()
        detector = CenterlineDetector()
        exporter = DataExporter()
        print("✓ 核心类实例化成功")
        
        return True
    except Exception as e:
        print(f"✗ 核心模块测试失败: {e}")
        return False


def test_gui_modules():
    """测试 GUI 模块"""
    print("\n" + "=" * 60)
    print("测试 3: 检查 GUI 模块")
    print("=" * 60)
    
    try:
        from laser_centerline_detection.gui import MainWindow
        print("✓ GUI 模块导入成功")
        
        return True
    except Exception as e:
        print(f"✗ GUI 模块测试失败: {e}")
        return False


def test_algorithms():
    """测试算法功能"""
    print("\n" + "=" * 60)
    print("测试 4: 检查算法功能")
    print("=" * 60)
    
    try:
        import numpy as np
        from laser_centerline_detection.core import ImageProcessor, CenterlineDetector
        
        # 创建测试图像
        test_image = np.zeros((100, 100), dtype=np.uint8)
        # 添加一条简单的激光条纹
        for x in range(100):
            center_y = 50
            for y in range(40, 60):
                distance = abs(y - center_y)
                intensity = 255 * np.exp(-(distance**2) / (2 * 3**2))
                test_image[y, x] = min(255, int(intensity))
        
        # 测试检测器
        detector = CenterlineDetector()
        
        # 测试三种算法
        methods = [
            (CenterlineDetector.METHOD_GRAY_CENTROID, "灰度重心法"),
            (CenterlineDetector.METHOD_GAUSSIAN_FITTING, "高斯拟合法"),
            (CenterlineDetector.METHOD_MAX_VALUE, "极值法")
        ]
        
        for method, name in methods:
            points = detector.detect(test_image, method)
            if len(points) > 0:
                print(f"✓ {name:15s} 工作正常 (检测到 {len(points)} 个点)")
            else:
                print(f"⚠ {name:15s} 未检测到点")
        
        return True
    except Exception as e:
        print(f"✗ 算法功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "🔍 激光中心线检测软件 - 安装测试\n")
    
    results = []
    
    # 运行所有测试
    results.append(("依赖包", test_imports()))
    results.append(("核心模块", test_core_modules()))
    results.append(("GUI模块", test_gui_modules()))
    results.append(("算法功能", test_algorithms()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name:15s}: {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n" + "🎉 所有测试通过！软件已正确安装。")
        print("\n运行以下命令启动软件:")
        print("    python main.py")
        print("\n或者:")
        print("    cd laser_centerline_detection")
        print("    python main.py")
        return 0
    else:
        print("\n" + "⚠️  部分测试失败，请检查上述错误信息。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
