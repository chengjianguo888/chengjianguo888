#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
激光中心线检测软件 - 主程序入口

使用说明:
    python main.py

功能特点:
    - 支持多种图像格式加载
    - 提供三种中心线检测算法
    - 图形化用户界面
    - 数据导出功能
"""

import sys
from PyQt5.QtWidgets import QApplication
from laser_centerline_detection.gui import MainWindow


def main():
    """主函数"""
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("激光中心线检测软件")
    app.setOrganizationName("Laser Detection")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
