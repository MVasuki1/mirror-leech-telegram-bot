#!/usr/bin/env python3
from asyncio import sleep
from pyrogram.errors import FloodWait
from time import time
from re import match as re_match

from bot import config_dict, LOGGER, status_reply_dict, status_reply_dict_lock, Interval, bot, user, download_dict_lock
from bot.helper.ext_utils.bot_utils import get_readable_message, setInterval, sync_to_async


async def sendMessage(message, text, buttons=None):
    try:
        return await message.reply(text=text, quote=True, disable_web_page_preview=True,
                                   disable_notification=True, reply_markup=buttons)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendMessage(message, text, buttons)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def editMessage(message, text, buttons=None):
    try:
        await message.edit(text=text, disable_web_page_preview=True, reply_markup=buttons)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await editMessage(message, text, buttons)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def sendFile(message, file, caption=None):
    try:
        return await message.reply_document(document=file, quote=True, caption=caption, disable_notification=True)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendFile(message, file, caption)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def sendRss(text, url=None):
    LOGGER.info(text)
    try:
        if user:
            return await user.send_message(chat_id=config_dict['RSS_CHAT_ID'], text=text, disable_web_page_preview=True, disable_notification=True)
            #if url:
            #    return await user.send_message(chat_id=config_dict['RSS_CHAT_LOG'], text=url, disable_web_page_preview=True, disable_notification=True)
        else:
            return await bot.send_message(chat_id=config_dict['RSS_CHAT_ID'], text=text, disable_web_page_preview=True, disable_notification=True)
            #if url:
            #    return await bot.send_message(chat_id=config_dict['RSS_CHAT_LOG'], text=url, disable_web_page_preview=True, disable_notification=True)
    except FloodWait as f:
        LOGGER.warning(str(f))
        await sleep(f.value * 1.2)
        return await sendRss(text)
    except Exception as e:
        LOGGER.error(str(e))
        return str(e)


async def deleteMessage(message):
    try:
        await message.delete()
    except Exception as e:
        LOGGER.error(str(e))


async def auto_delete_message(cmd_message=None, bot_message=None):
    if config_dict['AUTO_DELETE_MESSAGE_DURATION'] != -1:
        await sleep(config_dict['AUTO_DELETE_MESSAGE_DURATION'])
        if cmd_message is not None:
            await deleteMessage(cmd_message)
        if bot_message is not None:
            await deleteMessage(bot_message)


async def delete_all_messages():
    async with status_reply_dict_lock:
        for key, data in list(status_reply_dict.items()):
            try:
                del status_reply_dict[key]
                await deleteMessage(data[0])
            except Exception as e:
                LOGGER.error(str(e))


async def get_tg_link_content(link):
    if link.startswith('https://t.me/'):
        private = False
        msg = re_match(r"https:\/\/t\.me\/(?:c\/)?([^\/]+)\/([0-9]+)", link)
    else:
        private = True
        msg = re_match(
            r"tg:\/\/openmessage\?user_id=([0-9]+)&message_id=([0-9]+)", link)

    chat = msg.group(1)
    msg_id = int(msg.group(2))
    if chat.isdigit():
        chat = int(chat) if private else int(f'-100{chat}')
        superChat = True
    else:
        superChat = False
    if private:
        if not user:
            raise Exception('USER_SESSION_STRING required for this private link!')
        if message := await user.get_messages(chat_id=chat, message_ids=msg_id) and message.from_user:
            return message, True
        else:
            raise Exception("You Don't have access to this message!")
    elif superChat and (message := await bot.get_messages(chat_id=chat, message_ids=msg_id)):
        return message, False
    elif user and (message := await user.get_messages(chat_id=chat, message_ids=msg_id)):
        message = await user.get_messages(chat_id=chat, message_ids=msg_id)
        return message, True
    else:
        raise Exception("You Don't have access to this message!")


async def update_all_messages(force=False):
    async with status_reply_dict_lock:
        if not status_reply_dict or not Interval or (not force and time() - list(status_reply_dict.values())[0][1] < 3):
            return
        for chat_id in list(status_reply_dict.keys()):
            status_reply_dict[chat_id][1] = time()
    async with download_dict_lock:
        msg, buttons = await sync_to_async(get_readable_message)
    if msg is None:
        return
    async with status_reply_dict_lock:
        for chat_id in list(status_reply_dict.keys()):
            if status_reply_dict[chat_id] and msg != status_reply_dict[chat_id][0].text:
                rmsg = await editMessage(status_reply_dict[chat_id][0], msg, buttons)
                if isinstance(rmsg, str) and rmsg.startswith('Telegram says: [400'):
                    del status_reply_dict[chat_id]
                    continue
                status_reply_dict[chat_id][0].text = msg
                status_reply_dict[chat_id][1] = time()


async def sendStatusMessage(msg):
    async with download_dict_lock:
        progress, buttons = await sync_to_async(get_readable_message)
    if progress is None:
        return
    async with status_reply_dict_lock:
        chat_id = msg.chat.id
        if chat_id in list(status_reply_dict.keys()):
            message = status_reply_dict[chat_id][0]
            await deleteMessage(message)
            del status_reply_dict[chat_id]
        message = await sendMessage(msg, progress, buttons)
        message.text = progress
        status_reply_dict[chat_id] = [message, time()]
        if not Interval:
            Interval.append(setInterval(
                config_dict['STATUS_UPDATE_INTERVAL'], update_all_messages))
