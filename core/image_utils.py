"""
image_utils.py

包含：
- 图像格式转换工具函数 (PIL.Image → QImage)

实现：
- 统一转换为 RGBA 模式 (Image.convert)
- 通过 tobytes("raw", "RGBA") 获取底层字节数据
- 使用 QImage 构造函数创建 Format_RGBA8888 图像
- 调用 .copy() 解除与原始内存的引用绑定

"""

from PyQt6.QtGui import QImage


def pil_to_qimage(pil_img):
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")

    data = pil_img.tobytes("raw", "RGBA")

    return QImage(
        data,
        pil_img.size[0],
        pil_img.size[1],
        QImage.Format.Format_RGBA8888
    ).copy()