import asyncio
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path

import aiohttp
from pyrogram import enums

from plugins.config import Config
from plugins.database.database import db
from plugins.functions.display_progress import progress_for_pyrogram, humanbytes, TimeFormatter
from plugins.functions.ran_text import random_char
from plugins.functions.split_upload import send_file_in_parts
from plugins.script import Translation
from plugins.thumbnail import Gthumb01, Gthumb02, Mdata01, Mdata02, Mdata03


logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)


def _message_url(message):
    text = (message.text or "").strip()
    if "|" in text:
        parts = text.split("|")
        if len(parts) >= 2:
            return parts[0].strip(), parts[1].strip()
    for entity in message.entities or []:
        if entity.type == "text_link":
            return entity.url, os.path.basename(entity.url.split("?", 1)[0]) or "download.bin"
        if entity.type == "url":
            return text[entity.offset:entity.offset + entity.length], None
    return text, None


def _safe_filename(name):
    name = os.path.basename(name or "download.bin")
    return "".join(ch if ch.isalnum() or ch in " .-_()[]" else "_" for ch in name)[:180] or "download.bin"


async def _send_regular_file(bot, update, path, send_type, caption):
    start_time = time.time()
    thumb_path = None
    try:
        if send_type == "audio":
            duration = await Mdata03(path)
            thumb_path = await Gthumb01(bot, update)
            await update.message.reply_audio(
                audio=path,
                caption=caption,
                parse_mode=enums.ParseMode.HTML,
                duration=duration,
                thumb=thumb_path,
                progress=progress_for_pyrogram,
                progress_args=(Translation.UPLOAD_START, update.message, start_time),
            )
        elif send_type == "vm":
            width, duration = await Mdata02(path)
            thumb_path = await Gthumb02(bot, update, duration, path)
            await update.message.reply_video_note(
                video_note=path,
                duration=duration,
                length=width,
                thumb=thumb_path,
                progress=progress_for_pyrogram,
                progress_args=(Translation.UPLOAD_START, update.message, start_time),
            )
        elif await db.get_upload_as_doc(update.from_user.id):
            width, height, duration = await Mdata01(path)
            thumb_path = await Gthumb02(bot, update, duration, path)
            await update.message.reply_video(
                video=path,
                caption=caption,
                duration=duration,
                width=width,
                height=height,
                supports_streaming=True,
                parse_mode=enums.ParseMode.HTML,
                thumb=thumb_path,
                progress=progress_for_pyrogram,
                progress_args=(Translation.UPLOAD_START, update.message, start_time),
            )
        else:
            thumb_path = await Gthumb01(bot, update)
            await update.message.reply_document(
                document=path,
                thumb=thumb_path,
                caption=caption,
                parse_mode=enums.ParseMode.HTML,
                progress=progress_for_pyrogram,
                progress_args=(Translation.UPLOAD_START, update.message, start_time),
            )
    finally:
        if thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except OSError:
                pass


async def ddl_call_back(bot, update):
    try:
        send_type, _, _ = update.data.split("=", 2)
    except ValueError:
        await update.message.edit_caption(caption=Translation.DOWNLOAD_FAILED)
        return False

    url, requested_name = _message_url(update.message.reply_to_message)
    if not url.lower().startswith(("http://", "https://")):
        await update.message.edit_caption(caption=Translation.NO_VOID_FORMAT_FOUND.format("Invalid URL"))
        return False

    work_dir = Path(Config.DOWNLOAD_LOCATION) / f"{update.from_user.id}_{random_char(6)}"
    work_dir.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(requested_name or Path(url.split("?", 1)[0]).name or "download.bin")
    path = work_dir / filename
    started = datetime.now()

    try:
        await update.message.edit_caption(
            caption=Translation.DOWNLOAD_START.format(filename),
            parse_mode=enums.ParseMode.HTML,
        )
        async with aiohttp.ClientSession() as session:
            await download_coroutine(
                bot, session, url, str(path), update.message.chat.id, update.message.id, time.time()
            )
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError("The URL returned no downloadable file")

        size = path.stat().st_size
        await update.message.edit_caption(
            caption=f"Download complete: {humanbytes(size)}\n{Translation.UPLOAD_START}",
            parse_mode=enums.ParseMode.HTML,
        )
        if size > Config.TG_MAX_FILE_SIZE:
            await send_file_in_parts(
                update.message,
                str(path),
                caption=Translation.CUSTOM_CAPTION_UL_FILE,
                progress_message="Uploading large-file part...",
            )
        else:
            await _send_regular_file(bot, update, str(path), send_type, Translation.CUSTOM_CAPTION_UL_FILE)
        elapsed = (datetime.now() - started).seconds
        await update.message.edit_caption(
            caption=Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(elapsed, 0),
            parse_mode=enums.ParseMode.HTML,
        )
        return True
    except asyncio.TimeoutError:
        await update.message.edit_caption(caption=Translation.SLOW_URL_DECED)
    except Exception as exc:
        logger.exception("Direct URL download failed")
        await update.message.edit_caption(caption=Translation.NO_VOID_FORMAT_FOUND.format(str(exc)[:500]))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    return False


async def download_coroutine(bot, session, url, file_name, chat_id, message_id, start):
    downloaded = 0
    last_update = 0.0
    chunk_size = max(int(getattr(Config, "CHUNK_SIZE", 1024 * 1024)), 1024 * 1024)
    timeout = aiohttp.ClientTimeout(total=Config.PROCESS_MAX_TIMEOUT)
    async with session.get(url, timeout=timeout, allow_redirects=True) as response:
        response.raise_for_status()
        total_length = int(response.headers.get("Content-Length", "0") or 0)
        content_type = response.headers.get("Content-Type", "")
        if total_length and "text" in content_type.lower() and total_length < 500:
            raise ValueError("URL returned a text response instead of a file")
        await bot.edit_message_text(
            chat_id,
            message_id,
            text=(
                f"Initiating Download\nURL: {url}\n"
                f"File Size: {humanbytes(total_length) if total_length else 'unknown'}"
            ),
        )
        with open(file_name, "wb") as output:
            while True:
                chunk = await response.content.read(chunk_size)
                if not chunk:
                    break
                output.write(chunk)
                downloaded += len(chunk)
                now = time.time()
                if now - last_update >= 5:
                    last_update = now
                    elapsed = max(now - start, 0.001)
                    if total_length:
                        speed = downloaded / elapsed
                        eta = ((total_length - downloaded) / speed) * 1000 if speed else 0
                        status = (
                            f"**Download Status**\nURL: {url}\n"
                            f"File Size: {humanbytes(total_length)}\n"
                            f"Downloaded: {humanbytes(downloaded)}\nETA: {TimeFormatter(eta)}"
                        )
                    else:
                        status = f"**Download Status**\nURL: {url}\nDownloaded: {humanbytes(downloaded)}"
                    try:
                        await bot.edit_message_text(chat_id, message_id, text=status)
                    except Exception:
                        pass
