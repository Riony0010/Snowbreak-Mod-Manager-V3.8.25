"""
widgets.py

包含：
- 自定义 QStyledItemDelegate
  (重写 initStyleOption() / setEditorData() / createEditor()
   控制文本颜色与单元格编辑行为)

- 可拖拽预览 QLabel
  (使用 QTimer 实现悬停延迟
   重写 enterEvent() / leaveEvent()
   实现 dragEnterEvent() / dropEvent() 处理图片拖拽)
"""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QLabel, QStyledItemDelegate, QLineEdit

from constants import COL_CAT, ROLE_ITEM_TYPE


class CustomDelegate(QStyledItemDelegate):

    # ---------- 文本颜色控制 ----------
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)

        foreground_data = index.data(Qt.ItemDataRole.ForegroundRole)
        color = QColor(foreground_data) if foreground_data else QColor("#EEEEEE")

        for role in (
            QPalette.ColorRole.HighlightedText,
            QPalette.ColorRole.Text,
            QPalette.ColorRole.WindowText,
        ):
            option.palette.setColor(QPalette.ColorGroup.All, role, color)

    # ---------- 编辑文本处理 ----------
    def setEditorData(self, editor, index):
        text = index.model().data(index, Qt.ItemDataRole.EditRole)

        if text.startswith("📂 "):
            text = text.replace("📂 ", "")

        editor.setText(text)

    # ---------- 控制哪些单元格可编辑 ----------
    def createEditor(self, parent, option, index):
        item = self.parent().itemFromIndex(index)
        if not item:
            return None

        col = index.column()
        i18n = self.parent().window().i18n
        item_type = item.data(COL_CAT, ROLE_ITEM_TYPE)

        if item_type == "folder":
            cat_text = item.text(COL_CAT).replace("📂 ", "").strip()
            if col != COL_CAT or cat_text == i18n.t("cat_uncategorized"):
                return None

        elif item_type == "file":
            from constants import COL_NAME
            if col != COL_NAME:
                return None

        else:
            return None

        return QLineEdit(parent)


# =========================
# Drop Preview Label
# =========================
class DropLabel(QLabel):

    def __init__(self, pak_name, rel_dir, parent_mgr):
        super().__init__("...")

        self.pak_name = pak_name
        self.rel_dir = rel_dir
        self.mgr = parent_mgr

        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background: #2d2d2d; "
            "border-radius: 5px; "
            "color: #777; "
            "border: 1px dashed #444;"
        )

        # ---------- 悬停定时器 ----------
        from constants import HOVER_DELAY_MS

        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(
            lambda: self.mgr.show_large_preview(
                self.pak_name,
                self.mapToGlobal(self.rect().topRight())
            )
        )

    # ---------- 鼠标事件 ----------
    def enterEvent(self, event):
        from constants import HOVER_DELAY_MS
        self.hover_timer.start(HOVER_DELAY_MS)

    def leaveEvent(self, event):
        self.hover_timer.stop()
        self.mgr.preview_win.hide()

    # ---------- 拖拽事件 ----------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.mgr.handle_img_drop(
                self.pak_name,
                self.rel_dir,
                urls[0].toLocalFile()
            )