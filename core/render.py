"""猜卡题图渲染：裁剪、模糊、切割、字符画。

移植自 nonebot-plugin-ocgbot-v2 的 ``guess_card.py::getGuessImg`` 与
``libraries/charpic.py``。原插件里 ``h, w = image.size`` 后按 ``(h * 0.13, ...)``
裁剪的写法（宽高写反）是它既有的出题效果，这里原样保留。
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

STR_MAP = "@@$$&B88QMMGW##EE93SPPDOOU**==()+^,\"--''.  "

_FONT_CANDIDATES = [
    # 插件自带字体（若用户放入）
    "data/fonts/consola.ttf",
    # Windows
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\consolab.ttf",
    # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansMono-Regular.ttf",
    # macOS
    "/System/Library/Fonts/Menlo.ttc",
]


def get_random(num: int) -> int:
    """原插件 ``libraries/tool.py::getRandom``。"""
    return random.randint(1, num) % num


def resolve_font(preferred: Optional[str] = None, base_dir: Optional[Path] = None) -> Optional[Path]:
    """找一个等宽字体，找不到时返回 ``None``（由调用方回退到默认字体）。"""
    candidates: list[Path] = []
    if preferred:
        candidates.append(Path(preferred))
        if base_dir is not None and not Path(preferred).is_absolute():
            candidates.append(Path(base_dir) / preferred)
    for item in _FONT_CANDIDATES:
        path = Path(item)
        if base_dir is not None and not path.is_absolute():
            path = Path(base_dir) / item
        candidates.append(path)
    for path in candidates:
        try:
            if path.is_file():
                return path
        except OSError:  # pragma: no cover - 权限异常
            continue
    return None


def _load_font(font_path: Optional[Path], size: int = 15):
    if font_path is not None:
        try:
            return ImageFont.truetype(str(font_path), size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def crop_card(image: Image.Image, card_type: str) -> Image.Image:
    """按卡种裁掉卡框，只留卡图区域。"""
    h, w = image.size
    if "灵摆" in card_type:
        return image.crop((h * 0.08, w * 0.2, h * 0.9, w * 0.6))
    return image.crop((h * 0.13, w * 0.19, h * 0.87, w * 0.7))


def char_pic(image: Image.Image, font_path: Optional[Path] = None) -> Image.Image:
    """把图片转成字符画再渲染成图。"""
    num = len(STR_MAP)
    font = _load_font(font_path, 15)

    gray_img = image.convert("L")
    gray_img = gray_img.resize((200, int(gray_img.height * 200 / gray_img.width)))
    gray_img = gray_img.resize((gray_img.width, gray_img.height // 2))

    lines = []
    for y in range(gray_img.height):
        chars = []
        for x in range(gray_img.width):
            gray = gray_img.getpixel((x, y))
            if gray != 0:
                chars.append(STR_MAP[int(num * gray / 256)])
            else:
                chars.append(" ")
        lines.append("".join(chars))
    text = "\n".join(lines)

    text_img = Image.new("RGB", (2000, 2000), "white")
    draw = ImageDraw.Draw(text_img)
    _, _, w, h = draw.multiline_textbbox((0, 0), text, font=font)
    draw.multiline_text((0, 0), text, font=font, fill="black")
    return text_img.crop((0, 0, w, h))


def get_guess_img(
    image: Image.Image,
    resize: int = 7,
    cut_size: int = 6,
    restrict: int = 3,
    font_path: Optional[Path] = None,
) -> Image.Image:
    """随机生成三种题图之一：模糊 / 切割 / 字符画。"""
    height, weight = image.size
    re_num = get_random(restrict)

    if re_num == 1:
        # 模糊处理
        image.thumbnail((height / resize, weight / resize), Image.LANCZOS)
        height, weight = image.size
        image = image.resize((height * resize, weight * resize))
    elif re_num == 2:
        # 切割处理
        sqrt = math.sqrt(cut_size)
        be_sqrt = cut_size / sqrt
        cut = (sqrt, be_sqrt) if get_random(2) == 1 else (be_sqrt, sqrt)
        cut_height = int(image.size[0] / cut[0])
        cut_weight = int(image.size[1] / cut[1])
        if cut_height <= 0 or cut_weight <= 0:  # pragma: no cover - 极小图片
            return image
        try:
            cut_x = random.randint(cut_height, height - cut_height)
            cut_y = random.randint(cut_weight, weight - cut_weight)
        except ValueError:  # 图太小，退回居中裁剪
            cut_x = max(0, (height - cut_height) // 2)
            cut_y = max(0, (weight - cut_weight) // 2)
        image = image.crop((cut_x, cut_y, cut_x + cut_height, cut_y + cut_weight))
    else:
        # 字符画
        image = char_pic(image, font_path)

    return image


def save_png(image: Image.Image, path: Path) -> Path:
    """把图片保存成 PNG（转 RGB，避免 RGBA/P 模式保存抖动）。"""
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(path), "PNG")
    return path
