"""
workers.py

包含：
- 图片加载信号类 (QObject + pyqtSignal)
- 图片异步加载任务 (QRunnable 子类)

实现：
- 在线程池中执行 run()
- 使用 PIL.Image 打开与处理图片
- 生成原图与缩略图
- 通过 pyqtSignal.emit() 将 QImage 回传主线程
- 异常处理与空图回退
"""

import os

from PyQt6.QtCore import QRunnable, pyqtSignal, QObject
from PyQt6.QtGui import QImage
from PIL import Image

from core.image_utils import pil_to_qimage



class ImageLoadSignals(QObject):
    image_loaded = pyqtSignal(str, QImage, QImage, str)



class ImageLoadWorker(QRunnable):

    def __init__(self, path, raw_name, tid, callback_signal):
        super().__init__()
        self.path = path
        self.raw_name = raw_name
        self.tid = tid
        self.callback_signal = callback_signal

    def run(self):
        try:
            if os.path.exists(self.path):

                with Image.open(self.path) as pil:
                    pil.load()

                    # 原图
                    full_qimg = pil_to_qimage(pil)

                    # 缩略图
                    pil.thumbnail((60, 60), Image.Resampling.LANCZOS)

                    self.callback_signal.emit(
                        self.raw_name,
                        pil_to_qimage(pil),
                        full_qimg,
                        self.tid
                    )
            else:
                self.callback_signal.emit(
                    self.raw_name,
                    QImage(),
                    QImage(),
                    self.tid
                )

        except Exception:
            self.callback_signal.emit(
                self.raw_name,
                QImage(),
                QImage(),
                self.tid
            )
