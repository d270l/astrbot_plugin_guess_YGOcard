"""猜卡文案。

文案逐字移植自 nonebot-plugin-ocgbot-v2 (0.2.10.6) 的
``libraries/globalMessage.py``，包含「雌小鬼语录」与「正常语录」两套，
``##`` 为称呼占位符，``{0}`` 为内容占位符。
"""

from __future__ import annotations

import random

# 0：雌小鬼语录  1：正常语录（原插件 mess_type_choose = 1）
MESS_TYPE_TSUNDERE = 0
MESS_TYPE_NORMAL = 1

MESS_TYPE_CHOICES = {
    "雌小鬼": MESS_TYPE_TSUNDERE,
    "正常": MESS_TYPE_NORMAL,
}

MESSAGE_TYPE = [
    {
        "guess": {
            "sendwitchoutcd": [
                "打咩❤️！",
                "前面的区域之后再来探索吧~",
                "##！慢点啦！",
                "##,小蓝不让你猜卡了(叉腰)~",
                "##又在猜卡哦~休息一下好不好~",
                "##又在猜卡呀，天天只会猜卡，真是飞舞❤️～",
                "笨蛋##，着什么急❤️～笨蛋❤️笨蛋",
                "##，不给你猜了！生气吗？生气吗❤️？",
            ],
            "tips": [
                "呃啊~##❤~这都不会？我偷偷告诉你这张卡{0}。",
                "##❤~##❤~，这张卡{0}~",
                "##真好捉弄❤~。这张卡{0}~",
                "好❤恶❤心~，连这张卡{0}都不知道❤~",
                "杂❤~鱼❤~这张卡是{0}~",
                "哎~这么简单的题都不会，这张卡是{0}❤~",
                "行不行啊~##❤~连这张卡是{0}都不知道~",
                "这张卡小蓝三岁就会了，##连它是{0}都不知道❤~",
                "呐❤~呐❤~呐❤~##不会是笨蛋吧，这张卡是{0}呀~",
            ],
            "lose": [
                "这都猜不到，##就是弱哎❤，答案是{0}",
                "略略略❤~猜不到吧，答案是{0}",
                "##果然是杂❤鱼，连这个是{0}都猜不到？",
                "弱哎❤~这就不行了，答案是{0}哎~",
                "行不行啊❤~##，连{0}都猜不到~",
                "不是吧❤~这都猜不到❤~，答案是{0}",
                "##❤~##❤~答案是{0}~",
                "就这啊~##❤~答案是{0}哦~",
                "##❤~连{0}都答不上来~真是飞舞❤~",
                "不会吧❤不会吧❤不会有人连{0}都猜不到吧❤",
                "##！告诉你答案吧！是{0}！",
            ],
            "skip": [
                "略略略❤##这就不行了？答案是{0}",
                "就这❤~就这❤~答案是{0}",
                "##这就结束了❤？答案是{0}",
                "弱哎❤~##好弱❤~答案是{0}",
                "就这啊~##❤~答案是{0}哦~",
                "不会吧❤不会吧❤不会有人连{0}都猜不到吧❤",
                "##也太❤弱❤了❤吧，答案是{0}耶~",
                "##❤~连{0}都答不上来~真是飞舞❤~",
                "行不行啊❤~##，连{0}都猜不到~",
            ],
            "timeout": [
                "时间到啦！##连这都不会吗？答案是{0}",
            ],
            "win": [
                "哎，竟然答对了吗？真无聊❤~答案就是{0}啦",
                "##竟然答对了❤~答案是{0}",
                "好吧，好吧，算你对了啦❤~答案就是{0}",
                "恶心！变态！竟然答对了❤~答案是{0}",
                "答错...好吧,##竟然答对了{0}(生气)",
                "呐❤呐❤呐❤，##竟然答对了{0},##不会作弊了吧❤~",
            ],
        },
    },
    {
        "guess": {
            "sendwitchoutcd": [
                "打咩️！",
                "前面的区域之后再来探索吧~",
                "##！慢点啦！",
                "##,小蓝不让你猜卡了(叉腰)~",
                "##又在猜卡哦~休息一下好不好~",
                "##又在猜卡呀,不要猜卡了好不好~",
                "##，稍等一下，小蓝在准备卡组~",
                "##，不要猜卡啦，让小蓝休息一下吧QAQ",
                "洗衣服中（勿扰）",
            ],
            "tips": [
                "##答不出来吗，小蓝提醒你一下这张卡{0}。",
                "##！##！这张卡{0}啦！",
                "唔...这张卡{0}小蓝偷偷告诉##，不要告诉别人哦~",
                "嘟嘟嘟~这张卡{0}哦~",
                "（翻阅卡表）这张卡是{0}哦~（叉腰）",
                "呀！好像题目有点难，小蓝提醒一下##吧，这张卡是{0}~",
                "哎~##猜不到吗？这张卡是{0}",
                "这张卡{0}！快猜快猜，猜完小蓝要去洗衣服了",
            ],
            "lose": [
                "啊！##没猜出来吗！答案是{0}啦",
                "##！##！错了啦！答案是{0}啦",
                "（翻阅卡表）答案好像是{0}哎？##没猜出来，好可惜哦~",
                "嘟嘟嘟，答案新鲜出炉！是{0}哒~",
                "答案是{0}哦~，##再接再厉吧~",
            ],
            "skip": [
                "啊！##猜不到吗！答案是{0}啦",
                "##！##！！答案是{0}啦",
                "（翻阅卡表）答案好像是{0}哎？##没猜出来，好可惜哦~",
                "嘟嘟嘟，答案新鲜出炉！是{0}哒~",
                "答案是{0}哦~，##再接再厉吧~",
                "QWQ既然##不会，那么小蓝告诉你答案吧，是{0}哦~",
            ],
            "timeout": [
                "时间到啦！答案是{0}哦~",
            ],
            "win": [
                "##好厉害！答案就是{0}啦",
                "##答对了！（崇拜眼）答案是{0}",
                "哇！欧尼酱答对啦！好厉害鸭！答案就是{0}",
                "呼呼呼！##答对啦，答案是{0}，下次小蓝要出更难的题（比拳头）",
                "好耶,##答对了{0}！小蓝可以去洗衣服啦",
                "嘿嘿嘿，##好厉害，小蓝都不会呢，答案就是{0}哦",
            ],
        },
    },
]

# 称呼，## 的替换值
NAMED = [
    [
        "臭哥哥",
        "哥哥",
        "臭欧尼酱",
        "欧尼酱",
        "杂鱼",
        "臭杂鱼",
        "杂鱼哥哥",
        "大叔",
        "臭大叔",
    ],
    [
        "欧尼酱",
        "哥哥",
        "哥哥大人",
    ],
]

START_TEXT_TAIL = "，你有三次机会哟~"
TIMEOUT_TEXT_TAIL = "秒后公布答案！(输入跳过结束游戏)"
IMAGE_MISSING_TEXT = "对应图片不存在，无法进行猜卡~"
RESET_TEXT = "猜卡状态已重置"
FUNCTION_OFF_TEXT = "猜卡功能已关闭！"
NO_PERMISSION_TEXT = "只有群主、群管理员或 Bot 管理员才能使用该指令哦~"
SKIP_WORDS = ("不知道", "跳过")


def _norm(mess_type: int) -> int:
    return MESS_TYPE_TSUNDERE if mess_type == MESS_TYPE_TSUNDERE else MESS_TYPE_NORMAL


def get_named(mess_type: int = MESS_TYPE_NORMAL) -> str:
    """随机取一个称呼。"""
    return random.choice(NAMED[_norm(mess_type)])


def _pick(kind: str, mess_type: int, prefix: str = "") -> str:
    arr = MESSAGE_TYPE[_norm(mess_type)]["guess"][kind]
    return prefix + random.choice(arr).replace("##", get_named(mess_type))


def guess_sendwitchoutcd(mess_type: int = MESS_TYPE_NORMAL) -> str:
    """CD 中时的提示语，无前缀。"""
    return _pick("sendwitchoutcd", mess_type)


def guess_tips(mess_type: int = MESS_TYPE_NORMAL) -> str:
    """猜错后的提示语，带 ``\\r\\n`` 前缀。"""
    return _pick("tips", mess_type, "\r\n")


def guess_lose(mess_type: int = MESS_TYPE_NORMAL) -> str:
    """次数用尽的文案，带 ``\\r\\n`` 前缀。"""
    return _pick("lose", mess_type, "\r\n")


def guess_skip(mess_type: int = MESS_TYPE_NORMAL) -> str:
    """跳过时的文案，带 ``\\r\\n`` 前缀。"""
    return _pick("skip", mess_type, "\r\n")


def guess_timeout(mess_type: int = MESS_TYPE_NORMAL) -> str:
    """超时公布答案的文案，无前缀。"""
    return _pick("timeout", mess_type)


def guess_win(mess_type: int = MESS_TYPE_NORMAL) -> str:
    """猜对的文案，带 ``\\r\\n`` 前缀。"""
    return _pick("win", mess_type, "\r\n")
