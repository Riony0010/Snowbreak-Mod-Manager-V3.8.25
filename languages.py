"""
language.py

Contains:
- Multilingual manager (I18nManager)
- Built-in Chinese and English translation dictionaries
- Runtime language switching and key lookup with fallback
"""


class I18nManager:
    def __init__(self, default_lang="zh_CN"):
        self.current_lang = default_lang
        self.translations = {}

        self.default_en = {
            "window_title": "Snowbreak Mod Manager",
            "path_game_paks": "Game Paks Path",
            "path_mod_repo": "Mod Library Path",
            "not_set": "Not Set",
            "btn_open": "📂 Open",
            "btn_set_game": "Select Game",
            "btn_set_repo": "Select Library",
            "search_placeholder": "🔍 Search mods... (Ctrl +/- Zoom, Ctrl 0 Reset)",
            "btn_select_all": "Select All",
            "btn_deselect_all": "Deselect All",
            "btn_batch_enable": "Enable Selected",
            "btn_batch_disable": "Disable Selected",
            "btn_batch_move": "Move Selected",
            "btn_delete": "Delete",
            "btn_new_folder": "New Folder",
            "btn_refresh": "Refresh",
            "btn_lang_toggle": "中文",
            "conflict_warn": "⚠ {} Name Conflicts",
            "selected_count": "{} Mods Selected",
            "header_folder": "Category",
            "header_preview": "Preview",
            "header_name": "Mod Name",
            "header_action": "Status",
            "cat_uncategorized": "Uncategorized",
            "mod_enabled": "Enabled",
            "mod_disabled": "Disabled",
            "tip_select_path": "Please set paths first!",
            "confirm_delete": "Are you sure you want to delete the selected {0} items?",
            "confirm_delete_title": "Confirm Delete",
            "msg_rename_fail": "Rename Failed",
            "msg_op_fail": "Operation Failed",
            "dialog_move_title": "Move Mods",
            "dialog_move_label": "Destination Folder:",
            "new_folder_default": "New Folder",
            "err_depth_limit": "Cannot create folder here (Max depth reached)",
            "msg_file_op_detail": "File operation failed: {}",
            "msg_unknown_error_detail": "Unknown error: {}",
            "msg_create_folder_fail_detail": "Failed to create folder: {}",
            "log_style_format_failed": "Stylesheet formatting failed, missing placeholder: {}",
            "log_move_failed": "Move failed: {} item(s) affected: {}",
            "log_folder_delete_failed": "Folder delete failed: {} item(s) affected: {}",
            "log_file_delete_failed": "File delete failed: {}: {}",
            "log_batch_failed": "Batch operation failed: {} item(s) affected: {}",
            "log_preview_failed": "Preview processing failed: {}",
            "log_preview_exception": "Preview processing exception: {}",
        }

        self.default_zh = {
            "window_title": "尘白禁区模组管理器",
            "path_game_paks": "游戏 Pak 路径",
            "path_mod_repo": "模组库路径",
            "not_set": "未设置",
            "btn_open": "📂 打开",
            "btn_set_game": "选择游戏路径",
            "btn_set_repo": "选择库路径",
            "search_placeholder": "🔍 搜索模组... (Ctrl +/- 缩放, Ctrl 0 重置)",
            "btn_select_all": "全选",
            "btn_deselect_all": "取消全选",
            "btn_batch_enable": "启用选中",
            "btn_batch_disable": "禁用选中",
            "btn_batch_move": "移动选中",
            "btn_delete": "删除",
            "btn_new_folder": "新建文件夹",
            "btn_refresh": "刷新",
            "btn_lang_toggle": "EN",
            "conflict_warn": "⚠ {} 处名称冲突",
            "selected_count": "已选择 {} 个模组文件",
            "header_folder": "分类",
            "header_preview": "预览",
            "header_name": "模组名称",
            "header_action": "状态",
            "cat_uncategorized": "未分类",
            "mod_enabled": "已启用",
            "mod_disabled": "已禁用",
            "tip_select_path": "请先设置路径！",
            "confirm_delete": "确定要删除选中的 {0} 个项目吗？",
            "confirm_delete_title": "确认删除",
            "msg_rename_fail": "重命名失败",
            "msg_op_fail": "操作失败",
            "dialog_move_title": "移动模组",
            "dialog_move_label": "目标文件夹:",
            "new_folder_default": "新建文件夹",
            "err_depth_limit": "无法在此创建文件夹（已达最大层级）",
            "msg_file_op_detail": "文件操作失败: {}",
            "msg_unknown_error_detail": "未知错误: {}",
            "msg_create_folder_fail_detail": "创建文件夹失败: {}",
            "log_style_format_failed": "样式表格式化失败，缺少占位符: {}",
            "log_move_failed": "移动失败: {} 个项目受影响: {}",
            "log_folder_delete_failed": "文件夹删除失败: {} 个项目受影响: {}",
            "log_file_delete_failed": "文件删除失败: {}: {}",
            "log_batch_failed": "批量操作失败: {} 个项目受影响: {}",
            "log_preview_failed": "预览图处理失败: {}",
            "log_preview_exception": "预览图处理异常: {}",
        }

        self.load_language(default_lang)

    def load_language(self, lang_code):
        self.current_lang = lang_code
        self.translations = self.default_zh if lang_code == "zh_CN" else self.default_en

    def t(self, key, *args):
        fallback = self.default_zh if self.current_lang == "zh_CN" else self.default_en
        text = self.translations.get(key, fallback.get(key, key))
        return text.format(*args) if args else text
