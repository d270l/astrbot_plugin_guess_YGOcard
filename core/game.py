"""猜卡游戏状态机。

对应原插件 ``guess_card.py`` 的 ``guessCard`` / ``guessSolve`` / ``guessReset``
三个 matcher，以及 ``libraries/Guess.py`` 里的 ``GuessData``。

与原插件的差别：
* 原插件用 ``asyncio.sleep`` 阻塞在开局 handler 里，这里改为独立的后台任务，
  同一个群里的多个玩家可以各自开局、互不阻塞；
* 原插件把原图以 ``base64`` 字节串存进状态，f-string 拼出来会带 ``b''``
  前缀导致答案图发送失败，这里改为保存文件路径，答案图能正常显示。
"""

from __future__ import annotations

import asyncio
import random
import sqlite3
import time
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from PIL import Image

from . import texts
from .carddb import Card, CardDB, is_guess_win
from .render import crop_card, get_guess_img, save_png
from .replies import ReplyTemplates
from .store import GuessStore


@dataclass
class GuessConfig:
    """从插件配置里解析出来的运行参数。"""

    guess_times: int = 3
    answer_timeout: int = 30
    blur_scale: int = 7
    cut_size: int = 6
    at_sender: bool = True
    use_web_pic: bool = True
    pic_url_template: str = "https://cdn.233.momobako.com/ygopro/pics/{id}.jpg"
    download_timeout: float = 15.0
    mess_type: int = texts.MESS_TYPE_NORMAL
    llm_context: bool = True
    llm_context_max: int = 8


@dataclass
class Reply:
    """一条待发送的消息（由 main.py 转成 AstrBot 消息链）。"""

    text: str = ""
    image: Optional[Path] = None
    at: bool = False


@dataclass
class Game:
    uid: str
    card: Card
    question: Path
    answer: Path
    time: int
    umo: str
    group_session: Optional[str]
    session_id: str
    user_id: str
    user_name: str = ""
    deadline: float = 0.0
    end: bool = False
    task: Optional[asyncio.Task] = field(default=None, repr=False)


def uid_of(group_id: str, user_id: str) -> str:
    if group_id:
        return f"group_{group_id}user_{user_id}"
    return f"private_user_{user_id}"


def session_of(group_id: str, user_id: str) -> tuple[Optional[str], str]:
    if group_id:
        return f"group_{group_id}", f"user_{user_id}"
    return None, f"user_{user_id}"


class GuessGameManager:
    def __init__(
        self,
        db: CardDB,
        store: GuessStore,
        cfg: GuessConfig,
        pics_dir: Path,
        tmp_dir: Path,
        font_path: Optional[Path],
        send_cb: Callable[[str, Reply], "asyncio.Future | None"],
        replies: Optional[ReplyTemplates] = None,
    ) -> None:
        self.db = db
        self.store = store
        self.cfg = cfg
        self.replies = replies if replies is not None else ReplyTemplates(mess_type=cfg.mess_type)
        self.pics_dir = Path(pics_dir)
        self.tmp_dir = Path(tmp_dir)
        self.font_path = font_path
        self._send_cb = send_cb
        self.games: dict[str, Game] = {}
        self._pending: set[str] = set()
        self._tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------------ 查询
    def has_game(self, uid: str) -> bool:
        return uid in self.games

    def get(self, uid: str) -> Optional[Game]:
        return self.games.get(uid)

    # ------------------------------------------------------------------ 开局
    async def start(
        self, group_id: str, user_id: str, umo: str, user_name: str = ""
    ) -> Optional[Reply]:
        uid = uid_of(group_id, user_id)
        if uid in self.games or uid in self._pending:
            # 原插件在这里静默 finish()
            return None
        group_session, session_id = session_of(group_id, user_id)
        self._pending.add(uid)
        try:
            try:
                self.store.check_permission(session_id, group_session)
            except PermissionError as exc:
                return Reply(text=str(exc))

            card = await asyncio.to_thread(self._random_card)
            if card is None:
                return Reply(text=self.replies.image_missing())

            prepared = await self._prepare(card)
            if prepared is None:
                return Reply(text=self.replies.image_missing())
            question, answer = prepared

            self.store.update_last_send(session_id)
            game = Game(
                uid=uid,
                card=card,
                question=question,
                answer=answer,
                time=self.cfg.guess_times,
                umo=umo,
                group_session=group_session,
                session_id=session_id,
                user_id=user_id,
                user_name=user_name,
                deadline=time.time() + self.cfg.answer_timeout,
            )
            self.games[uid] = game
            game.task = asyncio.create_task(self._timeout_worker(uid, card.cardId))
            self._tasks.add(game.task)
            game.task.add_done_callback(self._tasks.discard)

            return Reply(
                text=self.replies.start(self.cfg.guess_times, self.cfg.answer_timeout),
                image=question,
                at=True,
            )
        finally:
            self._pending.discard(uid)

    def _random_card(self) -> Optional[Card]:
        try:
            js = self.db.get_random_card()
        except sqlite3.Error:
            return None
        if not js.cards:
            return None
        return js.cards[0]

    # ------------------------------------------------------------------ 作答
    async def answer(self, group_id: str, user_id: str, text: str) -> Optional[Reply]:
        uid = uid_of(group_id, user_id)
        game = self.games.get(uid)
        if game is None:
            return None
        name = str(text).strip()
        card = game.card

        if name in texts.SKIP_WORDS:
            self._end(uid)
            return Reply(
                text=self.replies.skip(card.name),
                image=game.answer,
                at=True,
            )

        js = await asyncio.to_thread(self.db.get_card, name)
        if js.cards is None or is_guess_win(js, card.name, name):
            if game.time == 1:
                self._end(uid)
                return Reply(
                    text=self.replies.lose(card.name),
                    image=game.answer,
                    at=True,
                )
            if game.time == 3:
                hint = self.replies.tip(self.replies.hint_type(card.mainType))
            elif game.time == 2:
                if card.mainType == "怪兽":
                    ran = random.randint(0, 2)
                    if ran == 0:
                        hint = self.replies.tip(self.replies.hint_zz(card.zz))
                    elif ran == 1:
                        hint = self.replies.tip(self.replies.hint_attribute(card.attribute))
                    else:
                        hint = self.replies.tip(self.replies.hint_fulltype(card.type))
                else:
                    hint = self.replies.tip(self.replies.hint_fulltype(card.type))
            else:
                hint = self.replies.tip(self.replies.hint_fulltype(card.type))
            # 原插件一半的台词里自带「这张卡是」，再拼上「是怪兽卡」会出现「是是」
            hint = hint.replace("是是", "是")
            game.time -= 1
            return Reply(
                text=hint + self.replies.left(game.time),
                at=True,
            )

        self._end(uid)
        return Reply(
            text=self.replies.win(card.name),
            image=game.answer,
            at=True,
        )

    # ------------------------------------------------------------------ 重置
    def reset(self, group_id: str, user_id: str) -> Optional[Reply]:
        uid = uid_of(group_id, user_id)
        if uid in self.games:
            self._end(uid)
            return Reply(text=self.replies.reset())
        # 原插件不在局中时静默
        return None

    # ------------------------------------------------------------ LLM 上下文
    def describe_games(
        self, umo: str, group_id: str, user_id: str, limit: int = 8
    ) -> str:
        """把本会话的猜卡进度整理成一段可注入 system prompt 的说明。

        只描述进度，不包含答案卡名——避免大模型顺口把答案说出来。
        """
        now = time.time()
        active = [g for g in self.games.values() if not g.end and g.umo == umo]
        speaker_uid = uid_of(group_id, user_id)
        lines: list[str] = []
        if active:
            lines.append(
                f"[猜一张卡] 本会话有 {len(active)} 位玩家正在猜卡，"
                "你只知道这些进度，回答时不要编造或透露答案卡名："
            )
            shown = active[:limit]
            for game in shown:
                label = self._player_label(game)
                if game.uid == speaker_uid:
                    label += "（当前发言人）"
                lines.append(f"- {label}：{self._progress(game, now)}")
            if len(active) > len(shown):
                lines.append(f"- 另有 {len(active) - len(shown)} 位玩家在猜卡")
            speaker = next((g for g in active if g.uid == speaker_uid), None)
            if speaker is not None and speaker not in shown:
                lines.append(f"- 当前发言人也在猜卡，{self._progress(speaker, now)}")

        cooldown = self._cooldown_left(group_id, user_id, now)
        if cooldown > 0:
            lines.append(f"- 当前发言人的猜卡冷却还剩 {int(cooldown)} 秒，现在开局会被拒绝")
        if not lines:
            return ""
        lines.append("被问起猜卡时可按上述进度回答；用户正在猜卡时不要主动剧透。")
        return "\n".join(lines)

    @staticmethod
    def _player_label(game: Game) -> str:
        name = (game.user_name or "").strip()
        return f"{name}({game.user_id})" if name else f"用户{game.user_id}"

    @staticmethod
    def _progress(game: Game, now: float) -> str:
        left = max(0, int(round(game.deadline - now)))
        return f"还剩 {game.time} 次机会，约 {left} 秒后公布答案"

    def _cooldown_left(self, group_id: str, user_id: str, now: float) -> float:
        group_session, session_id = session_of(group_id, user_id)
        target = group_session if group_session is not None else session_id
        try:
            return self.store.read_cd(target) + self.store.read_last_send(session_id) - now
        except Exception:
            return 0.0

    # ------------------------------------------------------------------ 超时
    async def _timeout_worker(self, uid: str, card_id: int) -> None:
        try:
            await asyncio.sleep(max(1, int(self.cfg.answer_timeout)))
            game = self.games.get(uid)
            if game is None or game.end or game.card.cardId != card_id:
                return
            # 不能走 _end()：那会 cancel 掉当前正在运行的这个超时任务
            self.games.pop(uid, None)
            game.end = True
            reply = Reply(
                text=self.replies.timeout(game.card.name),
                image=game.answer,
                at=False,
            )
            result = self._send_cb(game.umo, reply)
            if asyncio.iscoroutine(result):
                await result
        except asyncio.CancelledError:
            raise
        except Exception:
            # 后台任务不应影响主流程
            pass

    def _end(self, uid: str) -> None:
        game = self.games.pop(uid, None)
        if game is None:
            return
        game.end = True
        if game.task is not None and not game.task.done():
            game.task.cancel()

    # ------------------------------------------------------------------ 卡图
    def _pic_path(self, card_id: int) -> Path:
        return self.pics_dir / f"{card_id}.jpg"

    def _download(self, path: Path) -> bool:
        url = self.cfg.pic_url_template.format(id=path.stem)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=self.cfg.download_timeout) as resp:
                data = resp.read()
            if not data:
                return False
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return True
        except Exception:
            return False

    async def _ensure_picture(self, card: Card) -> Optional[Path]:
        path = self._pic_path(card.cardId)
        try:
            if path.is_file() and path.stat().st_size > 0:
                return path
        except OSError:
            return None
        if not self.cfg.use_web_pic:
            return None
        ok = await asyncio.to_thread(self._download, path)
        return path if ok else None

    async def _prepare(self, card: Card) -> Optional[tuple[Path, Path]]:
        picture = await self._ensure_picture(card)
        if picture is None:
            return None

        def _cleanup_old() -> None:
            """顺手清掉一小时前的题图，避免缓存目录无限增长。"""
            deadline = time.time() - 3600
            for old in self.tmp_dir.glob("[qa]_*.png"):
                try:
                    if old.stat().st_mtime < deadline:
                        old.unlink()
                except OSError:
                    pass

        def _work() -> tuple[Path, Path]:
            with Image.open(picture) as im:
                original = im.convert("RGB").copy()
            cropped = crop_card(original, card.type)
            quiz = get_guess_img(
                cropped,
                resize=self.cfg.blur_scale,
                cut_size=self.cfg.cut_size,
                restrict=3,
                font_path=self.font_path,
            )
            tag = uuid.uuid4().hex[:12]
            question = save_png(quiz, self.tmp_dir / f"q_{card.cardId}_{tag}.png")
            answer = save_png(original, self.tmp_dir / f"a_{card.cardId}_{tag}.png")
            _cleanup_old()
            return question, answer

        try:
            return await asyncio.to_thread(_work)
        except (OSError, ValueError):
            return None

    # ------------------------------------------------------------------ 生命周期
    async def close(self) -> None:
        for uid in list(self.games.keys()):
            self._end(uid)
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
