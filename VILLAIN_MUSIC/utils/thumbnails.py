import logging
import os
import re
import traceback

import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from py_yt import VideosSearch

logging.basicConfig(level=logging.INFO)

CARD_ASSET_PATH = "VILLAIN_MUSIC/assets/card.png"

BRAND_NAME = "Music"

_CARD_ASSET_CACHE = None


def get_card_asset():
    global _CARD_ASSET_CACHE
    if _CARD_ASSET_CACHE is None:
        raw = Image.open(CARD_ASSET_PATH).convert("RGBA")
        _CARD_ASSET_CACHE = raw.crop(raw.getbbox())
    return _CARD_ASSET_CACHE


def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    return image.resize((newWidth, newHeight))


def crop_center_square(img, output_size, radius_frac=0.09):
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((output_size, output_size))

    mask = Image.new("L", (output_size, output_size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, output_size, output_size), radius=int(output_size * radius_frac), fill=255
    )
    out = Image.new("RGBA", (output_size, output_size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def fit_text(text, font_path, size, max_w):
    font = ImageFont.truetype(font_path, size)
    if font.getlength(text) > max_w:
        while len(text) > 1 and font.getlength(text + "…") > max_w:
            text = text[:-1]
        text += "…"
    return text, font


async def gen_thumb(videoid: str):
    try:
        if os.path.isfile(f"cache/{videoid}_v4.png"):
            return f"cache/{videoid}_v4.png"

        url = f"https://www.youtube.com/watch?v={videoid}"
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            title = result.get("title")
            title = re.sub(r"\W+", " ", title).title() if title else "Unsupported Title"

            duration = result.get("duration") or "Live"

            thumbnail_data = result.get("thumbnails")
            thumbnail = thumbnail_data[0]["url"].split("?")[0] if thumbnail_data else None

            views_data = result.get("viewCount")
            views = (views_data.get("short") if views_data else None) or "Unknown Views"

            channel_data = result.get("channel")
            channel = (channel_data.get("name") if channel_data else None) or "Unknown Channel"

        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    filepath = f"cache/thumb{videoid}.png"
                    f = await aiofiles.open(filepath, mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        image_path = f"cache/thumb{videoid}.png"
        youtube = Image.open(image_path).convert("RGB")

        W, H = 1280, 720

        background = ImageOps.fit(youtube, (W, H)).convert("RGBA")
        background = background.filter(ImageFilter.GaussianBlur(18))
        background = ImageEnhance.Brightness(background).enhance(0.55)

        card_asset = get_card_asset()
        card_w = 780
        card_h = int(card_w * card_asset.size[1] / card_asset.size[0])
        card = card_asset.resize((card_w, card_h))
        card_x = (W - card_w) // 2
        card_y = (H - card_h) // 2
        background.alpha_composite(card, (card_x, card_y))

        draw = ImageDraw.Draw(background)

        thumb_size = int(card_w * 0.28)
        thumb = crop_center_square(youtube, thumb_size)
        thumb_x = card_x + int(card_w * 0.072)
        thumb_y = card_y + int(card_h * 0.116)
        background.alpha_composite(thumb, (thumb_x, thumb_y))

        text_x = card_x + int(card_w * 0.377)
        text_max_w = (card_x + card_w) - int(card_w * 0.05) - text_x

        brand_font = ImageFont.truetype("VILLAIN_MUSIC/assets/font.ttf", int(card_h * 0.028))
        title_text, title_font = fit_text(
            title, "VILLAIN_MUSIC/assets/font3.ttf", int(card_h * 0.062), text_max_w
        )
        sub_text, sub_font = fit_text(
            f"{channel} | {views[:23]}", "VILLAIN_MUSIC/assets/font2.ttf", int(card_h * 0.050), text_max_w
        )

        brand_y = card_y + int(card_h * 0.183)
        title_y = card_y + int(card_h * 0.248)
        sub_y = card_y + int(card_h * 0.33)
        draw.text((text_x, brand_y), BRAND_NAME, font=brand_font, fill=(210, 210, 210))
        draw.text((text_x, title_y), title_text, font=title_font, fill=(255, 255, 255))
        draw.text((text_x, sub_y), sub_text, font=sub_font, fill=(225, 225, 225))

        dur_font = ImageFont.truetype("VILLAIN_MUSIC/assets/font2.ttf", int(card_h * 0.032))
        bar_y = card_y + int(card_h * 0.625)
        bar_x_start = card_x + int(card_w * 0.144)
        bar_x_end = card_x + int(card_w * 0.840)

        current = "00:00" if duration != "Live" else "LIVE"
        draw.text((bar_x_start - 12, bar_y), current, font=dur_font, fill=(255, 255, 255), anchor="rm")
        draw.text((bar_x_end + 12, bar_y), duration, font=dur_font, fill=(255, 255, 255), anchor="lm")

        os.remove(f"cache/thumb{videoid}.png")

        background_path = f"cache/{videoid}_v4.png"
        background.convert("RGB").save(background_path)

        return background_path

    except Exception as e:
        logging.error(f"Error generating thumbnail for video {videoid}: {e}")
        traceback.print_exc()
        return None
