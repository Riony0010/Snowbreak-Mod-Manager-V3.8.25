"""
main.py

包含：
- 程序入口函数 main()
- Qt 高 DPI 缩放策略设置
- QApplication 初始化与窗口启动
- 主窗口 ModManager3 启动与事件循环管理
"""

import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from UI import ModManager3

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    win = ModManager3()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()