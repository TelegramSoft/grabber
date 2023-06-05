import re
from typing import List
from pyrogram.enums import MessageEntityType
from pyrogram.types import User, Message
from vk_api import VkApi, VkUpload

import settings

vk = VkApi(token=settings.VK_BOT_TOKEN)
vk_upload = VkUpload(vk)


async def get_prefix(user: User, entities: List, with_filter: bool):
    if not with_filter:
        return generate_prefix_from_user(user)

    if not entities:
        return ""
    for entity in entities:
        if entity.type == MessageEntityType.TEXT_MENTION:
            return generate_prefix_from_user(entity.user)


def generate_prefix_from_user(user: User):
    if not user:
        return ""
    prefix = f"[{user.first_name}"
    if user.last_name:
        prefix += " " + user.last_name
    return prefix + f"](tg://user?id={user.id})\n"


def get_vk_prefix(username):
    if settings.VK_PREFIX:
        return f"{settings.VK_PREFIX} https://t.me/{username}\n"
    return settings.TELEGRAM_GROUP_TITLE


async def get_username(message: Message, entities: List, with_filter):
    if with_filter and entities:
        for entity in entities:
            if entity.type == MessageEntityType.TEXT_MENTION:
                return entity.user.username if entity.user.username else ""
    try:
        return message.from_user.username
    except AttributeError:
        return message.sender_chat.username


def vk_wall_post(group_ids=settings.VK_GROUP_IDS, message=None, streams: dict = None):
    if streams is None:
        streams = {}
    api = vk.get_api()

    for group_id in group_ids:
        print(f"Отправка в группу в ВК с id {group_id}")
        new_attachments_list = []

        attachments = [stream
                       for stream, stream_type in streams.items()
                       if stream_type == "photo"]
        if attachments:
            uploaded = vk_upload.photo_wall(
                photos=attachments,
                group_id=group_id,
            )
            for upload in uploaded:
                new_attachments_list.append(f"photo{upload['owner_id']}_{upload['id']}")

        attachments = [stream
                       for stream, stream_type in streams.items()
                       if stream_type == "video"]
        if attachments:
            for attach in attachments:
                uploaded = vk_upload.video(
                    video_file=attach,
                    group_id=group_id,
                )
                new_attachments_list.append(f"video{uploaded['owner_id']}_{uploaded['video_id']}")

        if new_attachments_list:
            api.wall.post(
                owner_id=-int(group_id),
                from_group=1,
                message=message,
                attachments=",".join(new_attachments_list)
            )
        else:
            api.wall.post(
                owner_id=-int(group_id),
                from_group=1,
                message=message
            )


async def check_for_phone(text, entities):
    if entities:
        for entity in entities:
            if entity == MessageEntityType.PHONE_NUMBER:
                return True
    else:
        if not text:
            return False
    for num in settings.PHONES:
        for plus_str in settings.PLUS_STR:
            if plus_str + str(num) in text:
                return True
    return False


async def check_for_links(entities):
    if not settings.LINK_FILTER:
        return False
    if entities:
        for entity in entities:
            if entity.type == MessageEntityType.URL or entity.type == MessageEntityType.TEXT_LINK:
                return True
    return False


def check_for_bad_words(text) -> str:
    if not settings.STOP_WORDS_FILTER:
        return text

    # Удаляем указанные слова из текста сообщения
    new_text = re.sub(r"\b(?:{})\b".format("|".join(settings.STOP_WORDS)), '', text, flags=re.IGNORECASE)

    return new_text


async def stop_post_filter(pre_text):
    if not settings.STOP_POST_FILTER:
        return True
    text = re.split(fr"[{''.join(settings.SPLIT_SYMBOLS)}]", pre_text)

    for word in text:
        if word.lower() in settings.STOP_POST_WORDS:
            return False
    return True


async def remove_links(text: str, entities: List):
    if not settings.REMOVE_LINKS or not entities:
        return text

    # Удаляем ссылки из текста сообщения
    for entity in entities:
        if entity.type == MessageEntityType.TEXT_LINK:
            # Проверяем наличие ссылки в белом списке
            if entity.url in settings.LINKS_WHITELIST:
                continue
        elif entity.type == MessageEntityType.URL:
            # Получаем ссылку и проверяем есть ли она в белом списке
            link = text[entity.offset:][:entity.offset + entity.length].strip()
            if link in settings.LINKS_WHITELIST:
                continue
        else:
            continue

        # Вырезаем ссылки
        text = text[:entity.offset] + text[entity.offset + entity.length:]

    return text


async def check_language(text):
    has_arabic = bool(re.search(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]", text))
    has_ukrainian = bool(re.search(r"[\u0404\u0407\u0406\u0490\u0454\u0457\u0456\u0491]", text))

    return not has_ukrainian or has_arabic
