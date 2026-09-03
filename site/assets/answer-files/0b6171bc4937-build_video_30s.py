"""
30 秒竖屏商品推广视频生成脚本（基于 ecommerce-full-pipeline Skill 的 video_generator 逻辑适配）

复用 Skill 原生能力：
- 9:16 竖屏构图
- Ken Burns 慢推拉（resize lambda，奇偶段反向）
- PIL 烧录文字 + 底部信息栏（_create_image_slide 同款做法，规避 ImageMagick 依赖）
- 淡入淡出
- 无 bgm.mp3 时不挂音轨（本次显式 audio=False，满足"不使用未授权音乐"）

本次适配点（题目要求）：
- 钩子段 3s -> 2s（前 2 秒建立信息钩子）
- 总时长 15s -> 30s
- 分辨率 720x1280 -> 1080x1920
- 字体路径改为 macOS 系统字体（Skill 原路径为 Linux DejaVuSans）
- 全程文字烧录，手机静音可理解
- 不使用任何人物/品牌/音乐素材
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy import ImageClip, concatenate_videoclips, vfx

# ── 基本参数 ──
W, H = 1080, 1920
FPS = 24
ASSET_DIR = "/Users/bytedance/Doubao/chats/2026-08-12/new-chat-447/video_assets"
OUT_PATH = "/Users/bytedance/Doubao/chats/2026-08-12/new-chat-447/promo_minipowerbank_30s.mp4"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REG = "/System/Library/Fonts/Helvetica.ttc"

# 沿用 Skill COLOR_SCHEMES 第一套：白底 / 深灰字 / 红色 accent
TEXT = (30, 30, 30)
ACCENT = (255, 107, 107)
WHITE = (255, 255, 255)
DARK = (18, 18, 22)


def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def cover_crop(img, w, h):
    """居中裁剪为 w:h（与 Skill _create_image_slide 裁剪逻辑一致）"""
    iw, ih = img.size
    target = w / h
    cur = iw / ih
    if cur > target:
        new_w = int(ih * target)
        left = (iw - new_w) // 2
        img = img.crop((left, 0, left + new_w, ih))
    else:
        new_h = int(iw / target)
        top = (ih - new_h) // 2
        img = img.crop((0, top, iw, top + new_h))
    return img.resize((w, h), Image.LANCZOS)


def draw_center(draw, text, y, fnt, fill, w=W):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) // 2, y), text, font=fnt, fill=fill)


def make_hook_frame():
    """0-2s 信息钩子：痛点大字 + 产品图 + 副文"""
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)

    # 顶部红色装饰条
    draw.rectangle([W // 2 - 60, 220, W // 2 + 60, 232], fill=ACCENT)

    # 痛点钩子大字（前 2 秒核心信息）
    draw_center(draw, "PHONE", 300, font(130), WHITE)
    draw_center(draw, "AT 1%?", 450, font(130), ACCENT)

    # 产品图（缩小居中）
    prod = Image.open(os.path.join(ASSET_DIR, "p1_hero.jpg")).convert("RGB")
    prod = cover_crop(prod, 560, 760)
    # 圆角蒙版
    mask = Image.new("L", (560, 760), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 560, 760], radius=40, fill=255)
    img.paste(prod, ((W - 560) // 2, 660), mask)

    # 副文
    draw_center(draw, "This charger is", 1500, font(54), WHITE)
    draw_center(draw, "lipstick-size.", 1580, font(74), ACCENT)
    draw_center(draw, "Swipe up / Keep watching", 1720, font(36), (170, 170, 175))
    return img


def make_product_frame(img_path, headline, subhead, price=None, cta=False):
    """商品展示帧：商品图 + 底部信息栏（沿用 Skill 底部信息栏设计）"""
    bg = Image.open(img_path).convert("RGB")
    bg = cover_crop(bg, W, H)

    # 底部信息栏（CTA 页内容更多，加高）
    overlay_h = 540 if cta else (470 if price else 380)
    overlay = Image.new("RGBA", (W, overlay_h), (255, 255, 255, 238))
    bg.paste(overlay, (0, H - overlay_h), overlay)

    draw = ImageDraw.Draw(bg)

    # 顶部小标签（红色胶囊，加宽避免文字溢出）
    bx0, by0 = 60, 90
    tag = "MINI POWER BANK"
    tf = font(34)
    tb = draw.textbbox((0, 0), tag, font=tf)
    tw = tb[2] - tb[0]
    bx1 = bx0 + tw + 56
    draw.rounded_rectangle([bx0, by0, bx1, by0 + 60], radius=30, fill=ACCENT)
    draw.text((bx0 + 28, by0 + 11), tag, font=tf, fill=WHITE)

    # 底部文案
    y0 = H - overlay_h + 40
    draw.text((60, y0), headline, font=font(72), fill=TEXT)
    draw.text((60, y0 + 100), subhead, font=font(46), fill=(90, 90, 95))

    if price is not None and not cta:
        draw.text((60, y0 + 200), f"${price:.2f}", font=font(86), fill=ACCENT)
        draw.text((60, y0 + 310), "Factory direct", font=font(34), fill=(120, 120, 125))

    if cta:
        # 价格 + CTA 按钮 + 引导
        draw.text((60, y0 + 190), f"${price:.2f}", font=font(76), fill=ACCENT)
        btn_w, btn_h = 640, 130
        bx, by = (W - btn_w) // 2, y0 + 300
        draw.rounded_rectangle([bx, by, bx + btn_w, by + btn_h], radius=65, fill=ACCENT)
        cta_text = "SHOP NOW"
        cf = font(60)
        cb = draw.textbbox((0, 0), cta_text, font=cf)
        draw.text((bx + (btn_w - (cb[2] - cb[0])) // 2, by + 28),
                  cta_text, font=cf, fill=WHITE)
        draw_center(draw, "Link in bio", by + btn_h + 22, font(38), (90, 90, 95))

    return bg


def ken_burns(clip, duration, zoom_in=True):
    """Ken Burns 慢推拉（复用 Skill _create_image_slide 的 resize lambda 写法，适配 moviepy 2.x 的 resized）"""
    if zoom_in:
        return clip.resized(lambda t: 1 + 0.06 * t / duration)
    return clip.resized(lambda t: 1.06 - 0.06 * t / duration)


def build():
    frames_dir = "/Users/bytedance/Doubao/chats/2026-08-12/new-chat-447/video_assets/_frames"
    os.makedirs(frames_dir, exist_ok=True)

    # 分镜：(帧图, 时长秒, Ken Burns 方向)
    scenes = [
        (make_hook_frame(), 2.0, None),
        (make_product_frame(os.path.join(ASSET_DIR, "p1_hero.jpg"),
                            "Mini Power Bank", "5000mAh emergency charger", price=19.31), 6.0, True),
        (make_product_frame(os.path.join(ASSET_DIR, "p2_size.jpg"),
                            "Lipstick-Size", "Smaller than a credit card"), 5.0, False),
        (make_product_frame(os.path.join(ASSET_DIR, "p3_bag.jpg"),
                            "Slips Into Any Bag", "Pocket-friendly & ultra light"), 5.0, True),
        (make_product_frame(os.path.join(ASSET_DIR, "p4_charge.jpg"),
                            "Fast Charging", "USB-C input, power on the go"), 5.0, False),
        (make_product_frame(os.path.join(ASSET_DIR, "p5_detail.jpg"),
                            "USB-C + LED Gauge", "Know your battery at a glance"), 4.0, True),
        (make_product_frame(os.path.join(ASSET_DIR, "p1_hero.jpg"),
                            "Grab Yours Today", "5000mAh mini power bank", price=19.31, cta=True), 3.0, False),
    ]

    clips = []
    for i, (frame, dur, zoom_in) in enumerate(scenes):
        fp = os.path.join(frames_dir, f"frame_{i}.png")
        frame.save(fp)
        c = ImageClip(fp).with_duration(dur)
        if zoom_in is not None:
            c = ken_burns(c, dur, zoom_in=zoom_in)
        c = c.with_effects([vfx.FadeIn(0.3), vfx.FadeOut(0.3)])
        clips.append(c)

    final = concatenate_videoclips(clips, method="compose").with_fps(FPS)
    # Ken Burns 放大后画布会超出 1080x1920，居中裁回（放大的溢出部分被画布裁切）
    final = final.cropped(x_center=W / 2, y_center=H / 2, width=W, height=H)
    final.write_videofile(
        OUT_PATH, fps=FPS, codec="libx264",
        audio=False,            # 无音轨：不使用未授权音乐
        bitrate="4000k",
        preset="medium",
        threads=4,
        ffmpeg_params=["-pix_fmt", "yuv420p"],
        logger=None,
    )
    for c in clips:
        c.close()
    final.close()
    print(f"OK -> {OUT_PATH}")


if __name__ == "__main__":
    build()
