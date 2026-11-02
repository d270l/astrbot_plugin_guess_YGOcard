"""AstrBot 猜一张卡插件。

移植自 nonebot-plugin-ocgbot-v2 的「猜一张卡」小游戏：
随机抽一张游戏王卡片，裁掉卡框后随机做模糊 / 切割 / 字符画处理发给玩家，
玩家在群里直接输入卡名作答，共三次机会，30 秒后自动公布答案。

指令：
    游戏王猜卡 / 猜一张卡   开始一局（群里也可以直接发，不必 @机器人）
    猜卡重置               重置自己当前的猜卡状态
    猜卡cd <秒>            设置本群猜卡冷却（群主 / 群管理员 / Bot 管理员）
    猜卡功能 on|off        开关本群猜卡功能（同上）
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.star import Context, Star, StarTools

from .core import texts
from .core.carddb import CardDB
from .core.game import GuessConfig, GuessGameManager, Reply, uid_of
from .core.render import resolve_font
from .core.replies import KEYS as REPLY_KEYS
from .core.replies import ReplyTemplates
from .core.store import GuessStore

PLUGIN_NAME = "astrbot_plugin_guess_YGOcard"

# 这些词开头的消息交给指令处理，不当成猜卡作答
COMMAND_WORDS = ("游戏王猜卡", "猜一张卡", "猜卡重置", "猜卡cd", "猜卡功能")

# 自定义过滤器需要访问插件实例，模块加载时还拿不到实例，先留一个全局引用
_PLUGIN: Optional["GuessCardPlugin"] = None


class GuessTriggerFilter(filter.CustomFilter):
    """把「无唤醒词的指令」和「进行中的猜卡作答」交给本插件处理。

    普通群消息（没 @ 机器人、没有唤醒词）默认不会唤醒 AstrBot，
    这里显式声明：只有指令词开头、或者当前用户正处在猜卡局中时才接管，
    其余消息继续交给别的插件 / 大模型。
    """

    def filter(self, event: AstrMessageEvent, cfg: AstrBotConfig) -> bool:  # noqa: ARG002
        plugin = _PLUGIN
        if plugin is None or plugin.manager is None:
            return False
        text = (event.get_message_str() or "").strip()
        if not text:
            return False
        if text.startswith(COMMAND_WORDS):
            # 带 @ / 唤醒词时由 CommandFilter 处理，避免重复触发
            return not event.is_at_or_wake_command
        uid = uid_of(event.get_group_id() or "", str(event.get_sender_id()))
        return plugin.manager.has_game(uid)


class GuessCardPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.config = config
        # 指令可能在 initialize 之前就被触发，先用默认值兜底
        self.cfg = GuessConfig()
        self.replies = ReplyTemplates()
        self.db: Optional[CardDB] = None
        self.store: Optional[GuessStore] = None
        self.manager: Optional[GuessGameManager] = None
        self.font_path = None
        self._data_dir: Optional[Path] = None
        self._cache_dir: Optional[Path] = None

    # ------------------------------------------------------------------ 生命周期
    async def initialize(self) -> None:
        global _PLUGIN

        plugin_dir = Path(__file__).resolve().parent
        data_dir = Path(StarTools.get_data_dir(PLUGIN_NAME))
        data_dir.mkdir(parents=True, exist_ok=True)
        cache_dir = data_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._data_dir = data_dir
        self._cache_dir = cache_dir
        # 清掉上一次运行留下的题图缓存
        for old in cache_dir.glob("*.png"):
            try:
                old.unlink()
            except OSError:
                pass

        mess_type = texts.MESS_TYPE_CHOICES.get(
            str(self.config.get("mess_type", "正常")),
            texts.MESS_TYPE_NORMAL,
        )
        self.replies = ReplyTemplates(
            {key: self.config.get(key, "") for key in REPLY_KEYS},
            mess_type=mess_type,
        )
        cdb_path = self._resolve_cdb(plugin_dir)
        nickname_path = plugin_dir / "data" / "nickname.json"
        try:
            self.db = CardDB(
                cdb_path,
                nickname_path if nickname_path.is_file() else None,
                web_search=bool(self.config.get("use_web_search", False)),
            )
        except FileNotFoundError as exc:
            logger.error(f"[guess-card] {exc}，猜卡功能不可用")
            self.db = None
            return

        self.store = GuessStore(
            data_dir / "guess_cfg.json",
            default_cd=self._int("default_cd", 20),
            mess_type=mess_type,
            replies=self.replies,
        )
        self.font_path = resolve_font(str(self.config.get("font_path", "") or ""), plugin_dir)
        self.cfg = GuessConfig(
            guess_times=max(1, self._int("guess_times", 3)),
            answer_timeout=max(1, self._int("answer_timeout", 30)),
            blur_scale=max(2, self._int("blur_scale", 7)),
            cut_size=max(2, self._int("cut_size", 6)),
            at_sender=bool(self.config.get("at_sender", True)),
            use_web_pic=bool(self.config.get("use_web_pic", True)),
            pic_url_template=str(
                self.config.get("pic_url_template")
                or "https://cdn.233.momobako.com/ygopro/pics/{id}.jpg",
            ),
            mess_type=mess_type,
        )
        pics_dir = self._resolve_pics_dir(plugin_dir, data_dir)
        self.manager = GuessGameManager(
            db=self.db,
            store=self.store,
            cfg=self.cfg,
            pics_dir=pics_dir,
            tmp_dir=cache_dir,
            font_path=self.font_path,
            send_cb=self._send_by_session,
            replies=self.replies,
        )
        _PLUGIN = self
        logger.info(
            f"[guess-card] 已就绪：卡库 {cdb_path.name}，卡图目录 {pics_dir}，"
            f"字体 {self.font_path.name if self.font_path else '默认'}",
        )

    async def terminate(self) -> None:
        global _PLUGIN
        _PLUGIN = None
        if self.manager is not None:
            await self.manager.close()
            self.manager = None
        if self.db is not None:
            self.db.close()
            self.db = None
        if self._cache_dir is not None:
            for old in self._cache_dir.glob("*.png"):
                try:
                    old.unlink()
                except OSError:
                    pass

    # ------------------------------------------------------------------ 指令
    @filter.command("游戏王猜卡", alias={"猜一张卡"})
    async def cmd_guess_start(self, event: AstrMessageEvent):
        """游戏王猜卡 / 猜一张卡：开始一局猜卡"""
        event.stop_event()
        reply = await self._do_start(event)
        if reply is not None:
            yield self._result(event, reply, event.get_sender_id())

    @filter.command("猜卡重置")
    async def cmd_guess_reset(self, event: AstrMessageEvent):
        """猜卡重置：重置自己当前的猜卡状态"""
        event.stop_event()
        reply = self._do_reset(event)
        if reply is not None:
            yield self._result(event, reply)

    @filter.command("猜卡cd")
    async def cmd_guess_cd(self, event: AstrMessageEvent, cd: str = ""):
        """猜卡cd <秒>：设置本群猜卡冷却时间"""
        event.stop_event()
        reply = self._do_cd(event, cd)
        yield self._result(event, reply)

    @filter.command("猜卡功能")
    async def cmd_guess_switch(self, event: AstrMessageEvent, mode: str = ""):
        """猜卡功能 on|off：开关本群猜卡功能"""
        event.stop_event()
        reply = self._do_switch(event, mode)
        yield self._result(event, reply)

    @filter.custom_filter(GuessTriggerFilter)
    async def on_free_text(self, event: AstrMessageEvent):
        """处理没有 @机器人 的指令，以及局内玩家的猜卡作答。"""
        if self.manager is None:
            return
        text = (event.get_message_str() or "").strip()
        if not text:
            return
        event.stop_event()

        reply: Optional[Reply]
        if text.startswith(("游戏王猜卡", "猜一张卡")):
            reply = await self._do_start(event)
        elif text.startswith("猜卡重置"):
            reply = self._do_reset(event)
        elif text.startswith("猜卡cd"):
            reply = self._do_cd(event, text[len("猜卡cd") :].strip())
        elif text.startswith("猜卡功能"):
            reply = self._do_switch(event, text[len("猜卡功能") :].strip())
        else:
            group_id, user_id = self._group_user(event)
            reply = await self.manager.answer(group_id, user_id, text)

        if reply is not None:
            yield self._result(event, reply, event.get_sender_id())

    # ------------------------------------------------------------------ 各指令实现
    async def _do_start(self, event: AstrMessageEvent) -> Optional[Reply]:
        if self.manager is None:
            return Reply(text=self.replies.not_ready())
        group_id, user_id = self._group_user(event)
        return await self.manager.start(group_id, user_id, event.unified_msg_origin)

    def _do_reset(self, event: AstrMessageEvent) -> Optional[Reply]:
        if self.manager is None:
            return None
        group_id, user_id = self._group_user(event)
        return self.manager.reset(group_id, user_id)

    def _do_cd(self, event: AstrMessageEvent, arg: str) -> Reply:
        if not self._is_privileged(event):
            return Reply(text=self.replies.no_permission())
        message = str(arg).replace(" ", "")
        try:
            cd_time = int(message)
        except (TypeError, ValueError):
            return Reply(text=self.replies.invalid_cd(message))
        sid = self._session_of_group(event)
        if not _verify_sid(sid):
            return Reply(text=f"无效目标对象: {sid}")
        assert self.store is not None
        return Reply(text=self.store.update_cd(sid, cd_time))

    def _do_switch(self, event: AstrMessageEvent, arg: str) -> Reply:
        if not self._is_privileged(event):
            return Reply(text=self.replies.no_permission())
        message = str(arg)
        if "off" in message:
            add_mode = True
        elif "on" in message:
            add_mode = False
        else:
            return Reply(text=self.replies.invalid_switch(message))
        sid = self._session_of_group(event)
        if not _verify_sid(sid):
            return Reply(text=f"无效目标对象: {sid}")
        assert self.store is not None
        return Reply(text=self.store.update_ban_list(sid, add_mode))

    # ------------------------------------------------------------------ 工具
    @staticmethod
    def _group_user(event: AstrMessageEvent) -> tuple[str, str]:
        return event.get_group_id() or "", str(event.get_sender_id())

    @staticmethod
    def _session_of_group(event: AstrMessageEvent) -> str:
        group_id = event.get_group_id() or ""
        if group_id:
            return f"group_{group_id}"
        return f"user_{event.get_sender_id()}"

    def _is_privileged(self, event: AstrMessageEvent) -> bool:
        """群主 / 群管理员 / AstrBot 全局管理员。"""
        if event.is_admin():
            return True
        raw = getattr(event.message_obj, "raw_message", None)
        if raw is None:
            return False
        sender = raw.get("sender") if isinstance(raw, dict) else getattr(raw, "sender", None)
        if sender is None:
            return False
        role = sender.get("role") if isinstance(sender, dict) else getattr(sender, "role", None)
        return role in ("owner", "admin")

    def _result(
        self,
        event: AstrMessageEvent,
        reply: Reply,
        at_uid: Optional[str] = None,
    ):
        if reply.at and self.cfg.at_sender and at_uid:
            return event.chain_result(
                self._components(reply, at_uid),
            )
        return event.chain_result(self._components(reply, None))

    @staticmethod
    def _components(reply: Reply, at_uid: Optional[str]) -> list:
        components: list = []
        if reply.at and at_uid:
            components.append(Comp.At(qq=at_uid))
        if reply.text:
            components.append(Comp.Plain(reply.text))
        if reply.image is not None:
            components.append(Comp.Image.fromFileSystem(str(reply.image)))
        return components

    def _send_by_session(self, umo: str, reply: Reply):
        """超时公布答案时用：脱离事件主动发送。"""
        chain = MessageChain(chain=self._components(reply, None))
        return self.context.send_message(umo, chain)

    def _int(self, key: str, default: int) -> int:
        try:
            return int(self.config.get(key, default))
        except (TypeError, ValueError):
            return default

    def _resolve_cdb(self, plugin_dir: Path) -> Path:
        configured = str(self.config.get("cdb_path", "") or "").strip()
        if configured:
            path = Path(configured)
            if path.is_dir():
                path = path / "cards.cdb"
            if path.is_file():
                return path
            logger.warning(f"[guess-card] 配置的卡库不存在: {path}，回退到内置卡库")
        for candidate in (
            plugin_dir / "data" / "cards.cdb",
            plugin_dir / "data" / "cdb" / "cards.cdb",
        ):
            if candidate.is_file():
                return candidate
        raise FileNotFoundError(
            "未找到 cards.cdb，请把卡库放到插件 data 目录或在配置里填写 cdb_path",
        )

    def _resolve_pics_dir(self, plugin_dir: Path, data_dir: Path) -> Path:
        configured = str(self.config.get("pics_dir", "") or "").strip()
        path = Path(configured) if configured else plugin_dir / "data" / "pics"
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError:
            path = data_dir / "pics"
            path.mkdir(parents=True, exist_ok=True)
        return path


def _verify_sid(sid: str) -> bool:
    try:
        s_type, s_id = sid.split("_")
        return s_type in ("group", "user") and s_id.isdigit()
    except ValueError:
        return False
