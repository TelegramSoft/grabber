import re

from nltk import word_tokenize
from pyrogram.enums import MessageEntityType
from pyrogram.types import User
from vk_api import VkApi, VkUpload

import settings

vk = VkApi(token=settings.VK_BOT_TOKEN)
vk_upload = VkUpload(vk)


def get_prefix(user: User):
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


def get_username(message):
    try:
        return message.from_user.username
    except AttributeError:
        return message.sender_chat.username


def vk_wall_post(group_ids=settings.VK_GROUP_IDS, message=None, streams: dict = None):
    # if attachments_dir is None:
    #     attachments_dir = []
    if streams is None:
        streams = {}
    for group_id in group_ids:
        print(f"Отправка в группу в ВК с id {group_id}")
        new_attachments_list = []
        api = vk.get_api()

        # attachments = [os.path.join(attachments_dir, file)
        #                for file in os.listdir(attachments_dir)
        #                if os.path.isfile(os.path.join(attachments_dir, file)) and (
        #                    file.endswith(".jpg") or file.endswith(".png") or file.endswith(".jpeg"))]
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

        # attachments = [os.path.join(attachments_dir, file)
        #                for file in os.listdir(attachments_dir)
        #                if os.path.isfile(os.path.join(attachments_dir, file)) and (
        #                        file.endswith(".mp4") or file.endswith(".MOV"))]
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
                owner_id=-group_id,
                from_group=1,
                message=message,
                attachments=",".join(new_attachments_list)
            )
        else:
            api.wall.post(
                owner_id=-group_id,
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

    split_words = word_tokenize(str(text), language="russian")
    return " ".join([word for word in split_words if word.lower() not in settings.STOP_WORDS])


async def stop_post_filter(pre_text):
    if not settings.STOP_POST_FILTER:
        return True
    text = re.split(fr"[{''.join(settings.SPLIT_SYMBOLS)}]", pre_text)

    for word in text:
        if word.lower() in settings.STOP_POST_WORDS:
            return False
    return True
