#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
激光中心线检测软件 v2.0 - 主程序入口

使用说明:
    python main.py

新功能 (v2.0):
    - 现代深色主题GUI
    - 支持高斯/中值/双边滤波和CLAHE增强
    - 四种检测算法（含Steger亚像素法）
    - Matplotlib坐标曲线图表
    - 后台线程检测，界面不卡顿
    - 实时检测模式
    - 统计信息面板
    - CSV和Excel双格式导出
"""

import sys
from PyQt5.QtWidgets import QApplication
from laser_centerline_detection.gui import MainWindow


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("激光中心线检测软件 v2.0")
    app.setOrganizationName("Laser Detection")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
