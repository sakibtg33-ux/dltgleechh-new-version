import logging
import random
import string
from datetime import date

import aiohttp

from plugins.config import Config
from plugins.database.database import db


logger = logging.getLogger(__name__)
TOKENS = {}
VERIFIED = {}
LOG_TEXT_P = "#NewUser\nID - <code>{}</code>\nName - {}"


async def get_verify_shorted_link(link):
    api_key = Config.SHORT_API
    domain = Config.SHORT_DOMAIN
    if not api_key or not domain:
        return link
    if link.startswith("http:"):
        link = "https:" + link[5:]
    try:
        async with aiohttp.ClientSession() as session:
            if domain == "api.shareus.in":
                url = f"https://{domain}/shortLink"
                params = {"token": api_key, "format": "json", "link": link}
                async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                    data = await response.json(content_type=None)
                    return data.get("shortlink", link) if data.get("status") == "success" else link
            url = f"https://{domain}/api"
            params = {"api": api_key, "url": link}
            async with session.get(url, params=params, raise_for_status=True, ssl=False) as response:
                data = await response.json(content_type=None)
                return data.get("shortenedUrl", link) if data.get("status") == "success" else link
    except Exception:
        logger.exception("Shortlink request failed")
        return link


async def _ensure_user(bot, user):
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id)
        if Config.LOG_CHANNEL:
            try:
                await bot.send_message(Config.LOG_CHANNEL, LOG_TEXT_P.format(user.id, user.mention))
            except Exception:
                logger.exception("Could not log new user")


async def check_token(bot, userid, token):
    user = await bot.get_users(userid)
    await _ensure_user(bot, user)
    return bool(TOKENS.get(user.id, {}).get(token) is False)


async def get_token(bot, userid, link):
    user = await bot.get_users(userid)
    await _ensure_user(bot, user)
    token = "".join(random.choices(string.ascii_letters + string.digits, k=7))
    TOKENS[user.id] = {token: False}
    return str(await get_verify_shorted_link(f"{link}verify-{user.id}-{token}"))


async def verify_user(bot, userid, token):
    user = await bot.get_users(userid)
    await _ensure_user(bot, user)
    TOKENS[user.id] = {token: True}
    VERIFIED[user.id] = date.today().isoformat()


async def check_verification(bot, userid):
    user = await bot.get_users(userid)
    await _ensure_user(bot, user)
    value = VERIFIED.get(user.id)
    if not value:
        return False
    try:
        return date.fromisoformat(value) >= date.today()
    except ValueError:
        return False
