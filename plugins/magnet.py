import asyncio
import os
import re
import shutil
from pathlib import Path

from pyrogram import Client, filters, enums

from plugins.config import Config
from plugins.database.add import AddUser
from plugins.functions.forcesub import handle_force_subscribe
from plugins.functions.ran_text import random_char
from plugins.functions.split_upload import send_file_in_parts
from plugins.functions.verify import check_verification


MAGNET_RE = r"^magnet:\?xt=urn:btih:[^\s]+$"


def _safe_name(path: Path) -> str:
    return re.sub(r"[\\/:*?\"<>|]", "_", path.name)[:180]


@Client.on_message(filters.private & filters.regex(MAGNET_RE))
async def magnet_download(bot, message):
    if not message.from_user:
        return
    await AddUser(bot, message)
    if Config.TRUE_OR_FALSE and not await check_verification(bot, message.from_user.id):
        await message.reply_text("Please verify first to use this bot.", quote=True)
        return
    if Config.UPDATES_CHANNEL and await handle_force_subscribe(bot, message) == 400:
        return
    magnet = message.text.strip()
    work_dir = Path(Config.DOWNLOAD_LOCATION) / f"{message.from_user.id}_{random_char(6)}" / "torrent"
    work_dir.mkdir(parents=True, exist_ok=True)
    status = await message.reply_text("Torrent download শুরু হয়েছে...", quote=True)

    command = [
        "aria2c",
        "--dir", str(work_dir),
        "--seed-time=0",
        "--file-allocation=none",
        "--follow-torrent=mem",
        "--bt-enable-lpd=true",
        "--bt-tracker-connect-timeout=30",
        "--bt-request-peer-speed-limit=1M",
        "--summary-interval=5",
        "--console-log-level=warn",
        magnet,
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(
            process.communicate(), timeout=Config.TORRENT_TIMEOUT
        )
        if process.returncode != 0:
            error = stderr.decode(errors="replace").strip()[-2500:]
            await status.edit_text(f"Torrent download ব্যর্থ হয়েছে:\n<code>{error}</code>", parse_mode=enums.ParseMode.HTML)
            return

        files = [p for p in work_dir.rglob("*") if p.is_file() and ".aria2" not in p.name]
        if not files:
            await status.edit_text("Torrent থেকে কোনো file পাওয়া যায়নি।")
            return

        await status.edit_text(f"{len(files)}টি file পাওয়া গেছে। Upload শুরু হচ্ছে...")
        for index, path in enumerate(sorted(files), 1):
            safe_path = path.with_name(_safe_name(path))
            if safe_path != path:
                path.rename(safe_path)
                path = safe_path
            await send_file_in_parts(
                message,
                str(path),
                caption=f"Torrent file {index}/{len(files)}: {path.name}",
                progress_message="Uploading torrent file...",
            )
        await status.edit_text("Torrent-এর সব file upload সম্পন্ন হয়েছে।")
    except asyncio.TimeoutError:
        await status.edit_text("Torrent download timeout হয়েছে।")
    except FileNotFoundError:
        await status.edit_text("aria2c পাওয়া যায়নি; Railway Dockerfile redeploy করুন।")
    except Exception as exc:
        await status.edit_text(f"Torrent processing error: {str(exc)[:2000]}")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
