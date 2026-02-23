"""
config.py

"""

import json
import os


class ConfigManager:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.repo_path = ""
        self.game_path = ""
        self.lang = "zh_CN"
        self.folder_states = {}
        self.known_mods = set()
        self.window_size = [1200, 850]

    def load(self):
        if not os.path.exists(self.config_file):
            return

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.repo_path = data.get("repo", "")
            self.game_path = data.get("game", "")
            self.lang = data.get("lang", "zh_CN")
            self.folder_states = data.get("folder_states", {})
            self.known_mods = set(data.get("known_mods", []))

            ws = data.get("window_size", [1200, 850])
            if (
                isinstance(ws, list)
                and len(ws) == 2
                and isinstance(ws[0], int)
                and isinstance(ws[1], int)
                and ws[0] > 100
                and ws[1] > 100
            ):
                self.window_size = ws

        except json.JSONDecodeError:
            print("配置文件损坏，已忽略。")
        except OSError as e:
            print(f"读取配置失败: {e}")

    def save(self):
        data = {
            "repo": self.repo_path,
            "game": self.game_path,
            "lang": self.lang,
            "folder_states": self.folder_states,
            "known_mods": list(self.known_mods),
            "window_size": self.window_size,
        }

        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except OSError as e:
            print(f"保存配置失败: {e}")
