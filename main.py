import asyncio

import settings
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, InputMediaVideo, Message

from utils import get_username, check_for_phone, check_for_links, stop_post_filter, vk_wall_post, get_vk_prefix, \
    get_prefix

app = Client(settings.SESSION_NAME, settings.API_ID, settings.API_HASH)
used_media_groups = []


async def forward_media(client: Client, message: Message):
    await asyncio.sleep(settings.BEFORE_SEND_TIMEOUT)

    username = get_username(message)
    streams = {}
    try:
        print(f"Новое сообщение из {message.chat.title}...")
    except AttributeError:
        print(f"Новое сообщение...")

    # Получение текста сообщения и entity
    if message.media_group_id:
        mg = await message.get_media_group()
        text = mg[0].caption
        entities = mg[0].caption_entities
    elif message.video or message.photo:
        text = message.caption
        entities = message.caption_entities
    else:
        text = message.text
        entities = message.entities

    # Проверки и фильтры
    if (settings.ONLY and username not in settings.ONLY_FROM) or username in settings.NOT_SEND_MESSAGE_FROM:
        return
    # Проверка на телефон
    if not await check_for_phone(text, entities) and settings.PHONE_FILTER:
        print("Сообщение без телефона...")
        return
    # Проверка на ссылки
    if await check_for_links(entities):
        print("Сообщение содержит ссылки...")
        return
    # Проверка на запрешенные слова
    if not await stop_post_filter(text):
        print("Сообщение содержит запрещенные слова...")
        return

    # Определяем медиа в сообщении и отправка в ТГ
    if message.media_group_id:
        # Это медиа группа
        media_group = await client.get_media_group(message.chat.id, message.id)
        media_list = []
        for media in media_group:
            stream = await client.download_media(media)
            if media.photo:
                # Это фото
                if media.caption:
                    photo = InputMediaPhoto(media.photo.file_id, caption=get_prefix(message.from_user) + media.caption)
                else:
                    photo = InputMediaPhoto(media.photo.file_id, caption=media.caption)
                media_list.append(photo)
                streams[stream] = "photo"
            elif media.video:
                # Это видео
                if media.caption:
                    video = InputMediaVideo(media.video.file_id, caption=get_prefix(message.from_user) + media.caption)
                else:
                    video = InputMediaVideo(media.video.file_id, caption=media.caption)
                media_list.append(video)
                streams[stream] = "video"
        for chat in settings.GROUPS_TO_SEND:
            print(f"Отправка в {chat}")
            await client.send_media_group(chat_id=chat, media=media_list)
    elif message.photo:
        # Это фото
        for chat in settings.GROUPS_TO_SEND:
            print(f"Отправка в {chat}")
            if message.caption:
                await client.send_photo(chat_id=chat, photo=message.photo.file_id,
                                        caption=get_prefix(message.from_user) + message.caption)
            else:
                await client.send_photo(chat_id=chat, photo=message.photo.file_id,
                                        caption=message.caption)
        streams[await client.download_media(message)] = "photo"
    elif message.video:
        # Это видео
        for chat in settings.GROUPS_TO_SEND:
            print(f"Отправка в {chat}")
            if message.caption:
                await client.send_video(chat_id=chat, video=message.video.file_id,
                                        caption=get_prefix(message.from_user) + message.caption)
            else:
                await client.send_video(chat_id=chat, video=message.video.file_id, caption=message.caption)
        streams[await client.download_media(message)] = "video"
    else:
        # Это текстовое сообщение без медиа
        for chat in settings.GROUPS_TO_SEND:
            print(f"Отправка в {chat}")
            await client.send_message(chat_id=chat, text=get_prefix(message.from_user) + message.text)

    # Отправка в ВК
    if settings.VK_REPOST and username not in settings.VK_NOT_SEND_MESSAGES_FROM:
        if text:
            vk_wall_post(message=get_vk_prefix(username) + text, streams=streams)
        else:
            vk_wall_post(message=get_vk_prefix(username), streams=streams)


@app.on_message(filters.chat(settings.GROUPS_TO_TAKE))
async def media_handler(client, message):
    global used_media_groups

    if message.media_group_id:
        if message.media_group_id in used_media_groups:
            return
        used_media_groups.append(message.media_group_id)

    await forward_media(client, message)


def main():
    app.run()


if __name__ == '__main__':
    main()
