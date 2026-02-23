"""
mod_manager.py

包含：
- 模组仓库核心管理类 (ModManagerCore)
- 仓库与游戏目录扫描 (os.scandir / os.listdir)
- 模组启用 / 禁用切换 (shutil.copy2 / os.remove)
- 模组移动与重命名 (os.rename)
- 文件与文件夹删除 (os.remove / shutil.rmtree)
- 文件夹创建 (os.makedirs + 自动重名递增)
- 预览图处理 (PIL.Image 打开与保存 PNG)
- 游戏目录文件集合获取 (set + os.listdir)

说明：
- 所有操作基于文件系统路径拼接 (os.path.join)
- 通过相对路径与物理路径转换控制分类结构
- 自动同步 .pak 与对应 .png 预览图
- 返回状态或新路径供 UI 层更新
"""

import os
import shutil
from functools import cmp_to_key

if os.name == "nt":
    try:
        import ctypes
        _STR_CMP_LOGICAL_W = ctypes.windll.shlwapi.StrCmpLogicalW
        _STR_CMP_LOGICAL_W.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        _STR_CMP_LOGICAL_W.restype = ctypes.c_int
    except Exception:
        _STR_CMP_LOGICAL_W = None
else:
    _STR_CMP_LOGICAL_W = None


def _logical_sort(names):
    if _STR_CMP_LOGICAL_W is None:
        return sorted(names)
    return sorted(names, key=cmp_to_key(_STR_CMP_LOGICAL_W))


class ModManagerCore:

    def __init__(self, repo_path, game_path):
        self.repo_path = repo_path
        self.game_path = game_path

    def logical_sort(self, names):
        return _logical_sort(names)

    def scan_repository(self):
        root_paks = []
        root_dirs = []

        if os.path.exists(self.repo_path):
            with os.scandir(self.repo_path) as it:
                for entry in it:
                    if entry.is_file() and entry.name.lower().endswith(".pak"):
                        root_paks.append(entry.name)
                    elif entry.is_dir():
                        root_dirs.append(entry.name)

        root_paks = self.logical_sort(root_paks)
        root_dirs = self.logical_sort(root_dirs)
        return root_paks, root_dirs

    def scan_directory(self, dir_path):
        paks = []
        dirs = []
        try:
            entries = self.logical_sort(os.listdir(dir_path))
            for e in entries:
                ep = os.path.join(dir_path, e)
                if os.path.isfile(ep) and e.lower().endswith(".pak"):
                    paks.append(e)
                elif os.path.isdir(ep):
                    dirs.append(e)
        except OSError:
            pass
        return paks, dirs

    def toggle_mod(self, src, pak, is_en):
        target = os.path.join(self.game_path, pak)
        new_en = is_en
        try:
            if is_en:
                if os.path.exists(target):
                    os.remove(target)
                new_en = False
            else:
                shutil.copy2(src, target)
                new_en = True
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"操作失败: {e}")
        return new_en

    def move_mod(self, src_rel, pak, dest_rel, uncat_key):
        phys_src = "" if src_rel == uncat_key else src_rel
        phys_dest = "" if dest_rel == uncat_key else dest_rel

        old_p = os.path.join(self.repo_path, phys_src, pak)
        new_p = os.path.join(self.repo_path, phys_dest, pak)
        try:
            if os.path.exists(old_p.replace(".pak", ".png")):
                os.rename(
                    old_p.replace(".pak", ".png"),
                    new_p.replace(".pak", ".png")
                )

            os.rename(old_p, new_p)
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"移动失败: {e}")

    def delete_mod(self, rel, pak, uncat_key):
        phys_rel = "" if rel == uncat_key else rel
        target_path = os.path.join(self.repo_path, phys_rel, pak)
        try:
            if os.path.exists(target_path):
                os.remove(target_path)

            png_path = target_path.replace(".pak", ".png")
            if os.path.exists(png_path):
                os.remove(png_path)
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"删除失败: {e}")

    def delete_folder(self, folder_rel):
        folder_path = os.path.join(self.repo_path, folder_rel)
        try:
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"删除文件夹失败: {e}")

    def rename_folder(self, old_rel_path, new_name):
        parent_path = os.path.dirname(old_rel_path)

        src = os.path.join(self.repo_path, old_rel_path)
        dst = os.path.join(self.repo_path, parent_path, new_name)
        try:
            os.rename(src, dst)
            return os.path.join(parent_path, new_name)
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"重命名文件夹失败: {e}")

    def rename_mod(self, old_rel, old_pak, new_pak, uncat_key):
        phys_rel = "" if old_rel == uncat_key else old_rel

        src = os.path.join(self.repo_path, phys_rel, old_pak)
        dst = os.path.join(self.repo_path, phys_rel, new_pak)
        try:
            os.rename(src, dst)

            img_old = src.replace(".pak", ".png")
            img_new = dst.replace(".pak", ".png")

            if os.path.exists(img_old):
                os.rename(img_old, img_new)
        except (PermissionError, OSError) as e:
            raise RuntimeError(f"重命名模组失败: {e}")

    def create_folder(self, target_dir, base_name):
        target_path = os.path.join(target_dir, base_name)
        counter = 1

        while os.path.exists(target_path):
            counter += 1
            target_path = os.path.join(target_dir, f"{base_name} ({counter})")

        os.makedirs(target_path, exist_ok=True)
        return target_path

    def save_preview_image(self, src_img_path, dest_img_path):
        from PIL import Image
        with Image.open(src_img_path) as img:
            img.convert("RGB").save(dest_img_path, "PNG")

    def get_game_files(self):
        if os.path.exists(self.game_path):
            return set(os.listdir(self.game_path))
        return set()
