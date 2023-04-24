import asyncio
import shutil
from nltk import download

from pyrogram.enums import ParseMode
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo

from utils import *
from pyrogram import Client
from pyrogram import filters

app = Client(settings.SESSION_NAME, api_id=settings.API_ID, api_hash=settings.API_HASH)
used_media_groups = []

bad_group = False
channel_media_group = None
channel_media_group_text = ""
channel_media_group_streams = {}
channel_media_group_inputs = []


async def on_channel_media_group(client: Client, message: Message):
    global channel_media_group_streams, channel_media_group_text, channel_media_group, bad_group

    username = get_username(message)
    if (settings.ONLY and username not in settings.ONLY_FROM) or username in settings.NOT_SEND_MESSAGE_FROM:
        return

    # Проверка на телефон
    if message.caption:
        if not await check_for_phone(message.caption, message.caption_entities) and settings.PHONE_FILTER:
            print("Сообщение без телефона...")
            bad_group = True
            return
        if await check_for_links(message.caption_entities):
            print("Сообщение с ссылками...")
            bad_group = True
            return
        if not await stop_post_filter(message.caption):
            print("Сообщение содержит запрещенные слова...")
            bad_group = True
            return

    # Проверяем если уже другая медиа группа, то отправляем
    if channel_media_group != message.media_group_id:
        if not bad_group:
            # Отправка в ВК
            if settings.VK_REPOST and username not in settings.VK_NOT_SEND_MESSAGES_FROM:
                vk_wall_post(message=get_vk_prefix(username) + channel_media_group_text,
                             streams=channel_media_group_streams)

            # Отправка в ТГ
            for chat in settings.GROUPS_TO_SEND:
                await asyncio.sleep(settings.BEFORE_SEND_TIMEOUT)
                print(f"Отправка в '{chat}'...")
                chat = await client.get_chat(chat)
                await client.send_media_group(chat.id, media=channel_media_group_inputs)

        await clean_cache()

    if bad_group:
        return
    channel_media_group = message.media_group_id

    # Формирование медиа группы
    for index, msg in enumerate(await message.get_media_group()):
        input_entity = None
        stream = await client.download_media(msg)
        if msg.photo:
            channel_media_group_streams[stream] = "photo"
            input_entity = InputMediaPhoto(stream)
        if msg.video:
            channel_media_group_streams[stream] = "video"
            input_entity = InputMediaVideo(stream)

        if input_entity:
            if message.caption:
                channel_media_group_text = check_for_bad_words(message.caption)
                input_entity.caption = get_prefix(message.from_user) + channel_media_group_text
                input_entity.caption_entities = message.caption_entities
            channel_media_group_inputs.append(input_entity)


async def on_media_group(client: Client, message: Message):
    username = get_username(message)
    if (settings.ONLY and username not in settings.ONLY_FROM) or username in settings.NOT_SEND_MESSAGE_FROM:
        return
    if message.media_group_id in used_media_groups:
        return
    else:
        used_media_groups.append(message.media_group_id)
    media_group = await message.get_media_group()
    print(f"Найдена новая медиа группа из {message.chat.title}...")

    # Проверка на телефон
    if not await check_for_phone(message.caption, message.caption_entities) and settings.PHONE_FILTER:
        print("Сообщение без телефона...")
        return
    if not await stop_post_filter(message.caption):
        print("Сообщение содержит запрещенные слова...")
        return
    if await check_for_links(message.entities):
        print("Сообщение содержит ссылки...")
        return

    # Переменные
    media = []
    text = ""
    streams = {}

    # Формирование медиа группы
    for index, msg in enumerate(media_group):
        input_entity = None
        stream = await client.download_media(msg)
        if msg.photo:
            streams[stream] = "photo"
            input_entity = InputMediaPhoto(stream)
        if msg.video:
            streams[stream] = "video"
            input_entity = InputMediaVideo(stream)

        if input_entity:
            if index == 0:
                text = check_for_bad_words(message.caption)
                input_entity.caption = get_prefix(message.from_user) + text
                input_entity.caption_entities = message.caption_entities
            media.append(input_entity)

    # Отправка в ВК
    if settings.VK_REPOST and username not in settings.VK_NOT_SEND_MESSAGES_FROM:
        vk_wall_post(message=get_vk_prefix(username) + text, streams=streams)

    # Отправка в ТГ
    for chat in settings.GROUPS_TO_SEND:
        await asyncio.sleep(settings.BEFORE_SEND_TIMEOUT)
        print(f"Отправка в '{chat}'...")
        chat = await client.get_chat(chat)
        await client.send_media_group(chat.id, media=media)

    await clean_cache()


async def on_message(client: Client, message: Message):
    # Инициализация нужных переменных
    text = check_for_bad_words(message.text if message.text else message.caption)
    entities = message.entities if message.entities else message.caption_entities
    username = get_username(message)
    streams = {}

    if (settings.ONLY and username not in settings.ONLY_FROM) or username in settings.NOT_SEND_MESSAGE_FROM:
        return

    # Проверка на телефон
    if not await check_for_phone(text, entities) and settings.PHONE_FILTER:
        print("Сообщение без телефона...")
        return
    if await check_for_links(entities):
        print("Сообщение содержит ссылки...")
        return
    if not await stop_post_filter(text):
        print("Сообщение содержит запрещенные слова...")
        return

    # Получение вложения как поток байтов
    stream = None
    if message.photo or message.video:
        stream = await client.download_media(message)

    # Отправка в ВК
    if settings.VK_REPOST and username not in settings.VK_NOT_SEND_MESSAGES_FROM:
        if stream:
            streams[stream] = "photo" if message.photo else "video"
        vk_wall_post(message=get_vk_prefix(username) + text, streams=streams)

    # Отправка в ТГ
    for chat in settings.GROUPS_TO_SEND:
        await asyncio.sleep(settings.BEFORE_SEND_TIMEOUT)
        print(f"Отправка в '{chat}'...")
        chat = await client.get_chat(chat)
        if message.photo:
            await client.send_photo(chat.id, photo=stream,
                                    caption=get_prefix(message.from_user) + text, caption_entities=entities,
                                    parse_mode=ParseMode.MARKDOWN)
        elif message.video:
            await client.send_video(chat.id, video=stream,
                                    caption=get_prefix(message.from_user) + text, caption_entities=entities,
                                    parse_mode=ParseMode.MARKDOWN)
        else:
            await client.send_message(chat.id, text=get_prefix(message.from_user) + text, entities=entities)

    await clean_cache()


async def clean_cache(directory="downloads"):
    global channel_media_group, channel_media_group_text, channel_media_group_streams, \
        channel_media_group_inputs, bad_group

    await asyncio.sleep(10)
    if len(used_media_groups) >= 30:
        used_media_groups.clear()
    try:
        shutil.rmtree(directory)
    except (PermissionError, FileNotFoundError):
        pass

    bad_group = False
    channel_media_group = None
    channel_media_group_text = ""
    channel_media_group_streams = {}
    channel_media_group_inputs = []


if __name__ == '__main__':
    download("punkt")
    print("Connecting...")
    app.add_handler(MessageHandler(on_media_group, filters.media_group & filters.chat(settings.GROUPS_TO_TAKE)))
    app.add_handler(MessageHandler(on_channel_media_group,
                                   filters.media_group & filters.chat(settings.CHANNELS_TO_TAKE)))
    app.add_handler(MessageHandler(on_message,
                                   ~filters.media_group & filters.chat(settings.GROUPS_TO_TAKE) | filters.chat(
                                       settings.CHANNELS_TO_TAKE)))
    app.run()
