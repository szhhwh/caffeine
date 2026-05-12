from pathlib import Path

from PIL import Image, ImageDraw

_SIZE = 64
_CUP_COLOR_ACTIVE = (139, 90, 43)
_CUP_COLOR_INACTIVE = (160, 160, 160)
_STEAM_COLOR_ACTIVE = (200, 120, 50)
_STEAM_COLOR_INACTIVE = (190, 190, 190)
_HANDLE_COLOR_ACTIVE = (120, 75, 35)
_HANDLE_COLOR_INACTIVE = (140, 140, 140)
_BG_ACTIVE = (255, 235, 200)
_BG_INACTIVE = (230, 230, 230)


def _draw_cup(draw: ImageDraw.Draw, color: tuple, handle_color: tuple) -> None:
    cup_left = 12
    cup_right = 44
    cup_top = 22
    cup_bottom = 52

    draw.rounded_rectangle(
        [cup_left, cup_top, cup_right, cup_bottom],
        radius=4,
        fill=color,
    )

    draw.ellipse(
        [cup_left - 1, cup_bottom - 8, cup_right + 1, cup_bottom + 4],
        fill=color,
    )

    handle_rect = [cup_right, cup_top + 8, cup_right + 10, cup_top + 26]
    draw.arc(handle_rect, start=-90, end=90, fill=handle_color, width=3)

    saucer_top = cup_bottom - 2
    draw.ellipse(
        [cup_left - 4, saucer_top, cup_right + 4, saucer_top + 8],
        fill=handle_color,
    )


def _draw_steam(draw: ImageDraw.Draw, color: tuple) -> None:
    for cx, offset_x in [(20, 0), (28, 2), (36, -1)]:
        for i in range(3):
            y = 18 - i * 5
            x = cx + offset_x * (i % 2) + (i % 3 - 1) * 2
            draw.arc(
                [x - 3, y - 6, x + 3, y],
                start=0,
                end=180,
                fill=color,
                width=2,
            )


def create_icon(active: bool = True) -> Image.Image:
    bg = _BG_ACTIVE if active else _BG_INACTIVE
    cup_color = _CUP_COLOR_ACTIVE if active else _CUP_COLOR_INACTIVE
    handle_color = _HANDLE_COLOR_ACTIVE if active else _HANDLE_COLOR_INACTIVE
    steam_color = _STEAM_COLOR_ACTIVE if active else _STEAM_COLOR_INACTIVE

    img = Image.new("RGBA", (_SIZE, _SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        [4, 4, _SIZE - 4, _SIZE - 4],
        radius=10,
        fill=bg,
    )

    _draw_cup(draw, cup_color, handle_color)
    _draw_steam(draw, steam_color)

    if not active:
        from PIL import ImageOps

        grayscale = ImageOps.grayscale(img.convert("RGB"))
        img = grayscale.convert("RGBA")
        px = img.load()
        for x in range(_SIZE):
            for y in range(_SIZE):
                r, g, b, a = px[x, y]
                if a > 0:
                    px[x, y] = (r, g, b, 180)

    return img


def create_ico(path: str | bytes | Path, sizes: tuple[int, ...] = (16, 32, 48, 256)) -> None:
    icon = create_icon(active=True).convert("RGBA")
    sorted_sizes = sorted(sizes, reverse=True)
    resized = [icon.resize((s, s), Image.LANCZOS) for s in sorted_sizes]
    resized[0].save(
        path,
        format="ICO",
        sizes=[(s, s) for s in sorted_sizes],
        append_images=resized[1:],
    )
