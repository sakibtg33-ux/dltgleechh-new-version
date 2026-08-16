import os
import time
from typing import Awaitable, Callable, Optional

from plugins.config import Config


async def send_file_in_parts(
    message,
    file_path: str,
    caption: str = "",
    progress_message: Optional[str] = None,
    progress_args_factory: Optional[Callable[[object, float], tuple]] = None,
) -> int:
    """Send a file directly when possible, otherwise split it into Telegram-safe parts.

    Parts are temporary files named ``<original>.partNNN`` and are deleted after upload.
    The function deliberately uses documents for split parts so that arbitrary binary files
    and video segments are handled consistently.
    """
    try:
        from plugins.functions.display_progress import progress_for_pyrogram
    except ImportError:
        progress_for_pyrogram = None

    size = os.path.getsize(file_path)
    limit = int(getattr(Config, "TG_MAX_FILE_SIZE", 2194304000))
    if size <= limit:
        kwargs = {"document": file_path, "caption": caption}
        if progress_for_pyrogram is not None:
            kwargs.update(
                progress=progress_for_pyrogram,
                progress_args=(progress_message or "Uploading...", message, time.time()),
            )
        await message.reply_document(**kwargs)
        return 1

    part_size = min(int(getattr(Config, "UPLOAD_PART_SIZE", limit)), limit)
    if part_size <= 0:
        part_size = limit
    total_parts = (size + part_size - 1) // part_size
    sent = 0
    with open(file_path, "rb") as source:
        for part_number in range(1, total_parts + 1):
            part_path = f"{file_path}.part{part_number:03d}"
            with open(part_path, "wb") as part:
                remaining = part_size
                while remaining:
                    chunk = source.read(min(1024 * 1024, remaining))
                    if not chunk:
                        break
                    part.write(chunk)
                    remaining -= len(chunk)

            part_caption = (
                f"{caption}\n\nPart {part_number}/{total_parts}"
                if caption
                else f"Part {part_number}/{total_parts}"
            )
            try:
                kwargs = {"document": part_path, "caption": part_caption}
                if progress_for_pyrogram is not None:
                    kwargs.update(
                        progress=progress_for_pyrogram,
                        progress_args=(
                            progress_message or f"Uploading part {part_number}/{total_parts}...",
                            message,
                            time.time(),
                        ),
                    )
                await message.reply_document(**kwargs)
                sent += 1
            finally:
                try:
                    os.remove(part_path)
                except FileNotFoundError:
                    pass
    return sent
