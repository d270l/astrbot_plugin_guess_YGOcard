"""可自定义的机器人回复文案。

默认文案来自 :mod:`core.texts`（逐字移植自原插件），插件配置里每一项
``text_*`` 都可以覆盖对应的默认文案：

* 留空 → 使用内置文案（保留原作的多条随机台词与「称呼」随机）；
* 填写 → 使用你写的模板，模板里可以用 ``{named}`` 等占位符；
* 用 ``|`` 分隔可以写多条，每次随机抽一条，例如 ``答对啦！|厉害，是{name}``。

占位符说明见 :data:`PLACEHOLDERS`，未使用的占位符会原样忽略。
"""

from __future__ import annotations

import random
from typing import Any, Optional

from . import texts

# 所有可自定义的配置项，顺序与 _conf_schema.json 一致
KEYS = (
    "text_start",
    "text_timeout",
    "text_win",
    "text_lose",
    "text_skip",
    "text_tip",
    "text_hint_type",
    "text_hint_zz",
    "text_hint_attribute",
    "text_hint_fulltype",
    "text_left",
    "text_cd",
    "text_reset",
    "text_off",
    "text_no_permission",
    "text_image_missing",
    "text_not_ready",
    "text_invalid_cd",
    "text_invalid_switch",
    "text_cd_updated",
    "text_switch_off",
    "text_switch_on",
)

# 每个占位符的含义，写文档 / 提示时用
PLACEHOLDERS = {
    "named": "随机称呼，例如「哥哥大人」",
    "name": "答案卡名",
    "times": "每局机会次数（数字）",
    "times_text": "机会次数的中文写法，三次时为「三」，其它为数字",
    "timeout": "公布答案的倒计时秒数",
    "hint": "递进提示片段，例如「是怪兽卡」",
    "left": "剩余机会次数",
    "type": "卡片完整类型，例如「怪兽 效果」",
    "zz": "怪兽种族，例如「龙族」",
    "attribute": "怪兽属性，例如「光」",
    "cd": "剩余冷却时间，例如「12秒」",
    "old": "修改前的冷却秒数",
    "new": "修改后的冷却秒数",
    "arg": "用户输入的参数原文",
}

DEFAULT_NOT_READY = "猜卡功能还没有准备好，请稍后再试~"


class _SafeDict(dict):
    """模板里出现了不认识的占位符时替换成空字符串，而不是抛错。"""

    def __missing__(self, key: str) -> str:  # noqa: D105
        return ""


def _times_text(times: int) -> str:
    """与原插件一致：三次时写「三」，其它次数写数字。"""
    return "三" if int(times) == 3 else str(int(times))


class ReplyTemplates:
    """把配置里的自定义文案与内置文案合并成最终回复。"""

    def __init__(
        self,
        overrides: Optional[dict[str, Any]] = None,
        mess_type: int = texts.MESS_TYPE_NORMAL,
    ) -> None:
        self.mess_type = mess_type
        clean: dict[str, str] = {}
        for key, value in (overrides or {}).items():
            if key not in KEYS or not isinstance(value, str):
                continue
            if value.strip():
                clean[key] = value
        self._overrides = clean

    # ------------------------------------------------------------------ 内部
    def custom(self, key: str) -> bool:
        """这一项是否被用户自定义过。"""
        return key in self._overrides

    def _render(self, key: str, **kwargs: Any) -> Optional[str]:
        raw = self._overrides.get(key)
        if raw is None:
            return None
        kwargs.setdefault("named", texts.get_named(self.mess_type))
        return random.choice(raw.split("|")).format_map(_SafeDict(kwargs))

    def _default_or(self, key: str, default: str, **kwargs: Any) -> str:
        text = self._render(key, **kwargs)
        return default if text is None else text

    # ------------------------------------------------------------------ 对局
    def start(self, times: int, timeout: int) -> str:
        """开局文案（不带 @，调用方负责 @ 玩家）。"""
        default = (
            texts.get_named(self.mess_type)
            + "，你有"
            + _times_text(times)
            + "次机会哟~"
            + str(timeout)
            + texts.TIMEOUT_TEXT_TAIL
        )
        return self._default_or(
            "text_start",
            default,
            times=int(times),
            times_text=_times_text(times),
            timeout=int(timeout),
        )

    def timeout(self, name: str) -> str:
        """超时公布答案。"""
        return self._default_or(
            "text_timeout",
            texts.guess_timeout(self.mess_type).format(name),
            name=name,
        )

    def win(self, name: str) -> str:
        """猜对了。"""
        return self._default_or(
            "text_win",
            texts.guess_win(self.mess_type).format(name),
            name=name,
        )

    def lose(self, name: str) -> str:
        """机会用尽。"""
        return self._default_or(
            "text_lose",
            texts.guess_lose(self.mess_type).format(name),
            name=name,
        )

    def skip(self, name: str) -> str:
        """玩家跳过。"""
        return self._default_or(
            "text_skip",
            texts.guess_skip(self.mess_type).format(name),
            name=name,
        )

    def tip(self, hint: str) -> str:
        """猜错后的提示语，``hint`` 由下面四个 ``hint_*`` 方法生成。"""
        return self._default_or(
            "text_tip",
            texts.guess_tips(self.mess_type).format(hint),
            hint=hint,
        )

    def hint_type(self, card_type: str) -> str:
        """第一次猜错：卡片大类。"""
        return self._default_or("text_hint_type", "是" + card_type + "卡", type=card_type)

    def hint_zz(self, zz: str) -> str:
        """第二次猜错：怪兽种族。"""
        return self._default_or("text_hint_zz", "种族是" + zz, zz=zz)

    def hint_attribute(self, attribute: str) -> str:
        """第二次猜错：怪兽属性。"""
        return self._default_or(
            "text_hint_attribute",
            "属性是" + attribute,
            attribute=attribute,
        )

    def hint_fulltype(self, card_type: str) -> str:
        """第二次猜错：完整类型。"""
        return self._default_or(
            "text_hint_fulltype",
            "完整类型是" + card_type,
            type=card_type,
        )

    def left(self, left: int) -> str:
        """提示语后面的剩余次数。"""
        return self._default_or("text_left", "\r\n还有{0}次机会！".format(left), left=int(left))

    # ------------------------------------------------------------------ 指令
    def cd(self, cd_msg: str) -> str:
        """冷却未到时的提示，``cd_msg`` 已经拼好。"""
        default = f"{texts.guess_sendwitchoutcd(self.mess_type)} 你的CD还有{cd_msg}！"
        return self._default_or("text_cd", default, cd=cd_msg)

    def reset(self) -> str:
        """猜卡状态已重置。"""
        return self._default_or("text_reset", texts.RESET_TEXT)

    def off(self) -> str:
        """本群猜卡功能已关闭。"""
        return self._default_or("text_off", texts.FUNCTION_OFF_TEXT)

    def no_permission(self) -> str:
        """权限不足。"""
        return self._default_or("text_no_permission", texts.NO_PERMISSION_TEXT)

    def image_missing(self) -> str:
        """找不到卡图。"""
        return self._default_or("text_image_missing", texts.IMAGE_MISSING_TEXT)

    def not_ready(self) -> str:
        """插件还没初始化完。"""
        return self._default_or("text_not_ready", DEFAULT_NOT_READY)

    def invalid_cd(self, arg: str) -> str:
        """``猜卡cd`` 参数不是整数。"""
        return self._default_or(
            "text_invalid_cd",
            f"无效参数: {arg}, 请输入 正整数 或 0 为参数",
            arg=arg,
        )

    def invalid_switch(self, arg: str) -> str:
        """``猜卡功能`` 参数不是 on / off。"""
        return self._default_or(
            "text_invalid_switch",
            f"无效参数: {arg}, 请输入 on 或 off 为参数",
            arg=arg,
        )

    def cd_updated(self, old: Any, new: int) -> str:
        """``猜卡cd`` 设置成功。"""
        return self._default_or("text_cd_updated", f"cd更新成功 {old} -> {new}", old=old, new=new)

    def switch_off(self) -> str:
        """``猜卡功能 off`` 的结果。"""
        return self._default_or("text_switch_off", "功能已经关闭")

    def switch_on(self) -> str:
        """``猜卡功能 on`` 的结果。"""
        return self._default_or("text_switch_on", "功能已经开启")
