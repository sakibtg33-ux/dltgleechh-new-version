# (c) @AbirHasan2005

import datetime
import motor.motor_asyncio
from plugins.config import Config


class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users

    def new_user(self, id):
        return dict(
            id=id,
            join_date=datetime.date.today().isoformat(),
            apply_caption=True,
            upload_as_doc=False,
            thumbnail=None,
            caption=None,
            generate_ss=False,
            generate_sample_video=False
        )

    async def add_user(self, id):
        user = self.new_user(id)
        await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id': int(id)})
        return bool(user)

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    async def set_apply_caption(self, id, apply_caption):
        await self.col.update_one({'id': id}, {'$set': {'apply_caption': apply_caption}})

    async def get_apply_caption(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('apply_caption', True)

    async def set_upload_as_doc(self, id, upload_as_doc):
        await self.col.update_one({'id': id}, {'$set': {'upload_as_doc': upload_as_doc}})

    async def get_upload_as_doc(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('upload_as_doc', False)

    async def set_thumbnail(self, id, thumbnail):
        await self.col.update_one({'id': id}, {'$set': {'thumbnail': thumbnail}})

    async def get_thumbnail(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('thumbnail', None)

    async def set_caption(self, id, caption):
        await self.col.update_one({'id': id}, {'$set': {'caption': caption}})

    async def get_caption(self, id):
        user = await self.col.find_one({'id': int(id)})
        return user.get('caption', None)

    async def toggle_upload_as_doc(self, id):
        current = await self.get_upload_as_doc(id)
        await self.set_upload_as_doc(id, not current)
        return not current

    async def get_generate_ss(self, id):
        user = await self.col.find_one({'id': int(id)})
        return bool(user.get('generate_ss', False)) if user else False

    async def set_generate_ss(self, id, value):
        await self.col.update_one({'id': int(id)}, {'$set': {'generate_ss': bool(value)}})

    async def toggle_generate_ss(self, id):
        value = not await self.get_generate_ss(id)
        await self.set_generate_ss(id, value)
        return value

    async def get_generate_sample_video(self, id):
        user = await self.col.find_one({'id': int(id)})
        return bool(user.get('generate_sample_video', False)) if user else False

    async def set_generate_sample_video(self, id, value):
        await self.col.update_one({'id': int(id)}, {'$set': {'generate_sample_video': bool(value)}})

    async def toggle_generate_sample_video(self, id):
        value = not await self.get_generate_sample_video(id)
        await self.set_generate_sample_video(id, value)
        return value

    async def get_user_data(self, id) -> dict:
        user = await self.col.find_one({'id': int(id)})
        return user or None


db = Database(Config.DATABASE_URL, "UploadLinkToFileBot")
