"""猜卡冷却 / 功能开关的持久化，移植自 ``libraries/guessManage.py``。

配置文件结构（与原插件一致）::

    {
        "last": {"group_123": 1699999999.0, "user_456": 1699999999.0},
        "group_123": {"cd": 60},
        "ban": ["group_123"]
    }
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from . import texts


class GuessStore:
    """管理每个群 / 用户的猜卡冷却与开关。"""

    def __init__(self, path: Path, default_cd: int = 20, mess_type: int = texts.MESS_TYPE_NORMAL) -> None:
        self.path = Path(path)
        self.guess_cd = default_cd if default_cd > 0 else 0
        self.mess_type = mess_type
        self.cfg: dict = {}
        self.read_cfg()

    # ------------------------------------------------------------------ 文件读写
    def read_cfg(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.cfg = json.loads(f.read())
            if not isinstance(self.cfg, dict):
                raise ValueError("配置文件格式错误")
            return self.cfg
        except Exception:
            self.cfg = {}
            self.write_cfg()
            return {}

    def write_cfg(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(json.dumps(self.cfg))
        except OSError:
            pass

    # ------------------------------------------------------------------ 查询
    def read_last_send(self, session_id: str) -> float:
        try:
            return self.cfg["last"][session_id]
        except KeyError:
            return 0

    def read_cd(self, session_id: Optional[str]) -> int:
        try:
            return self.cfg[session_id]["cd"]
        except (KeyError, TypeError):
            return self.guess_cd

    def read_ban_list(self, session_id: Optional[str]) -> bool:
        try:
            return session_id in self.cfg["ban"]
        except KeyError:
            return False

    # ------------------------------------------------------------------ 冷却判定
    def check_permission(self, session_id: str, group_session: Optional[str]) -> None:
        """不满足条件时抛 ``PermissionError``（消息即原插件的提示文案）。"""
        if self.read_ban_list(group_session):
            raise PermissionError(texts.FUNCTION_OFF_TEXT)

        target = group_session if group_session is not None else session_id
        time_left = self.read_cd(target) + self.read_last_send(session_id) - time.time()
        if time_left > 0:
            hours, minutes, seconds = 0, 0, 0.0
            if time_left >= 60:
                minutes, seconds = divmod(time_left, 60)
                hours, minutes = divmod(minutes, 60)
            else:
                seconds = time_left
            cd_msg = (
                (str(round(hours)) + "小时" if hours else "")
                + (str(round(minutes)) + "分钟" if minutes else "")
                + (str(round(seconds, 3)) + "秒" if seconds else "")
            )
            raise PermissionError(f"{texts.guess_sendwitchoutcd(self.mess_type)} 你的CD还有{cd_msg}！")

    # ------------------------------------------------------------------ 更新
    def update_last_send(self, session_id: str) -> None:
        self.cfg.setdefault("last", {})[session_id] = time.time()

    def update_cd(self, session_id: str, cd_time: int) -> str:
        cd_time = cd_time if cd_time > 0 else 0
        try:
            cd_time_old = self.cfg[session_id]["cd"]
        except (KeyError, TypeError):
            cd_time_old = "未设定"
        if session_id not in self.cfg.keys():
            self.cfg[session_id] = {}
            self.write_cfg()
        self.cfg[session_id]["cd"] = cd_time
        self.write_cfg()
        return f"cd更新成功 {cd_time_old} -> {cd_time}"

    def update_ban_list(self, session_id: str, add_mode: bool) -> str:
        if add_mode:
            try:
                if session_id in self.cfg["ban"]:
                    return "功能已经关闭"
            except KeyError:
                self.cfg["ban"] = []
            self.cfg["ban"].append(session_id)
            self.write_cfg()
            return "功能已经关闭"
        try:
            self.cfg["ban"].remove(session_id)
            self.write_cfg()
            return "功能已经开启"
        except (ValueError, KeyError):
            return "功能已经开启"
