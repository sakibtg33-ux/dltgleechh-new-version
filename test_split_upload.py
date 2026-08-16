import asyncio
import os
import tempfile
from pathlib import Path

from plugins.config import Config
from plugins.functions.split_upload import send_file_in_parts


class DummyMessage:
    def __init__(self):
        self.parts = []

    async def reply_document(self, document, caption="", **kwargs):
        with open(document, "rb") as handle:
            self.parts.append((caption, handle.read()))


async def main():
    old_limit = Config.TG_MAX_FILE_SIZE
    old_part = Config.UPLOAD_PART_SIZE
    try:
        Config.TG_MAX_FILE_SIZE = 10
        Config.UPLOAD_PART_SIZE = 10
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "sample.bin"
            payload = bytes(range(256)) * 3
            source.write_bytes(payload)
            message = DummyMessage()
            sent = await send_file_in_parts(message, str(source), "sample")
            assert sent == 77, sent
            assert b"".join(content for _, content in message.parts) == payload
            assert all("Part " in caption for caption, _ in message.parts)
            assert not list(Path(folder).glob("*.part*"))
    finally:
        Config.TG_MAX_FILE_SIZE = old_limit
        Config.UPLOAD_PART_SIZE = old_part


if __name__ == "__main__":
    asyncio.run(main())
