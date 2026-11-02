"""卡库查询，移植自 nonebot-plugin-ocgbot-v2 的 ``libraries/Card.py``。

尽可能逐字保留原实现的派生逻辑（包括 ``getType`` 的逐 nibble 解析、
「把宽高写反」等历史行为），以保证猜卡提示文案里的种族/属性/类型与原插件一致。
"""

from __future__ import annotations

import copy
import json
import math
import random
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

PAGESIZE = 5

BG_URL = "https://ygocdb.com/api/v0/?search="

HAS_TYPE = [
    ["怪兽", "魔法", "陷阱", "N/A"],
    ["通常", "效果", "融合", "仪式"],
    ["N/A", "灵魂", "同盟", "二重"],
    ["调整", "同调", "衍生物", "N/A"],
    ["速攻", "永续", "装备", "场地"],
    ["反击", "反转", "卡通", "超量"],
    ["灵摆", "特殊召唤", "连接", "N/A"],
]

HAS_ZZ = [
    ["战士族", "魔法师族", "天使族", "恶魔族"],
    ["不死族", "机械族", "水族", "炎族"],
    ["岩石族", "鸟兽族", "植物族", "昆虫族"],
    ["雷族", "龙族", "兽族", "兽战士族"],
    ["恐龙族", "鱼族", "海龙族", "爬虫类族"],
    ["念动力族", "幻神兽族", "创造神族", "幻龙族"],
    ["电子界族", "幻想魔族", "N/A", "N/A"],
]

HAS_ATTRIBUTE = [
    ["地", "水", "炎", "风"],
    ["光", "暗", "神", ""],
]

_DERIVED_ATTRS = frozenset(
    {"cardId", "name", "effect", "zz", "mainType", "type", "level", "attribute", "atk", "deff"}
)


def get_type(datas: str) -> list[str]:
    """把 ``type`` 字段的十六进制字符串解析成类型列表。"""
    datas = datas.replace("0x", "")
    types: list[str] = []
    n = len(datas)
    for i in range(1, 8):
        if n >= i:
            c = datas[n - i]
            if c in ["a", "b", "c", "d", "e", "f"]:
                c = bin(ord(c) - 87)
            else:
                c = bin(int(c))
            line = c.replace("0b", "")
            for j in range(len(line)):
                if line[j] == "1":
                    types.append(HAS_TYPE[i - 1][len(line) - j - 1])
        else:
            break
    return types


def get_zz(datas: str) -> str:
    """把 ``race`` 字段解析成种族名。"""
    datas = datas.replace("0x", "")
    return HAS_ZZ[len(datas) - 1][len(bin(int(datas[0]))) - 3]


def get_attribute(datas: str) -> str:
    """把 ``attribute`` 字段解析成属性名。"""
    datas = datas.replace("0x", "")
    return HAS_ATTRIBUTE[len(datas) - 1][len(bin(int(datas[0]))) - 3]


class Card(dict):
    """一条卡数据，属性按需从原始字段派生。"""

    def __getattribute__(self, item: str) -> Any:
        if item in _DERIVED_ATTRS:
            raw = dict.__getitem__
            types = get_type(str(hex(raw(self, "type"))))
            if item == "cardId":
                return raw(self, "id")
            if item == "type":
                return " ".join(types)
            if item == "mainType":
                return types[0]
            if item == "zz":
                return get_zz(str(hex(raw(self, "race"))))
            if item == "atk":
                if types[0] == "怪兽":
                    return str(raw(self, "atk")) if str(raw(self, "atk")) != "-2" else "?"
                return None
            if item == "deff":
                if types[0] == "怪兽" and "连接" not in types:
                    return str(raw(self, "def")) if str(raw(self, "def")) != "-2" else "?"
                return None
            if item == "attribute":
                return get_attribute(str(hex(raw(self, "attribute"))))
            if item == "level":
                level = raw(self, "level") & 0xFFFF
                if "连接" in types:
                    return "Link " + str(level)
                if "超量" in types:
                    return str(level) + " 阶"
                return str(level) + " 星"
            if item == "effect":
                return raw(self, "desc").replace("\r", "")
            return raw(self, item)
        return super().__getattribute__(item)


class CardResult:
    """查询结果（对应原插件的 ``CardResult``）。"""

    def __init__(
        self,
        cards: Optional[list[Card]] = None,
        page_num: int = 0,
        amount: int = 0,
        now_num: int = 0,
    ) -> None:
        self.cards = cards
        self.pageNum = page_num
        self.amount = amount
        self.nowNum = now_num

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return (
            f"<CardResult amount={self.amount} page={self.nowNum}/{self.pageNum} "
            f"cards={None if self.cards is None else len(self.cards)}>"
        )


def is_guess_win(js: CardResult, card_name: str, name: str) -> bool:
    """猜卡判定：``False`` 表示猜对，``True`` 表示猜错。"""
    if name in card_name and len(name) >= len(card_name) / 3:
        return False
    if js.cards is None:
        return True
    if js.amount <= PAGESIZE:
        for card in js.cards:
            if card.name == card_name:
                return False
    else:
        if js.cards[0].name == card_name:
            return False
    return True


class CardDB:
    """cards.cdb 的查询封装。"""

    def __init__(
        self,
        cdb_path: Path,
        nickname_path: Optional[Path] = None,
        web_search: bool = False,
        web_timeout: float = 8.0,
    ) -> None:
        self.cdb_path = Path(cdb_path)
        if not self.cdb_path.is_file():
            raise FileNotFoundError(f"未找到卡片数据库: {self.cdb_path}")
        self.conn = sqlite3.connect(str(self.cdb_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.web_search = web_search
        self.web_timeout = web_timeout
        self.nick_name_0: dict[str, list[str]] = {}
        self.nick_name_1: list[dict] = []
        if nickname_path is not None:
            self._load_nickname(Path(nickname_path))

    # ------------------------------------------------------------------ 生命周期
    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:  # pragma: no cover - 关闭失败无需处理
            pass

    def _load_nickname(self, path: Path) -> None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                nick_json = json.loads(f.read())
            if isinstance(nick_json, dict):
                nick_json = nick_json["RECORDS"]
            for js in nick_json:
                if js["nk_type"] == 0:
                    if js["nick_name"] not in self.nick_name_0:
                        self.nick_name_0[js["nick_name"]] = [js["name"]]
                    else:
                        self.nick_name_0[js["nick_name"]].append(js["name"])
                if js["nk_type"] == 1:
                    self.nick_name_1.append(js)
        except Exception:
            # 别名表缺失不影响主流程
            self.nick_name_0 = {}
            self.nick_name_1 = []

    # ------------------------------------------------------------------ 查询
    def get_random_card(self) -> CardResult:
        sql = (
            "SELECT * FROM texts LEFT JOIN datas on texts.id=datas.id "
            "where name= (SELECT name FROM texts ORDER BY RANDOM() limit 1) "
            "GROUP BY texts.name;"
        )
        row = self._fetchone(sql)
        if row is None:  # pragma: no cover - 空数据库
            return CardResult(cards=[], pageNum=0, amount=0, nowNum=1)
        return self._card_result([Card(row)], 1)

    def get_card(self, name: str, page: str = "1") -> CardResult:
        if page is None or str(page).replace(" ", "") == "":
            page = "1"
        pageint = int(page)
        name = str(name)
        if name.isdigit():
            cards = self._search_by_id(int(name))
            if len(cards) == 0:
                cards = self._search_by_name(name)
        else:
            cards = self._search_by_name(name)
        return self._card_result(cards, pageint)

    def search_by_id(self, card_id: int) -> CardResult:
        return self._card_result(self._search_by_id(int(card_id)), 1)

    def _card_result(self, cards: list[Card], page: int) -> CardResult:
        result = CardResult()
        result.amount = len(cards)
        result.pageNum = int(math.ceil(len(cards) / PAGESIZE))
        if cards is not None:
            result.nowNum = page
        if page > result.pageNum:
            result.cards = None
        elif page == result.pageNum:
            result.cards = cards[PAGESIZE * (page - 1) : len(cards)]
        else:
            result.cards = cards[PAGESIZE * (page - 1) : PAGESIZE * page]
        return result

    def _search_by_id(self, cid: int) -> list[Card]:
        return self._select("texts.id=" + str(cid))

    def _search_by_name(self, name: str) -> list[Card]:
        org_name = copy.deepcopy(name)
        name = name.replace(" ", "")
        names = self._nick_name_match(name)
        cards: list[Card] = []
        for item in names:
            sql = "texts.name like '%{0}%'".format(item)
            cards_temp = self._select(sql)
            if len(cards_temp) == 0 and self.web_search:
                bg_id = self._search_from_bg(org_name)
                if bg_id is not None:
                    cards_temp = self._search_by_id(bg_id)
            cards_temp.sort(key=lambda a: len(a.name))
            cards.extend(cards_temp)
        return cards

    def _select(self, where: str) -> list[Card]:
        sql = (
            "select * from texts LEFT JOIN datas on texts.id = datas.id "
            "where {0} GROUP BY texts.name;".format(where)
        )
        return [Card(row) for row in self._fetchall(sql)]

    def _fetchall(self, sql: str) -> list[sqlite3.Row]:
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def _fetchone(self, sql: str) -> Optional[sqlite3.Row]:
        self.cursor.execute(sql)
        return self.cursor.fetchone()

    def _search_from_bg(self, name: str) -> Optional[int]:
        """原插件的联网兜底（ygocdb），默认关闭。"""
        try:
            url = BG_URL + urllib.parse.quote(name)
            with urllib.request.urlopen(url, timeout=self.web_timeout) as resp:
                js = json.loads(resp.read().decode("utf-8"))
            if len(js["result"]) == 0:
                return None
            return js["result"][0]["id"]
        except Exception:
            return None

    def _nick_name_match(self, name: str) -> list[str]:
        name = name.upper()
        to_name = None
        if name in self.nick_name_0:
            return self.nick_name_0[name]
        for nick in self.nick_name_1:
            if nick["nick_name"] in name:
                name = name.replace(nick["nick_name"], "▶")
                to_name = nick["name"]
        nameforsearch = "%".join(list(name))
        if to_name is not None:
            nameforsearch = nameforsearch.replace("▶", to_name)
        return [nameforsearch]


def random_card(db: CardDB) -> Optional[Card]:
    """随机取一张卡；数据库异常时返回 ``None``。"""
    try:
        js = db.get_random_card()
    except Exception:
        return None
    if not js.cards:
        return None
    card = js.cards[0]
    if random.random() < 0:  # pragma: no cover - 保留占位，避免优化器警告
        return None
    return card
