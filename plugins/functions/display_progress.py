import math
import time

from pyrogram import enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from plugins.script import Translation


async def progress_for_pyrogram(current, total, ud_type, message, start, job_id=None):
    now = time.time()
    diff = max(now - start, 0.001)
    total = max(int(total or 0), 1)
    current = min(max(int(current or 0), 0), total)
    percentage = current * 100 / total
    speed = current / diff
    elapsed_time_ms = round(diff * 1000)
    remaining = max(total - current, 0)
    eta_ms = round((remaining / speed) * 1000) if speed > 0 else 0

    if current != total and int(now) % 10 != 0:
        return

    progress = "┏━━━━✦[{0}{1}]✦━━━━".format(
        "".join("▣" for _ in range(math.floor(percentage / 10))),
        "".join("▢" for _ in range(10 - math.floor(percentage / 10))),
    )
    body = progress + Translation.PROGRESS.format(
        round(percentage, 2),
        humanbytes(current),
        humanbytes(total),
        humanbytes(speed),
        TimeFormatter(eta_ms) if eta_ms else "0 s",
    )
    callback = f"cancel_download+{job_id}" if job_id else "close"
    try:
        await message.edit(
            text=Translation.PROGRES.format(ud_type, body),
            parse_mode=enums.ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("⛔ Cancel", callback_data=callback)]]
            ),
        )
    except Exception:
        pass


def humanbytes(size):
    if size is None:
        return "0 B"
    size = float(size)
    if size <= 0:
        return "0 B"
    units = ("B", "KB", "MB", "GB", "TB")
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{round(size, 2)} {units[index]}"


def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(max(milliseconds, 0)), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    if not parts and milliseconds:
        parts.append(f"{milliseconds}ms")
    return ", ".join(parts) or "0s"
