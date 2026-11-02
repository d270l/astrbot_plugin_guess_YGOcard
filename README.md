<div align="center">


# astrbot_plugin_guess_YGOcard

_🃏 在群里玩「猜一张卡」：模糊、切割、字符画三种出题，三次机会，30 秒公布答案_

![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![AstrBot](https://img.shields.io/badge/AstrBot-4.x-orange.svg)
![Platform](https://img.shields.io/badge/platform-aiocqhttp%20%7C%20qq%20official%20%7C%20telegram%20%7C%20discord-lightgrey.svg)

</div>

---

## 📖 简介

`astrbot_plugin_guess_YGOcard` 是一个 **游戏王猜卡小游戏** 插件：机器人随机抽一张游戏王卡片，裁掉卡框后随机做 **模糊 / 切割 / 字符画** 三种处理之一，玩家看着残缺的题图猜卡名，三次机会用完或倒计时结束就公布答案与原图。

本插件把 [nonebot-plugin-ocgbot-v2](https://github.com/fireinsect/nonebot-plugin-ocgbot-v2) 里的「猜一张卡」玩法移植到了 AstrBot，出题算法、提示规则与台词都按原作实现，并在交互上做了适配：**群里直接发卡名就能作答，不需要 @ 机器人**。

---

## ✨ 功能特性

| | |
| --- | --- |
| 🎲 **三种出题模式** | 模糊、切割、字符画随机出现，参数与原作一致，可在配置里调整强度 |
| 💡 **三次机会 + 递进提示** | 第一次提示卡片类型，第二次给种族 / 属性 / 完整类型，第三次公布答案 |
| ⏱️ **30 秒倒计时** | 超时自动公布答案并发原图，倒计时与提示语可配置 |
| 💬 **免 @ 直接作答** | 局内直接在群里发卡名即可，插件只接管自己的消息，不影响其它插件与大模型 |
| 👥 **同群多局并行** | 按「群 + 用户」隔离，一个群可以同时开多局，各自计时互不干扰 |
| 📚 **内置卡库** | 自带 `cards.cdb` 与卡名别名表，装好即用，支持按 ID / 卡名 / 别名模糊查询 |
| 🖼️ **卡图自动缓存** | 本地缺图时联网下载并缓存，也可指定本地卡图目录或关闭联网 |
| 🔧 **完整配置** | 13 项玩法配置 + 22 项文案配置，可整套替换机器人的回复 |
| 🛡️ **管理便捷** | 冷却与开关按群持久化，仅群主 / 群管理员 / Bot 管理员可修改 |

---

## 🎬 效果预览

| 模糊 | 切割 | 字符画 |
| :---: | :---: | :---: |
| <img src="docs/images/mode-blur.png" width="220" /> | <img src="docs/images/mode-cut.png" width="220" /> | <img src="docs/images/mode-char.jpg" width="220" /> |

在群里的对话大致是：

```
玩家：游戏王猜卡
机器人：@玩家 哥哥大人，你有三次机会哟~30秒后公布答案！(输入跳过结束游戏)
        [题图]
玩家：青眼白龙
机器人：@玩家 咦？这张卡是怪兽卡
        还有2次机会！
```

---

## 📦 安装

### 环境要求

- **AstrBot** 4.x（在 4.29.1 上开发与测试）
- **Python** 3.10+
- **Pillow**：AstrBot 通常已自带；若日志提示缺失，见下方[常见问题](#-常见问题)

### 方式一：从链接安装（推荐）

1. 进入 AstrBot 管理面板 → 左侧 **插件** → **插件市场 / 已安装** 页面右下角的 **安装插件（+）**；
2. 选择 **从链接安装**，填入本仓库地址：

   ```
   https://github.com/d270l/astrbot_plugin_guess_YGOcard
   ```

3. 确认来源并安装，回到 **已安装** 页面确认插件已打开、没有加载错误；
4. 如需调整参数，点插件卡片上的齿轮图标进入 **插件配置**。

### 方式二：手动安装

把整个仓库文件夹放进 AstrBot 的插件目录：

```
AstrBot/
└── data/
    └── plugins/
        └── astrbot_plugin_guess_YGOcard/
            ├── main.py
            ├── metadata.yaml
            ├── _conf_schema.json
            ├── core/
            ├── data/
            └── ...
```

然后重启 AstrBot，或在面板 **已安装** 页面点击 **重载**。

### 方式三：从文件安装

下载本仓库的 ZIP 包，在 **安装插件（+）→ 从文件安装** 里上传即可（ZIP 内需保持上表的目录结构）。

### 更新

在 **已安装** 页面点击 **更新**（从 Git 仓库重新拉取），或手动替换文件后点 **重载**。更新前建议备份 `data/plugin_data/astrbot_plugin_guess_YGOcard/`（冷却与开关配置）。

---

## 🎮 使用方法

### 指令

| 指令 | 说明 | 权限 |
| --- | --- | --- |
| `游戏王猜卡` / `猜一张卡` | 开始一局猜卡 | 所有人 |
| 直接发送卡名 | 局内作答（无需 @ 机器人、无需唤醒前缀） | 局内玩家 |
| `跳过` / `不知道` | 放弃本局并立即公布答案 | 局内玩家 |
| `猜卡重置` | 重置自己当前的猜卡状态 | 所有人 |
| `猜卡cd <秒>` | 设置本群的猜卡冷却时间 | 群主 / 群管理员 / Bot 管理员 |
| `猜卡功能 on` / `off` | 开启 / 关闭本群的猜卡功能 | 群主 / 群管理员 / Bot 管理员 |

> 指令前缀沿用 AstrBot 的唤醒前缀（默认 `/`）。在群里 @ 机器人并发指令同样可用；**不 @ 也可以**，插件会自己接管上述指令词与局内作答。

### 提示规则

| 第几次猜错 | 提示内容 |
| --- | --- |
| 第 1 次 | 卡片类型：是怪兽卡 / 魔法卡 / 陷阱卡 |
| 第 2 次 | 怪兽：随机给「种族 / 属性 / 完整类型」之一；魔法陷阱：完整类型 |
| 第 3 次 | 公布卡名并发原图 |

### 判定规则

与原作一致，尽量让口语化的答案也算对：

- 答案包含在卡名中，且长度不少于卡名长度的 1/3（例如「青眼白龙」→「白龙」）；
- 模糊查询命中（含别名表，例如「黑魔导」→「黑魔导士」）；
- 多条结果时，只要有一条与目标卡名完全一致就算对。

---

## ⚙️ 配置说明

全部配置都在 **插件配置** 面板中，字段定义见 [`_conf_schema.json`](_conf_schema.json)。

| 配置项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `cdb_path` | string | `""` | 卡库路径（文件或所在目录），留空用内置 `data/cards.cdb` |
| `pics_dir` | string | `""` | 卡图目录，留空用 `data/pics` |
| `use_web_pic` | bool | `true` | 本地缺图时联网下载并缓存 |
| `pic_url_template` | string | `https://cdn.233.momobako.com/ygopro/pics/{id}.jpg` | 卡图地址模板，`{id}` 为卡图编号 |
| `guess_times` | int | `3` | 每局机会次数（1–10） |
| `answer_timeout` | int | `30` | 公布答案倒计时，单位秒（5–300） |
| `blur_scale` | int | `7` | 模糊模式缩放倍数，越大越模糊（2–20） |
| `cut_size` | int | `6` | 切割模式切块数，越大块越小（2–16） |
| `at_sender` | bool | `true` | 开局时是否 @ 玩家 |
| `default_cd` | int | `20` | 默认猜卡冷却（秒），可用 `猜卡cd` 按群覆盖 |
| `mess_type` | string | `正常` | 语录风格：`正常` 或 `雌小鬼` |
| `font_path` | string | `""` | 字符画模式字体，留空自动查找系统等宽字体 |
| `use_web_search` | bool | `false` | 本地卡库查不到时，用 ygocdb.com 兜底查询 |

> 另有 22 项 `text_*` 文案配置，用来替换机器人说出的每一句话，详见下一节。

---

## 💬 自定义回复文案

机器人说的每句话都能改，对应配置里的 `text_*` 字段：

- **留空** → 使用内置文案（保留原作的随机台词，以及「正常 / 雌小鬼」两套语录）；
- **填写** → 用你写的模板，里面可以放占位符，未使用的占位符会被忽略；
- 用 `|` 分隔可以一次写多条，每次随机抽一条：`答对啦！|厉害，答案就是{name}`。

### 可用占位符

| 占位符 | 含义 | 出现位置 |
| --- | --- | --- |
| `{named}` | 随机称呼，例如「哥哥大人」 | 大部分文案 |
| `{name}` | 答案卡名 | 猜对 / 猜错 / 跳过 / 超时 |
| `{times}` | 每局机会次数（数字） | 开局 |
| `{times_text}` | 机会次数的中文写法，3 次时为「三」，其它为数字 | 开局 |
| `{timeout}` | 公布答案的倒计时秒数 | 开局 |
| `{hint}` | 递进提示片段，例如「是怪兽卡」 | 猜错提示 |
| `{left}` | 剩余机会次数 | 剩余次数 |
| `{type}` | 卡片完整类型，例如「怪兽 效果」 | 类型提示 / 完整类型提示 |
| `{zz}` | 怪兽种族，例如「龙族」 | 种族提示 |
| `{attribute}` | 怪兽属性，例如「光」 | 属性提示 |
| `{cd}` | 剩余冷却时间，例如「12秒」 | 冷却提示 |
| `{old}` / `{new}` | 修改前后的冷却秒数 | `猜卡cd` 回复 |
| `{arg}` | 用户输入的原始参数 | 参数错误提示 |

### 文案配置项

| 配置项 | 作用的回复 | 默认值 |
| --- | --- | --- |
| `text_start` | 开局文案 | `{named}，你有{times_text}次机会哟~{timeout}秒后公布答案！(输入跳过结束游戏)` |
| `text_timeout` | 超时公布答案 | 随机多句，如「时间到啦！答案是{name}哦~」 |
| `text_win` | 猜对 | 随机多句，如「{named}好厉害！答案就是{name}啦」 |
| `text_lose` | 机会用尽 | 随机多句，如「答案是{name}哦~，{named}再接再厉吧~」 |
| `text_skip` | 跳过 / 不知道 | 随机多句，与「机会用尽」同一套风格 |
| `text_tip` | 猜错提示的主句 | 随机多句，如「{named}答不出来吗，小蓝提醒你一下这张卡{hint}。」 |
| `text_hint_type` | 第一次猜错的提示片段 | `是{type}卡` |
| `text_hint_zz` | 第二次猜错（怪兽）种族片段 | `种族是{zz}` |
| `text_hint_attribute` | 第二次猜错（怪兽）属性片段 | `属性是{attribute}` |
| `text_hint_fulltype` | 第二次猜错的完整类型片段 | `完整类型是{type}` |
| `text_left` | 提示后面的剩余次数 | 换行后接「还有{left}次机会！」 |
| `text_cd` | 冷却未到 | 随机开场白 + 「你的CD还有{cd}！」 |
| `text_reset` | 猜卡重置 | `猜卡状态已重置` |
| `text_off` | 本群功能已关闭 | `猜卡功能已关闭！` |
| `text_no_permission` | 权限不足 | `只有群主、群管理员或 Bot 管理员才能使用该指令哦~` |
| `text_image_missing` | 找不到卡图 | `对应图片不存在，无法进行猜卡~` |
| `text_not_ready` | 插件未就绪 | `猜卡功能还没有准备好，请稍后再试~` |
| `text_invalid_cd` | `猜卡cd` 参数错误 | `无效参数: {arg}, 请输入 正整数 或 0 为参数` |
| `text_invalid_switch` | `猜卡功能` 参数错误 | `无效参数: {arg}, 请输入 on 或 off 为参数` |
| `text_cd_updated` | `猜卡cd` 设置成功 | `cd更新成功 {old} -> {new}` |
| `text_switch_off` | `猜卡功能 off` | `功能已经关闭` |
| `text_switch_on` | `猜卡功能 on` | `功能已经开启` |

> 表里的「默认值」是「正常」语录中的一条，实际留空时会保留原作的随机台词；「雌小鬼」语录同理。

### 配置示例

把机器人改成干员口吻，只覆盖几句：

```json
{
  "text_start": "博士，作战开始。你有{times_text}次机会，{timeout}秒后揭晓答案。",
  "text_win": "判断正确，博士。答案就是{name}。",
  "text_lose": "判断失误。正确答案是{name}。",
  "text_tip": "线索：这张卡{hint}。|再想想，它是{hint}。",
  "text_left": "\n剩余机会：{left}"
}
```

保存后重载插件即可生效，其余没填的文案继续使用内置台词。

---

## 🃏 卡图与卡库

- **卡库**：`data/cards.cdb`（SQLite，取自 YGOPRO 生态的公开卡库），随插件分发，开箱即用。
- **卡图**：
  - 优先读 `pics_dir/{卡图ID}.jpg`；
  - 找不到且 `use_web_pic` 开启时，按 `pic_url_template` 下载并缓存到 `pics_dir`；
  - 两者都失败会提示「对应图片不存在，无法进行猜卡~」。

  如果你本地已有 YGOPRO 卡图目录（通常包含 `pics/*.jpg`），把 `pics_dir` 指过去即可完全离线运行。

---

## ❓ 常见问题

<details>
<summary><b>提示「对应图片不存在，无法进行猜卡~」</b></summary>

说明这张卡既没有本地卡图，联网下载也失败了。检查：

1. `pics_dir` 下是否有 `{卡图ID}.jpg`；
2. AstrBot 所在机器能否访问 `pic_url_template`（你的浏览器能打开，不代表服务器能打开）；
3. 需要完全离线时，把 `use_web_pic` 关掉并准备好本地卡图。
</details>

<details>
<summary><b>提示「猜卡功能已关闭！」</b></summary>

本群被管理员用 `猜卡功能 off` 关闭了，发送 `猜卡功能 on` 重新开启即可。
</details>

<details>
<summary><b>提示 CD 未到</b></summary>

同一玩家两次开局之间有冷却（默认 20 秒），群管理员可用 `猜卡cd 0` 关闭本群冷却。
</details>

<details>
<summary><b>缺少 Pillow 依赖</b></summary>

在 AstrBot 的 **数据与日志 → 日志** 页面用 Pip 安装入口安装 `Pillow`，并确保装进 AstrBot 实际运行的 Python 环境（Docker 部署时不要只装在宿主机）。
</details>

<details>
<summary><b>字符画糊成一团 / 字体警告</b></summary>

字符画模式需要等宽字体。插件会按 `font_path` → 系统 `consola.ttf` / `DejaVu Sans Mono` / `Noto Sans Mono` 的顺序查找，都没有则回退 Pillow 内置字体（效果较差）。可在 `font_path` 里指定一个等宽字体文件路径。
</details>

<details>
<summary><b>会不会抢别的插件的消息？</b></summary>

不会。插件通过自定义过滤器只在两种情况下接管消息：以猜卡指令词开头，或该用户当前正处于猜卡局中。其它群消息照常交给 AstrBot 的其它插件与大模型。
</details>

<details>
<summary><b>想让机器人换一种说话风格</b></summary>

用配置里的 `text_*` 文案字段覆盖内置台词即可，详见 [自定义回复文案](#-自定义回复文案)。只填你想改的那几句，其余留空继续用内置文案。
</details>

<details>
<summary><b>支持哪些消息平台？</b></summary>

需要能发送图片消息的平台，例如 QQ（aiocqhttp / OneBot v11、QQ 官方机器人）、Telegram、Discord 等。作答依赖「群里直接发文本」，因此在私聊中同样可用（按私聊会话隔离）。
</details>

---

## 🗂️ 项目结构

```
astrbot_plugin_guess_YGOcard/
├── main.py
├── metadata.yaml
├── _conf_schema.json
├── requirements.txt
├── logo.png
├── CHANGELOG.md
├── LICENSE
├── NOTICE
├── core/
│   ├── __init__.py
│   ├── carddb.py
│   ├── game.py
│   ├── render.py
│   ├── replies.py
│   ├── store.py
│   └── texts.py
├── data/
│   ├── cards.cdb
│   ├── nickname.json
│   └── pics/
└── docs/images/
```

---

## 🛠️ 开发与测试

- 插件类 `GuessCardPlugin(Star)`，位于 `main.py`；核心逻辑与 AstrBot 解耦，`core/` 下模块可单独测试。
- 状态保存：`data/plugin_data/astrbot_plugin_guess_YGOcard/guess_cfg.json`（冷却与开关），题图缓存放在同目录 `cache/` 下并自动清理。
- 修改代码后在面板点 **重载** 即可生效，无需重启整个 AstrBot。

本地自测的要点：

```python
from core.carddb import CardDB
from core.render import crop_card, get_guess_img
from PIL import Image

db = CardDB("data/cards.cdb", "data/nickname.json")
card = db.get_random_card().cards[0]
quiz = get_guess_img(crop_card(Image.open("pic.jpg"), card.type))
```

---



## 🙏 致谢

- 玩法、提示文案与出题算法来自 [fireinsect/nonebot-plugin-ocgbot-v2](https://github.com/fireinsect/nonebot-plugin-ocgbot-v2)（MIT）。
- 卡库来自 YGOPRO 生态的公开 `cards.cdb`；卡图来自公开 CDN。
- 游戏王及其卡片名称、卡图版权归 KONAMI / 原作者所有，本项目仅用于学习与技术交流。

---

## 📄 许可证

[MIT](LICENSE) © 2026 astrbot_plugin_guess_YGOcard contributors

本移植版本同样以 MIT 发布，原始项目署名见 [NOTICE](NOTICE)。

