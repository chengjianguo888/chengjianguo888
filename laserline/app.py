#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
laserline/app.py — 应用程序入口

用法:
    python app.py

或通过项目根目录：
    python -m laserline
"""

import sys
from PyQt5.QtWidgets import QApplication
from laserline.ui.mainwindow import MainWindow


def main():
    """启动 LaserLine 应用程序"""
    app = QApplication(sys.argv)
    app.setApplicationName("LaserLine")
    app.setApplicationDisplayName("LaserLine — 激光中心线检测软件")
    app.setOrganizationName("LaserLine")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
