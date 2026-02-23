import sys
import os
import shutil
from PyQt6.QtCore import Qt, QSize, QTimer, QThreadPool
from PyQt6.QtGui import QPixmap, QColor, QIcon, QKeyEvent, QFontMetrics
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QTreeWidget, QTreeWidgetItem, 
                             QPushButton, QLabel, QFileDialog, QMessageBox, 
                             QHeaderView, QLineEdit, QAbstractItemView, QCheckBox, 
                             QFrame, QInputDialog, QTreeWidgetItemIterator, QDialog)

from constants import (VERSION, COL_CAT, COL_CHECK, COL_PREVIEW, COL_NAME, COL_ACTION,
                       COLUMN_PROPORTIONS, ROLE_REL_PATH, ROLE_ITEM_TYPE, ROLE_DEPTH,
                       CONFIG_FILE, MAX_PREVIEW_SIZE)
from config import ConfigManager
from languages import I18nManager
from UI.widgets import CustomDelegate, DropLabel
from UI.styles import STYLE_TEMPLATE, ICON_CLOSED_PATH, ICON_OPEN_PATH
from core.mod_manager import ModManagerCore
from core.workers import ImageLoadSignals, ImageLoadWorker


class ModManager3(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager(CONFIG_FILE)
        self.config.load()
        
        self.repo_path = self.config.repo_path
        self.game_path = self.config.game_path
        self.folder_states = self.config.folder_states
        self.is_batch_op = False
        self.i18n = I18nManager(self.config.lang)
        self.known_mods = self.config.known_mods

        base_path = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.abspath(".")
        icon_path = os.path.join(base_path, "app.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.zoom_level = 1.0
        self.base_font_size = 14
        self.setWindowTitle(f"{self.i18n.t('window_title')} {VERSION}")

        ws = self.config.window_size if isinstance(self.config.window_size, list) else [1200, 850]
        if len(ws) == 2 and ws[0] > 100 and ws[1] > 100:
            self.resize(ws[0], ws[1])
        else:
            self.resize(1200, 850)
        self.qimage_cache, self.selected_mods = {}, set()
        self.is_first_scan, self.all_mods_in_repo, self.is_all_selected = True, set(), False
        self.task_counter = 0
        self.thread_pool = QThreadPool()
        self.image_load_signals = ImageLoadSignals()
        self.image_load_signals.image_loaded.connect(self.on_img_loaded)
        self.preview_win = QWidget()
        self.preview_win.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.preview_win_lbl = QLabel(self.preview_win)
        self.item_map = {}
        
        self.mod_core = ModManagerCore(self.repo_path, self.game_path)
        
        self.init_ui()
        self.apply_zoom()
    def sync_selection_to_checkboxes(self):
        if self.is_batch_op:
            return

        self.is_batch_op = True
        self.selected_mods.clear()

        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            item_type = item.data(COL_CAT, ROLE_ITEM_TYPE)

            if item_type == "file":
                is_sel = item.isSelected()
                w = self.tree.itemWidget(item, COL_CHECK)
                if w:
                    cb = w.findChild(QCheckBox)
                    if cb:
                        cb.blockSignals(True)
                        cb.setChecked(is_sel)
                        cb.blockSignals(False)

                if is_sel:
                    rel = item.data(COL_CAT, ROLE_REL_PATH)
                    pak = item.text(COL_NAME)
                    self.selected_mods.add((rel, pak))
            it += 1

        it = QTreeWidgetItemIterator(self.tree)
        while it.value():
            item = it.value()
            if item.data(COL_CAT, ROLE_ITEM_TYPE) == "file":
                self.update_ancestor_checkboxes(item)
            it += 1

        self.sync_all_sel_state()
        self.is_batch_op = False
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        path_bar = QFrame()
        path_bar.setObjectName("PathBar")
        path_bar_layout = QGridLayout(path_bar)
        
        self.game_title_lbl = QLabel(self.i18n.t('path_game_paks') + ":")
        self.game_title_lbl.setObjectName("PathLabel")
        self.repo_title_lbl = QLabel(self.i18n.t('path_mod_repo') + ":")
        self.repo_title_lbl.setObjectName("PathLabel")
        
        self.game_path_lbl = QLabel()
        self.game_path_lbl.setObjectName("PathLabel")
        self.repo_path_lbl = QLabel()
        self.repo_path_lbl.setObjectName("PathLabel")
        
        self.game_open_btn = QPushButton(self.i18n.t("btn_open"))
        self.game_open_btn.clicked.connect(lambda: self.open_folder_explorer(self.game_path))
        self.repo_open_btn = QPushButton(self.i18n.t("btn_open"))
        self.repo_open_btn.clicked.connect(lambda: self.open_folder_explorer(self.repo_path))
        self.game_btn = QPushButton(self.i18n.t("btn_set_game"))
        self.game_btn.clicked.connect(self.select_game)
        self.repo_btn = QPushButton(self.i18n.t("btn_set_repo"))
        self.repo_btn.clicked.connect(self.select_repo)

        path_bar_layout.addWidget(self.game_title_lbl, 0, 0)
        path_bar_layout.addWidget(self.game_path_lbl, 0, 1)
        path_bar_layout.addWidget(self.game_open_btn, 0, 2)
        path_bar_layout.addWidget(self.game_btn, 0, 3)
        
        path_bar_layout.addWidget(self.repo_title_lbl, 1, 0)
        path_bar_layout.addWidget(self.repo_path_lbl, 1, 1)
        path_bar_layout.addWidget(self.repo_open_btn, 1, 2)
        path_bar_layout.addWidget(self.repo_btn, 1, 3)
        
        path_bar_layout.setColumnStretch(1, 1)
        layout.addWidget(path_bar)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(self.i18n.t("search_placeholder"))
        self.search_bar.textChanged.connect(self.filter_list)
        layout.addWidget(self.search_bar)

        batch_layout = QHBoxLayout()
        self.all_sel_btn = QPushButton(self.i18n.t("btn_select_all"))
        self.all_sel_btn.clicked.connect(self.toggle_all_selection)
        batch_layout.addWidget(self.all_sel_btn)
        
        self.btn_batch_en = QPushButton(self.i18n.t("btn_batch_enable"))
        self.btn_batch_en.clicked.connect(lambda: self.exec_batch(True))
        batch_layout.addWidget(self.btn_batch_en)
        
        self.btn_batch_dis = QPushButton(self.i18n.t("btn_batch_disable"))
        self.btn_batch_dis.clicked.connect(lambda: self.exec_batch(False))
        batch_layout.addWidget(self.btn_batch_dis)
        
        self.btn_batch_move = QPushButton(self.i18n.t("btn_batch_move"))
        self.btn_batch_move.clicked.connect(self.batch_move_mods)
        batch_layout.addWidget(self.btn_batch_move)
        
        self.btn_batch_del = QPushButton(self.i18n.t("btn_delete"))
        self.btn_batch_del.setObjectName("btn_delete")
        self.btn_batch_del.clicked.connect(self.batch_delete_logic)
        batch_layout.addWidget(self.btn_batch_del)
        batch_layout.addStretch()
        
        self.conflict_label = QLabel("")
        self.conflict_label.setStyleSheet("color: #FF4444; font-weight: bold; margin-right: 10px;")
        batch_layout.addWidget(self.conflict_label)

        self.selection_label = QLabel("")
        self.selection_label.setStyleSheet("color: #FFFFFF; font-weight: bold; margin-right: 10px;")
        batch_layout.addWidget(self.selection_label)
        
        self.btn_new = QPushButton(self.i18n.t("btn_new_folder"))
        self.btn_new.clicked.connect(self.create_folder)
        self.btn_new.setStyleSheet("background-color: #2E5A2E;")
        batch_layout.addWidget(self.btn_new)

        self.lang_btn = QPushButton(self.i18n.t("btn_lang_toggle"))
        self.lang_btn.clicked.connect(self.toggle_language)
        self.lang_btn.setStyleSheet("background-color: #444;")
        batch_layout.addWidget(self.lang_btn)
        
        self.btn_ref = QPushButton(self.i18n.t("btn_refresh"))
        self.btn_ref.clicked.connect(self.manual_refresh_action)
        batch_layout.addWidget(self.btn_ref)
        layout.addLayout(batch_layout)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(5)
        self.update_tree_headers()
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(20)
        self.tree.header().setStretchLastSection(True)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.tree.setItemDelegate(CustomDelegate(self.tree))
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.itemChanged.connect(self.on_item_data_changed)
        self.tree.setUniformRowHeights(True)
        
        self.tree.itemSelectionChanged.connect(self.sync_selection_to_checkboxes)

        self.tree.itemExpanded.connect(self.update_single_folder_state)
        self.tree.itemCollapsed.connect(self.update_single_folder_state)

        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.header().setSectionsMovable(False)
        self.tree.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.tree.setSortingEnabled(False)
        self.tree.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tree.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.tree)

    def update_single_folder_state(self, item):
        item_type = item.data(COL_CAT, ROLE_ITEM_TYPE)
        if item_type == "folder":
            rel_path = item.data(COL_CAT, ROLE_REL_PATH)
            if rel_path:
                self.folder_states[rel_path] = item.isExpanded()

    def update_tree_headers(self):
        self.tree.setHeaderLabels([
            self.i18n.t("header_folder"), "", self.i18n.t("header_preview"), 
            self.i18n.t("header_name"), self.i18n.t("header_action")
        ])

    def _dialog_window_flags(self):
        return (
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )

    def _apply_dialog_chrome(self, dialog, title):
        dialog.setWindowTitle(title)
        dialog.setWindowFlags(self._dialog_window_flags())
        dialog.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, False)
        dialog.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)

        fm = QFontMetrics(dialog.font())
        title_w = fm.horizontalAdvance(title)
        min_w = max(420, title_w + 180)
        dialog.setMinimumWidth(min_w)
        if hasattr(dialog, "setSizeGripEnabled"):
            dialog.setSizeGripEnabled(True)

    def toggle_language(self):
        new_lang = "en" if self.i18n.current_lang == "zh_CN" else "zh_CN"
        self.i18n.load_language(new_lang)
        self.config.lang = new_lang
        self.save_cfg()
        
        self.setWindowTitle(f"{self.i18n.t('window_title')} {VERSION}")
        self.game_title_lbl.setText(self.i18n.t('path_game_paks') + ":")
        self.repo_title_lbl.setText(self.i18n.t('path_mod_repo') + ":")
        self.game_open_btn.setText(self.i18n.t("btn_open"))
        self.repo_open_btn.setText(self.i18n.t("btn_open"))
        self.game_btn.setText(self.i18n.t("btn_set_game"))
        self.repo_btn.setText(self.i18n.t("btn_set_repo"))
        self.search_bar.setPlaceholderText(self.i18n.t("search_placeholder"))
        self.all_sel_btn.setText(self.i18n.t("btn_select_all" if not self.is_all_selected else "btn_deselect_all"))
        self.btn_batch_en.setText(self.i18n.t("btn_batch_enable"))
        self.btn_batch_dis.setText(self.i18n.t("btn_batch_disable"))
        self.btn_batch_move.setText(self.i18n.t("btn_batch_move"))
        self.btn_batch_del.setText(self.i18n.t("btn_delete"))
        self.btn_new.setText(self.i18n.t("btn_new_folder"))
        self.btn_ref.setText(self.i18n.t("btn_refresh"))
        self.lang_btn.setText(self.i18n.t("btn_lang_toggle"))
        
        self.update_tree_headers()
        self.apply_zoom()
        self.refresh_data()
        self.sync_all_sel_state()

    def open_folder_explorer(self, path):
        if not path or not os.path.exists(path):
            return
        if sys.platform == 'win32':
            os.startfile(os.path.normpath(path))
        else:
            import subprocess
            subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', path])

    def manual_refresh_action(self):
        for r, p in self.all_mods_in_repo:
            self.known_mods.add(p)
        self.save_cfg()
        
        self.selected_mods.clear()
        self.is_all_selected = False
        self.refresh_data()

    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Equal:
                self.change_zoom(0.1)
            elif event.key() == Qt.Key.Key_Minus:
                self.change_zoom(-0.1)
            elif event.key() == Qt.Key.Key_0:
                self.zoom_level = 1.0
                self.apply_zoom()
        super().keyPressEvent(event)

    def change_zoom(self, delta):
        new_zoom = self.zoom_level + delta
        if 0.5 <= new_zoom <= 2.5:
            self.zoom_level = new_zoom
            self.apply_zoom()

    def apply_zoom(self):
        f = int(self.base_font_size * self.zoom_level)
        padding = int(2 * self.zoom_level)
        item_h = int(68 * self.zoom_level)
        btn_v_p = int(6 * self.zoom_level)
        btn_h_p = int(12 * self.zoom_level)
        small_f = int(13 * self.zoom_level)
        scroll_w = int(12 * self.zoom_level)
        scroll_r = int(6 * self.zoom_level)

        check_s = int(20 * self.zoom_level)
        branch_s = int(20 * self.zoom_level)


        try:
            new_qss = STYLE_TEMPLATE.format(
                font_size=f, 
                padding=padding, 
                item_height=item_h,
                btn_v_padding=btn_v_p, 
                btn_h_padding=btn_h_p,
                check_size=check_s,
                branch_size=branch_s,
                small_font=small_f,
                scroll_width=scroll_w, 
                scroll_radius=scroll_r,
                branch_closed=ICON_CLOSED_PATH, 
                branch_open=ICON_OPEN_PATH
            )
            self.setStyleSheet(new_qss)
        except KeyError as e:
            print(self.i18n.t("log_style_format_failed", e))

        base_title_w = 150 if self.i18n.current_lang == "en" else 115
        self.game_title_lbl.setFixedWidth(int(base_title_w * self.zoom_level))
        self.repo_title_lbl.setFixedWidth(int(base_title_w * self.zoom_level))
        
        min_btn_w = int(100 * self.zoom_level)
        for btn in [self.game_open_btn, self.repo_open_btn, self.game_btn, self.repo_btn]:
            btn.setMinimumWidth(min_btn_w)
            btn.setMaximumWidth(250)

        self.refresh_data()

    def wrap_center(self, widget, height=None):
        if height is None:
            height = int(66 * self.zoom_level)
        c = QWidget()
        c.setFixedHeight(height)
        l = QHBoxLayout(c)
        l.setContentsMargins(8, 0, 8, 0)
        l.setSpacing(0)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(widget)
        return c

    def get_pak_counts(self):
        counts = {}
        if not self.all_mods_in_repo:
            return counts
        for rel_path, pak_name in self.all_mods_in_repo:
            counts[pak_name] = counts.get(pak_name, 0) + 1
        return counts
    
    def get_item_checkbox(self, item):
        w = self.tree.itemWidget(item, COL_CHECK)
        if w:
            return w.findChild(QCheckBox)
        return None

    def update_ancestor_checkboxes(self, item):
        parent = item.parent()
        if not parent: return

        all_checked = True
        child_count = parent.childCount()
        
        for i in range(child_count):
            child = parent.child(i)
            cb = self.get_item_checkbox(child)
            if not cb or not cb.isChecked():
                all_checked = False
                break
        
        parent_cb = self.get_item_checkbox(parent)
        if parent_cb:
            parent_cb.blockSignals(True)
            parent_cb.setChecked(all_checked)
            parent_cb.blockSignals(False)
            

    def refresh_data(self):
        self.mod_core = ModManagerCore(self.repo_path, self.game_path)
        
        scroll_pos = self.tree.verticalScrollBar().value()
        not_set_html = f'<span style="color: #FF4444;">{self.i18n.t("not_set")}</span>'
        self.game_path_lbl.setText(f"{self.game_path if self.game_path else not_set_html}")
        self.repo_path_lbl.setText(f"{self.repo_path if self.repo_path else not_set_html}")

        if not self.repo_path or not self.game_path:
            return
            
        self.qimage_cache.clear()
        
        self.tree.blockSignals(True)
        self.tree.clear()
        self.item_map.clear()
        self.all_mods_in_repo.clear()
        
        game_files = self.mod_core.get_game_files()
        uncat_key = self.i18n.t("cat_uncategorized")
        
        row_h = int(68 * self.zoom_level)

        root_paks, root_dirs = self.mod_core.scan_repository()

        if root_paks:
            uncat_item = QTreeWidgetItem(self.tree)
            uncat_display = f"📂 {uncat_key}"
            uncat_item.setText(COL_CAT, uncat_display)
            uncat_item.setData(COL_CAT, Qt.ItemDataRole.UserRole, uncat_display)
            uncat_item.setData(COL_CAT, ROLE_ITEM_TYPE, "folder")
            uncat_item.setData(COL_CAT, ROLE_REL_PATH, uncat_key)
            uncat_item.setData(COL_CAT, ROLE_DEPTH, 0)
            
            uncat_item.setFlags(uncat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            uncat_item.setExpanded(self.folder_states.get(uncat_key, True))
            
            self._add_folder_checkbox(uncat_item, row_h, uncat_key)

            for pak in root_paks:
                self.all_mods_in_repo.add((uncat_key, pak))
                self._add_pak_item(uncat_item, pak, uncat_key, game_files, row_h)

        for dir_name in root_dirs:
            cat_item = QTreeWidgetItem(self.tree)
            cat_display = f"📂 {dir_name}"
            cat_item.setText(COL_CAT, cat_display)
            cat_item.setData(COL_CAT, Qt.ItemDataRole.UserRole, cat_display)
            cat_item.setData(COL_CAT, ROLE_ITEM_TYPE, "folder")
            cat_item.setData(COL_CAT, ROLE_REL_PATH, dir_name)
            cat_item.setData(COL_CAT, ROLE_DEPTH, 1)
            cat_item.setFlags(cat_item.flags() | Qt.ItemFlag.ItemIsEditable)
            
            is_expanded = self.folder_states.get(dir_name, True)
            cat_item.setExpanded(is_expanded)
            self._add_folder_checkbox(cat_item, row_h, dir_name)

            full_path = os.path.join(self.repo_path, dir_name)
            sub_paks, sub_dirs = self.mod_core.scan_directory(full_path)
                
            for pak in sub_paks:
                self.all_mods_in_repo.add((dir_name, pak))
                self._add_pak_item(cat_item, pak, dir_name, game_files, row_h)
            
            for sub_dir in sub_dirs:
                sub_rel_path = os.path.join(dir_name, sub_dir)
                sub_item = QTreeWidgetItem(cat_item)
                sub_display = f"📂 {sub_dir}"
                sub_item.setText(COL_CAT, sub_display)
                sub_item.setData(COL_CAT, Qt.ItemDataRole.UserRole, sub_display)
                sub_item.setData(COL_CAT, ROLE_ITEM_TYPE, "folder")
                sub_item.setData(COL_CAT, ROLE_REL_PATH, sub_rel_path)
                sub_item.setData(COL_CAT, ROLE_DEPTH, 2)
                sub_item.setFlags(sub_item.flags() | Qt.ItemFlag.ItemIsEditable)
                
                sub_expanded = self.folder_states.get(sub_rel_path, False)
                sub_item.setExpanded(sub_expanded)
                self._add_folder_checkbox(sub_item, row_h, sub_rel_path)
                
                sub_full_path = os.path.join(self.repo_path, sub_rel_path)
                sub_paks2, _ = self.mod_core.scan_directory(sub_full_path)
                for f in sub_paks2:
                    self.all_mods_in_repo.add((sub_rel_path, f))
                    self._add_pak_item(sub_item, f, sub_rel_path, game_files, row_h)

        if self.is_first_scan:
            if not self.known_mods and self.all_mods_in_repo:
                 for r, p in self.all_mods_in_repo:
                     self.known_mods.add(p)
                 self.save_cfg()
            self.is_first_scan = False

        counts = self.get_pak_counts()
        conflict_groups = sum(1 for pak_name in counts if counts[pak_name] > 1)
        self.conflict_label.setText(self.i18n.t("conflict_warn", conflict_groups) if conflict_groups > 0 else "")
        
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if item.data(COL_CAT, ROLE_ITEM_TYPE) == "file":
                pak = item.text(COL_NAME)
                if counts.get(pak, 0) > 1:
                    item.setForeground(COL_NAME, QColor("#FF4444"))
                elif pak not in self.known_mods:
                    item.setForeground(COL_NAME, QColor("#00A3FF"))
                else:
                    item.setForeground(COL_NAME, QColor("#EEEEEE"))
            iterator += 1

        self.tree.blockSignals(False)
        self.sync_all_sel_state()
        QTimer.singleShot(0, self.adjust_cols)
        QTimer.singleShot(10, lambda: self.tree.verticalScrollBar().setValue(scroll_pos))

    def _add_folder_checkbox(self, item, row_h, rel_path):
        item.setSizeHint(0, QSize(0, row_h))
        cb = QCheckBox()
        related_items = [(r, p) for r, p in self.all_mods_in_repo if r == rel_path or r.startswith(rel_path + os.sep)]
        if related_items and all(x in self.selected_mods for x in related_items):
            cb.setChecked(True)
        cb.stateChanged.connect(lambda st, it=item: self.on_folder_cb(it, st))
        self.tree.setItemWidget(item, COL_CHECK, self.wrap_center(cb, height=row_h))

    def _add_pak_item(self, parent, pak, rel_path, game_files, row_h):
        item = QTreeWidgetItem(parent)
        item.setText(COL_NAME, pak)
        item.setData(COL_NAME, Qt.ItemDataRole.UserRole, pak)
        item.setData(COL_CAT, ROLE_REL_PATH, rel_path)
        item.setData(COL_CAT, ROLE_ITEM_TYPE, "file")
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        
        counts = self.get_pak_counts()
        if counts.get(pak, 0) > 1:
            item.setForeground(COL_NAME, QColor("#FF4444"))
        elif pak not in self.known_mods:
            item.setForeground(COL_NAME, QColor("#00A3FF"))
        else:
            item.setForeground(COL_NAME, QColor("#EEEEEE"))

        m_cb = QCheckBox()
        if (rel_path, pak) in self.selected_mods:
            m_cb.setChecked(True)
        m_cb.stateChanged.connect(lambda st, r=rel_path, p=pak, it=item: self.on_mod_cb(r, p, st, it))
        self.tree.setItemWidget(item, COL_CHECK, self.wrap_center(m_cb, row_h))
        
        thumb_s = int(60 * self.zoom_level)
        uncat_key = self.i18n.t("cat_uncategorized")
        phys_rel = "" if rel_path == uncat_key else rel_path
        
        lbl = DropLabel(pak, phys_rel, self)
        lbl.setFixedSize(thumb_s, thumb_s)
        self.tree.setItemWidget(item, COL_PREVIEW, self.wrap_center(lbl, row_h))
        
        is_en = pak in game_files
        btn_txt = self.i18n.t("mod_enabled") if is_en else self.i18n.t("mod_disabled")
        btn = QPushButton(btn_txt)
        btn.setMinimumWidth(int(100 * self.zoom_level))
        btn.setStyleSheet("background-color: #0078D4;" if is_en else "background-color: #3A3A3A; color: #AAA;")
        src_path = os.path.join(self.repo_path, phys_rel, pak)
        btn.clicked.connect(lambda chk, s=src_path, p=pak, en=is_en, b=btn: self.toggle_mod(s, p, en, b))
        self.tree.setItemWidget(item, COL_ACTION, self.wrap_center(btn, row_h))
        
        self.task_counter += 1
        tid = str(self.task_counter)
        self.item_map[tid] = lbl
        img_path = os.path.join(self.repo_path, phys_rel, pak.replace(".pak", ".png"))
        self.thread_pool.start(ImageLoadWorker(img_path, pak.replace(".pak", ""), tid, self.image_load_signals.image_loaded))

    def toggle_all_selection(self):
        if not self.repo_path:
            return
        self.is_batch_op = True
        try:
            self.is_all_selected = not self.is_all_selected
            self.selected_mods.clear()
            if self.is_all_selected:
                for rel, pak in self.all_mods_in_repo:
                    self.selected_mods.add((rel, pak))
            
            self.tree.blockSignals(True)
            iterator = QTreeWidgetItemIterator(self.tree)
            while iterator.value():
                item = iterator.value()
                w = self.tree.itemWidget(item, COL_CHECK)
                if w:
                    cb = w.findChild(QCheckBox)
                    if cb:
                        cb.setChecked(self.is_all_selected)
                iterator += 1
            self.tree.blockSignals(False)
            self.update_all_sel_btn_style()
            self.sync_all_sel_state()
        finally:
            self.is_batch_op = False

    def update_all_sel_btn_style(self):
        self.all_sel_btn.setText(self.i18n.t("btn_deselect_all" if self.is_all_selected else "btn_select_all"))
        self.all_sel_btn.setStyleSheet("background-color: #0078D4; color: white;" if self.is_all_selected else "")

    def on_folder_cb(self, it, st):
        if self.is_batch_op:
            return
        self.is_batch_op = True
        is_checked = (st == Qt.CheckState.Checked.value)

        stack = [it]
        while stack:
            curr = stack.pop()
            curr.setSelected(is_checked)

            w = self.tree.itemWidget(curr, COL_CHECK)
            if w:
                cb = w.findChild(QCheckBox)
                if cb:
                    cb.blockSignals(True)
                    cb.setChecked(is_checked)
                    cb.blockSignals(False)

            if curr.data(COL_CAT, ROLE_ITEM_TYPE) == "file":
                rel = curr.data(COL_CAT, ROLE_REL_PATH)
                pak = curr.text(COL_NAME)
                if is_checked:
                    self.selected_mods.add((rel, pak))
                else:
                    self.selected_mods.discard((rel, pak))

            for i in range(curr.childCount()):
                stack.append(curr.child(i))

        self.update_ancestor_checkboxes(it)
        self.is_batch_op = False
        self.sync_all_sel_state()

    def on_mod_cb(self, r, p, st, item):
        if self.is_batch_op: return
        is_checked = (st == Qt.CheckState.Checked.value)

        item.setSelected(is_checked)

        if is_checked:
            self.selected_mods.add((r, p))
        else:
            self.selected_mods.discard((r, p))
        self.update_ancestor_checkboxes(item)
        self.sync_all_sel_state()

    def sync_all_sel_state(self):
        total = len(self.all_mods_in_repo)
        selected_count = len(self.selected_mods)
        self.is_all_selected = (total > 0 and selected_count >= total)
        self.update_all_sel_btn_style()
        self.selection_label.setText(self.i18n.t("selected_count", selected_count) if selected_count > 0 else "")

    def on_item_clicked(self, item, col):
        item_type = item.data(COL_CAT, ROLE_ITEM_TYPE)
        if item_type == "folder" and col == COL_CAT:
             if item.childCount() > 0:
                 item.setExpanded(not item.isExpanded())
        QTimer.singleShot(10, self.adjust_cols)

    def on_item_data_changed(self, item, column):
        new_val = item.text(column).strip()
        if not new_val:
            self.refresh_data()
            return

        item_type = item.data(COL_CAT, ROLE_ITEM_TYPE)
        uncat_key = self.i18n.t("cat_uncategorized")

        try:
            if item_type == "folder" and column == COL_CAT:
                old_display = item.data(COL_CAT, Qt.ItemDataRole.UserRole)
                if not old_display:
                    old_display = item.text(COL_CAT)
                
                old_name = old_display.replace("棣冩惃 ", "").strip()
                new_name = new_val.replace("棣冩惃 ", "").strip()
                
                if old_name == new_name:
                    self.refresh_data()
                    return
                if old_name == uncat_key:
                    self.refresh_data()
                    return
                
                full_rel_path = item.data(COL_CAT, ROLE_REL_PATH)
                new_rel_path = self.mod_core.rename_folder(full_rel_path, new_name)
                
                if full_rel_path in self.folder_states:
                    self.folder_states[new_rel_path] = self.folder_states.pop(full_rel_path)
                
                self.refresh_data()

            elif item_type == "file" and column == COL_NAME:
                old_val = item.data(COL_NAME, Qt.ItemDataRole.UserRole)
                if old_val == new_val:
                    return
                if not new_val.lower().endswith(".pak"):
                    new_val += ".pak"
                
                rel = item.data(COL_CAT, ROLE_REL_PATH)
                
                if self.game_path:
                    old_game_pak = os.path.join(self.game_path, old_val)
                    if os.path.exists(old_game_pak):
                        os.remove(old_game_pak)
                
                self.mod_core.rename_mod(rel, old_val, new_val, uncat_key)
                
                self.known_mods.discard(old_val)
                self.known_mods.add(new_val)
                self.save_cfg()

                self.refresh_data()
                
        except (PermissionError, OSError) as e:
            QMessageBox.warning(self, self.i18n.t("msg_rename_fail"), self.i18n.t("msg_file_op_detail", str(e)))
            self.refresh_data()
        except Exception as e:
            QMessageBox.warning(self, self.i18n.t("msg_rename_fail"), self.i18n.t("msg_unknown_error_detail", str(e)))
            self.refresh_data()

    def batch_move_mods(self):
        if not self.selected_mods:
            return
        
        uncat_key = self.i18n.t("cat_uncategorized")
        other_targets = set()
        
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            it = iterator.value()
            if it.data(COL_CAT, ROLE_ITEM_TYPE) == "folder":
                rp = it.data(COL_CAT, ROLE_REL_PATH)
                if rp and rp != uncat_key:
                    other_targets.add(rp)
            iterator += 1

        # Keep "Uncategorized" pinned to top, and sort the rest logically.
        targets = [uncat_key] + self.mod_core.logical_sort(list(other_targets))
        
        move_dialog = QInputDialog(self)
        move_title = self.i18n.t("dialog_move_title")
        move_dialog.setLabelText(self.i18n.t("dialog_move_label"))
        move_dialog.setComboBoxItems(targets)
        move_dialog.setComboBoxEditable(False)
        self._apply_dialog_chrome(move_dialog, move_title)

        if move_dialog.exec() == QDialog.DialogCode.Accepted and move_dialog.textValue():
            dest_rel = move_dialog.textValue()
            phys_dest = "" if dest_rel == uncat_key else dest_rel
            dest_dir = os.path.join(self.repo_path, phys_dest)
            os.makedirs(dest_dir, exist_ok=True)
            
            failed_moves = []
            for src_rel, pak in list(self.selected_mods):
                if src_rel != dest_rel:
                    try:
                        self.mod_core.move_mod(src_rel, pak, dest_rel, uncat_key)
                        self.known_mods.add(pak)
                    except Exception as e:
                        failed_moves.append(f"{pak}: {str(e)}")
            
            if failed_moves:
                print(self.i18n.t("log_move_failed", len(failed_moves), ", ".join(failed_moves[:5])))
            self.selected_mods.clear()
            self.save_cfg()
            self.refresh_data()

    def batch_delete_logic(self):
        items = self.tree.selectedItems()
        files_to_delete = list(self.selected_mods)
        folders_to_delete = []
        
        uncat_key = self.i18n.t("cat_uncategorized")
        for item in items:
            if item.data(COL_CAT, ROLE_ITEM_TYPE) == "folder":
                rp = item.data(COL_CAT, ROLE_REL_PATH)
                if rp != uncat_key:
                    folders_to_delete.append(rp)

        total = len(files_to_delete) + len(folders_to_delete)
        if total == 0:
            return

        msg = self.i18n.t("confirm_delete", total)
        confirm_box = QMessageBox(self)
        confirm_box.setIcon(QMessageBox.Icon.Question)
        confirm_title = self.i18n.t("confirm_delete_title")
        confirm_box.setText(msg)
        confirm_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        self._apply_dialog_chrome(confirm_box, confirm_title)

        if confirm_box.exec() != QMessageBox.StandardButton.Yes:
            return

        # 1) Delete flow guard: disable enabled mods in game path first.
        # This prevents leftover files when deleting directly from repo.
        failed_disable_ops = []
        try:
            enabled_files = self.mod_core.get_game_files()
        except Exception:
            enabled_files = set()

        folder_paks_to_disable = set()
        for folder_rel in folders_to_delete:
            for rel, pak in self.all_mods_in_repo:
                if rel == folder_rel or rel.startswith(folder_rel + os.sep):
                    folder_paks_to_disable.add(pak)

        for pak in folder_paks_to_disable:
            if pak in enabled_files and self.game_path:
                try:
                    os.remove(os.path.join(self.game_path, pak))
                    enabled_files.discard(pak)
                except (PermissionError, OSError) as e:
                    failed_disable_ops.append(f"{pak}: {str(e)}")

        for rel, pak in files_to_delete:
            skip = False
            for f in folders_to_delete:
                if rel == f or rel.startswith(f + os.sep):
                    skip = True
                    break
            if skip:
                continue

            if pak in enabled_files and self.game_path:
                try:
                    os.remove(os.path.join(self.game_path, pak))
                    enabled_files.discard(pak)
                except (PermissionError, OSError) as e:
                    failed_disable_ops.append(f"{pak}: {str(e)}")

        if failed_disable_ops:
            print(self.i18n.t("log_batch_failed", len(failed_disable_ops), ", ".join(failed_disable_ops[:5])))

        # 2) After disable stage, continue original delete stage.
        failed_folder_deletes = []
        for f in folders_to_delete:
            try:
                self.mod_core.delete_folder(f)
                if f in self.folder_states:
                    self.folder_states.pop(f)
            except Exception as e:
                failed_folder_deletes.append(f"{f}: {str(e)}")
        
        if failed_folder_deletes:
            print(self.i18n.t("log_folder_delete_failed", len(failed_folder_deletes), ", ".join(failed_folder_deletes[:5])))
            
        for rel, pak in files_to_delete:
            skip = False
            for f in folders_to_delete:
                if rel == f or rel.startswith(f + os.sep):
                    skip = True
                    break
            if skip:
                continue

            try:
                self.mod_core.delete_mod(rel, pak, uncat_key)
                self.known_mods.discard(pak)
            except Exception as e:
                print(self.i18n.t("log_file_delete_failed", pak, str(e)))
            
        self.selected_mods.clear()
        self.save_cfg()
        self.refresh_data()

    def create_folder(self):
        if not self.repo_path:
            return
        
        base_name = self.i18n.t("new_folder_default")
        target_dir = self.repo_path
        
        current_item = self.tree.currentItem()
        if current_item:
            item_type = current_item.data(COL_CAT, ROLE_ITEM_TYPE)
            rel_path = current_item.data(COL_CAT, ROLE_REL_PATH)
            depth = current_item.data(COL_CAT, ROLE_DEPTH)
            uncat_key = self.i18n.t("cat_uncategorized")

            if depth is None:
                depth = 0

            if item_type == "folder":
                if depth == 0:
                    target_dir = self.repo_path
                elif depth == 1:
                    target_dir = os.path.join(self.repo_path, rel_path)
                elif depth >= 2:
                    QMessageBox.warning(self, self.i18n.t("msg_op_fail"), self.i18n.t("err_depth_limit"))
                    return
            elif item_type == "file":
                phys_rel = "" if rel_path == uncat_key else rel_path
                parts = rel_path.replace("\\", "/").split("/")
                if len(parts) >= 2 and rel_path != uncat_key:
                     QMessageBox.warning(self, self.i18n.t("msg_op_fail"), self.i18n.t("err_depth_limit"))
                     return
                target_dir = os.path.join(self.repo_path, phys_rel)

        try:
            self.mod_core.create_folder(target_dir, base_name)
            self.refresh_data()
        except (PermissionError, OSError) as e:
            QMessageBox.warning(self, self.i18n.t("msg_op_fail"), self.i18n.t("msg_create_folder_fail_detail", str(e)))

    def exec_batch(self, en):
        if not self.selected_mods:
            return
        uncat_key = self.i18n.t("cat_uncategorized")
        
        failed_ops = []
        for rel, pak in list(self.selected_mods):
            phys_rel = "" if rel == uncat_key else rel
            src = os.path.join(self.repo_path, phys_rel, pak)
            
            if os.path.exists(src):
                target = os.path.join(self.game_path, pak)
                try:
                    if en:
                        shutil.copy2(src, target)
                    elif os.path.exists(target):
                        os.remove(target)
                    self.known_mods.add(pak)
                except (PermissionError, OSError) as e:
                    failed_ops.append(f"{pak}: {str(e)}")
        
        if failed_ops:
            print(self.i18n.t("log_batch_failed", len(failed_ops), ", ".join(failed_ops[:5])))
        
        self.save_cfg()
        self.refresh_data()

    def show_large_preview(self, pak, pos):
        rn = pak.replace(".pak", "")
        if rn in self.qimage_cache:
            pix = QPixmap.fromImage(self.qimage_cache[rn]).scaled(MAX_PREVIEW_SIZE, MAX_PREVIEW_SIZE, Qt.AspectRatioMode.KeepAspectRatio)
            self.preview_win_lbl.setPixmap(pix)
            self.preview_win_lbl.adjustSize()
            self.preview_win.adjustSize()
            self.preview_win.move(pos.x()+20, pos.y()-20)
            self.preview_win.show()

    def on_img_loaded(self, n, thumb, full, tid):
        if tid in self.item_map and not thumb.isNull():
            ts = int(60 * self.zoom_level)
            pix = QPixmap.fromImage(thumb).scaled(ts, ts, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.item_map[tid].setPixmap(pix)
            self.item_map[tid].setText("")
            if len(self.qimage_cache) > 1000:
                first_key = next(iter(self.qimage_cache))
                del self.qimage_cache[first_key]
            self.qimage_cache[n] = full

    def handle_img_drop(self, pak, rel, src):
        try:
            dest_img_path = os.path.join(self.repo_path, rel, pak.replace(".pak", ".png"))
            self.mod_core.save_preview_image(src, dest_img_path)
            self.known_mods.add(pak)
            self.save_cfg()
            QTimer.singleShot(100, self.refresh_data)
        except (PermissionError, OSError) as e:
            print(self.i18n.t("log_preview_failed", str(e)))
        except Exception as e:
            print(self.i18n.t("log_preview_exception", str(e)))
    def filter_list(self):
        t = self.search_bar.text().lower()
        if not t:
            iterator = QTreeWidgetItemIterator(self.tree)
            while iterator.value():
                iterator.value().setHidden(False)
                iterator += 1
            return

        iterator = QTreeWidgetItemIterator(self.tree)
        items_to_show_ids = set()
        parent_ids_to_expand = set()

        while iterator.value():
            item = iterator.value()
            item_type = item.data(COL_CAT, ROLE_ITEM_TYPE)

            if item_type == "folder":
                match = t in item.text(COL_CAT).lower()
            else:
                match = t in item.text(COL_NAME).lower()

            if match:
                items_to_show_ids.add(id(item))
                p = item.parent()
                while p:
                    items_to_show_ids.add(id(p))
                    parent_ids_to_expand.add(id(p))
                    p = p.parent()

            iterator += 1

        self.tree.blockSignals(True)
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            if id(item) in parent_ids_to_expand:
                item.setExpanded(True)
            item.setHidden(id(item) not in items_to_show_ids)
            iterator += 1
        self.tree.blockSignals(False)
    def toggle_mod(self, src, pak, is_en, btn_widget):
        if not btn_widget.isEnabled():
            return
        btn_widget.setEnabled(False)
        try:
            new_en = self.mod_core.toggle_mod(src, pak, is_en)
            
            self.known_mods.add(pak)
            self.save_cfg()

            btn_widget.setText(self.i18n.t("mod_enabled" if new_en else "mod_disabled"))
            btn_widget.setStyleSheet("background-color: #0078D4;" if new_en else "background-color: #3A3A3A; color: #AAA;")
            try:
                btn_widget.clicked.disconnect()
            except TypeError:
                pass
            btn_widget.clicked.connect(lambda chk=False, s=src, p=pak, en=new_en, b=btn_widget: self.toggle_mod(s, p, en, b))
        except (PermissionError, OSError) as e:
            QMessageBox.warning(self, self.i18n.t("msg_op_fail"), self.i18n.t("msg_file_op_detail", str(e)))
        except Exception as e:
            QMessageBox.warning(self, self.i18n.t("msg_op_fail"), self.i18n.t("msg_unknown_error_detail", str(e)))
        finally:
            btn_widget.setEnabled(True)

    def select_repo(self):
        p = QFileDialog.getExistingDirectory(self, self.i18n.t("btn_set_repo"))
        if p:
            self.repo_path = p
            self.config.repo_path = p
            self.save_cfg()
            self.refresh_data()

    def select_game(self):
        p = QFileDialog.getExistingDirectory(self, self.i18n.t("btn_set_game"))
        if p:
            self.game_path = p
            self.config.game_path = p
            self.save_cfg()
            self.refresh_data()

    def save_cfg(self):
        self.config.repo_path = self.repo_path
        self.config.game_path = self.game_path
        self.config.folder_states = self.folder_states
        self.config.known_mods = self.known_mods
        self.config.window_size = [self.width(), self.height()]
        self.config.save()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(50, self.adjust_cols)
        
    def resizeEvent(self, e):
        super().resizeEvent(e)
        QTimer.singleShot(10, self.adjust_cols)
        
    def closeEvent(self, event):
        self.save_cfg()
        super().closeEvent(event)
  
    def adjust_cols(self):
        header = self.tree.header()
        sw = self.tree.verticalScrollBar().width() if self.tree.verticalScrollBar().isVisible() else 0
        tw = self.tree.width() - sw
        if tw > 100:
            header.setUpdatesEnabled(False)
            for i in range(4):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                calc_w = int(tw * COLUMN_PROPORTIONS[i])
                if i == COL_CHECK:
                    calc_w = max(int(40 * self.zoom_level), calc_w)
                self.tree.setColumnWidth(i, calc_w)
            header.setSectionResizeMode(COL_ACTION, QHeaderView.ResizeMode.ResizeToContents)
            if header.sectionSize(COL_ACTION) < int(tw * COLUMN_PROPORTIONS[COL_ACTION]):
                header.setSectionResizeMode(COL_ACTION, QHeaderView.ResizeMode.Stretch)
            header.setUpdatesEnabled(True)


