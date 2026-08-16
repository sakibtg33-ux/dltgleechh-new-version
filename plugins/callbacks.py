import logging

from pyrogram import Client, types

from plugins.button import youtube_dl_call_back
from plugins.config import Config
from plugins.database.database import db
from plugins.dl_button import ddl_call_back
from plugins.functions.forcesub import handle_force_subscribe
from plugins.script import Translation
from plugins.settings.settings import OpenSettings


logger = logging.getLogger(__name__)


@Client.on_callback_query()
async def button(bot, update):
    data = update.data or ""
    if data == "home":
        await update.message.edit(
            text=Translation.START_TEXT.format(update.from_user.mention),
            reply_markup=Translation.START_BUTTONS,
        )
    elif data == "help":
        await update.message.edit(text=Translation.HELP_TEXT, reply_markup=Translation.HELP_BUTTONS)
    elif data == "about":
        await update.message.edit(text=Translation.ABOUT_TEXT, reply_markup=Translation.ABOUT_BUTTONS)
    elif data == "refreshForceSub":
        await update.answer()
        if await handle_force_subscribe(bot, update.message) != 400:
            await update.message.edit(
                text=Translation.START_TEXT.format(update.from_user.mention),
                reply_markup=Translation.START_BUTTONS,
            )
    elif data == "OpenSettings":
        await update.answer()
        await OpenSettings(update.message)
    elif data == "showThumbnail":
        thumbnail = await db.get_thumbnail(update.from_user.id)
        if not thumbnail:
            await update.answer("You did not set a custom thumbnail.", show_alert=True)
        else:
            await update.answer()
            await bot.send_photo(
                update.message.chat.id,
                thumbnail,
                "Custom Thumbnail",
                reply_markup=types.InlineKeyboardMarkup(
                    [[types.InlineKeyboardButton("Delete Thumbnail", callback_data="deleteThumbnail")]]
                ),
            )
    elif data == "deleteThumbnail":
        await db.set_thumbnail(update.from_user.id, None)
        await update.answer("Custom thumbnail deleted.", show_alert=True)
        await update.message.delete()
    elif data == "setThumbnail":
        await update.message.edit(text=Translation.TEXT, reply_markup=Translation.BUTTONS)
    elif data == "triggerGenSS":
        await update.answer()
        await db.toggle_generate_ss(update.from_user.id)
        await OpenSettings(update.message)
    elif data == "triggerGenSample":
        await update.answer()
        await db.toggle_generate_sample_video(update.from_user.id)
        await OpenSettings(update.message)
    elif data == "triggerUploadMode":
        await update.answer()
        await db.toggle_upload_as_doc(update.from_user.id)
        await OpenSettings(update.message)
    elif data.startswith("cancel_download+"):
        await update.answer()
        job_path = data.split("+", 1)[1]
        import os
        import shutil
        if os.path.isdir(job_path):
            shutil.rmtree(job_path, ignore_errors=True)
            await update.message.edit("Download cancelled")
        else:
            await update.message.edit("This download is already finished.")
    elif "close" in data:
        await update.message.delete()
    elif "|" in data:
        await youtube_dl_call_back(bot, update)
    elif "=" in data:
        await ddl_call_back(bot, update)
    else:
        await update.answer()
