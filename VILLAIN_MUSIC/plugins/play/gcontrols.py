import re

from pyrogram import filters
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.types import Message
from pytgcalls.exceptions import NoActiveGroupCall

import config
from strings import get_string
from VILLAIN_MUSIC import Apple, Resso, SoundCloud, Spotify, Telegram, YouTube, app
from VILLAIN_MUSIC.core.call import Aviax
from VILLAIN_MUSIC.utils import time_to_seconds
from VILLAIN_MUSIC.utils.formatters import formats
from VILLAIN_MUSIC.utils.database import get_lang, group_assistant
from VILLAIN_MUSIC.utils.gconnect_db import (
    get_gconnection,
    remove_gconnection,
    save_gconnection,
)
from VILLAIN_MUSIC.utils.logger import play_logs
from VILLAIN_MUSIC.utils.stream.stream import stream
from config import BANNED_USERS

SORRY_URL = (
    "❖ sᴏʀʀʏ ɪ ᴄᴀɴ'ᴛ ᴘʟᴀʏ ᴛʜɪꜱ 🙂\n\n"
    "» ᴍᴀʏʙᴇ ɪᴛ'ꜱ ᴅᴀɴɢᴇʀᴏᴜs ᴜʀʟ."
)

def is_safe_url(url):
    if not url or not isinstance(url, str):
        return True

    url_lower = url.lower()

    command_injection_patterns = [
        r';\s*curl', r';\s*wget', r';\s*bash', r';\s*sh\s', r';\s*cat\s',
        r';\s*rm\s', r';\s*chmod', r';\s*python', r';\s*perl', r';\s*node',
        r'\|\s*curl', r'\|\s*wget', r'\|\s*bash', r'&&\s*curl', r'&&\s*wget',
        r'\$\{IFS\}', r'\$IFS', r'`curl', r'`wget', r'`cat', r'\$\(curl',
        r'\$\(wget', r'\$\(cat', r'@\.env', r'\.env\s', r'\.config\s',
        r'/etc/passwd', r'/etc/shadow', r'file=@', r'-F\s+file', r'-X\s+POST',
        r'javascript:', r'<script', r'eval\(', r'exec\(', r'system\(',
        r'shell_exec', r'file://', r'%00', r'%0a', r'%0d',
    ]
    for pattern in command_injection_patterns:
        if re.search(pattern, url_lower, re.IGNORECASE):
            return False

    if url.count(';') > 0 or url.count('|') > 1:
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            url_parts = url.split('?', 1)
            if len(url_parts) > 1:
                params = url_parts[1]
                if ';' in params or '|' in params:
                    suspicious_after = (
                        params.split(';')[1] if ';' in params else params.split('|')[1]
                    )
                    if any(
                        cmd in suspicious_after.lower()
                        for cmd in ['curl', 'wget', 'bash', 'cat', 'env', 'file']
                    ):
                        return False
        else:
            return False

    allowed_domains = [
        'youtube.com', 'youtu.be', 'spotify.com', 'apple.com',
        'music.apple.com', 'soundcloud.com', 'resso.com',
    ]
    if url.startswith('http://') or url.startswith('https://'):
        domain_match = re.search(r'https?://(?:www\.)?([^/?\s]+)', url)
        if domain_match:
            domain = domain_match.group(1).lower()
            is_allowed = any(allowed in domain for allowed in allowed_domains)
            if not is_allowed and not url.startswith('https://t.me/'):
                return False

    return True


def sanitize_query(query):
    if not query or not isinstance(query, str):
        return query
    query = query.strip()
    dangerous_patterns = [
        r';\s*curl', r';\s*wget', r';\s*bash', r'\|\s*curl', r'\$\{IFS\}', r'\.env',
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return None
    return query

async def is_chat_admin(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
    except Exception:
        return False
    return member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER)


def is_owner_or_sudo(user_id):
    ids = set()
    for attr in ("OWNER_ID", "SUDOERS", "SUDO_USERS"):
        val = getattr(config, attr, None)
        if not val:
            continue
        if isinstance(val, (list, set, tuple)):
            for x in val:
                try:
                    ids.add(int(x))
                except (TypeError, ValueError):
                    pass
        else:
            try:
                ids.add(int(val))
            except (TypeError, ValueError):
                pass
    return user_id in ids


async def ensure_assistant_joined(client, chat_id):
    try:
        pytgcalls_assistant = await group_assistant(Aviax, chat_id)
    except Exception:
        return False, (
            "❖ ᴄᴏᴜʟᴅɴ'ᴛ ᴅᴇᴛᴇʀᴍɪɴᴇ ᴀ ᴠᴄ ᴀssɪsᴛᴀɴᴛ ғᴏʀ ᴛʜᴀᴛ ɢʀᴏᴜᴘ."
        )

    pytgcalls_to_client = {
        id(getattr(Aviax, "one", None)): getattr(Aviax, "userbot1", None),
        id(getattr(Aviax, "two", None)): getattr(Aviax, "userbot2", None),
        id(getattr(Aviax, "three", None)): getattr(Aviax, "userbot3", None),
        id(getattr(Aviax, "four", None)): getattr(Aviax, "userbot4", None),
        id(getattr(Aviax, "five", None)): getattr(Aviax, "userbot5", None),
    }
    assistant = pytgcalls_to_client.get(id(pytgcalls_assistant))
    if assistant is None:
        return False, (
            "❖ ᴄᴏᴜʟᴅɴ'ᴛ ʀᴇsᴏʟᴠᴇ ᴛʜᴇ ᴀssɪsᴛᴀɴᴛ'ꜱ ᴜsᴇʀʙᴏᴛ ᴄʟɪᴇɴᴛ."
        )

    try:
        await assistant.get_chat_member(chat_id, "me")
        return True, None
    except Exception:
        pass

    try:
        invite_link = await client.export_chat_invite_link(chat_id)
    except Exception:
        return False, (
            "❖ ᴛʜᴇ ᴠᴄ ᴀssɪsᴛᴀɴᴛ ɪsɴ'ᴛ ɪɴ ᴛʜᴀᴛ ɢʀᴏᴜᴘ ᴀɴᴅ ɪ ᴄᴏᴜʟᴅɴ'ᴛ ɢᴇɴᴇʀᴀᴛᴇ ᴀɴ ɪɴᴠɪᴛᴇ ʟɪɴᴋ.\n"
            "» ᴍᴀᴋᴇ sᴜʀᴇ ᴛʜᴇ ʙᴏᴛ ɪs ᴀᴅᴍɪɴ ᴡɪᴛʜ ɪɴᴠɪᴛᴇ ᴘᴇʀᴍɪssɪᴏɴs, ᴏʀ ᴀᴅᴅ ᴛʜᴇ ᴀssɪsᴛᴀɴᴛ ᴍᴀɴᴜᴀʟʟʏ."
        )

    try:
        await assistant.join_chat(invite_link)
        return True, None
    except Exception as e:
        return False, (
            "❖ ᴄᴏᴜʟᴅɴ'ᴛ ᴀᴜᴛᴏ-ᴊᴏɪɴ ᴛʜᴇ ᴠᴄ ᴀssɪsᴛᴀɴᴛ ɪɴᴛᴏ ᴛʜᴀᴛ ɢʀᴏᴜᴘ.\n"
            f"» ᴇʀʀᴏʀ: `{type(e).__name__}`\n"
            "» ᴘʟᴇᴀsᴇ ᴀᴅᴅ ᴛʜᴇ ᴀssɪsᴛᴀɴᴛ ᴛᴏ ᴛʜᴀᴛ ɢʀᴏᴜᴘ ᴍᴀɴᴜᴀʟʟʏ."
        )


@app.on_message(
    filters.command(["gconnect"], prefixes=["/", "!", ".", ""])
    & filters.group
    & ~BANNED_USERS
)
async def gconnect_command(client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not (is_owner_or_sudo(user_id) or await is_chat_admin(client, chat_id, user_id)):
        return await message.reply_text(
            "❖ ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ."
        )

    args = message.text.split(None, 1)

    if len(args) == 1:
        current = await get_gconnection(chat_id)
        if current:
            return await message.reply_text(
                "❖ ᴛʜɪs ᴄʜᴀᴛ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ\n"
                f"`{current}`\n\n"
                "» /gconnect <chat_id> — ᴄʜᴀɴɢᴇ ᴛʜᴇ ᴄᴏɴɴᴇᴄᴛɪᴏɴ\n"
                "» /gdisconnect — ʀᴇᴍᴏᴠᴇ ᴛʜᴇ ᴄᴏɴɴᴇᴄᴛɪᴏɴ"
            )
        return await message.reply_text(
            "❖ ʜᴏᴡ ᴛᴏ sᴇᴛ ᴜᴘ /gplay\n\n"
            "» ʀᴜɴ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ ɪɴ ᴛʜᴇ ɢʀᴏᴜᴘ ᴡʜᴇʀᴇ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ sᴇɴᴅ ᴄᴏᴍᴍᴀɴᴅs ғʀᴏᴍ.\n"
            "» /gconnect <second_chat_id> ʟɪɴᴋs ᴛʜɪs ᴄʜᴀᴛ ᴛᴏ ᴛʜᴇ ɢʀᴏᴜᴘ ᴡʜᴏsᴇ ᴠᴄ ᴡɪʟʟ ᴀᴄᴛᴜᴀʟʟʏ ᴘʟᴀʏ ᴛʜᴇ sᴏɴɢs.\n"
            "» ᴛʜᴇ ᴄᴏɴɴᴇᴄᴛɪᴏɴ ɪs sᴀᴠᴇᴅ ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ — ᴄᴏɴɴᴇᴄᴛ ᴏɴᴄᴇ, ᴜsᴇ ғᴏʀᴇᴠᴇʀ.\n\n"
            "➻ ᴇxᴀᴍᴘʟᴇ: `/gconnect -1001234567890`"
        )

    try:
        second_chat_id = int(args[1].strip())
    except ValueError:
        return await message.reply_text(
            "❖ ɪɴᴠᴀʟɪᴅ ᴄʜᴀᴛ ɪᴅ.\n\n"
            "» ɪᴛ ᴍᴜsᴛ ʙᴇ ɴᴜᴍᴇʀɪᴄ, ʟɪᴋᴇ `-1001234567890`."
        )

    if second_chat_id == chat_id:
        return await message.reply_text("❖ ʏᴏᴜ ᴄᴀɴ'ᴛ ᴄᴏɴɴᴇᴄᴛ ᴀ ᴄʜᴀᴛ ᴛᴏ ɪᴛsᴇʟғ.")

    try:
        target_chat = await client.get_chat(second_chat_id)
    except Exception:
        return await message.reply_text(
            "❖ ɪ ᴄᴏᴜʟᴅɴ'ᴛ ғɪɴᴅ ᴛʜᴀᴛ ᴄʜᴀᴛ.\n\n"
            "» ᴍᴀᴋᴇ sᴜʀᴇ ᴛʜᴇ ʙᴏᴛ (ᴀɴᴅ ɪᴛs ᴀssɪsᴛᴀɴᴛ) ᴀʀᴇ ᴀʟʀᴇᴀᴅʏ ᴍᴇᴍʙᴇʀs ᴏғ ᴛʜᴀᴛ ɢʀᴏᴜᴘ."
        )

    if target_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return await message.reply_text(
            "❖ ᴛʜᴇ ᴛᴀʀɢᴇᴛ ᴄʜᴀᴛ ᴍᴜsᴛ ʙᴇ ᴀ ɢʀᴏᴜᴘ ᴏʀ sᴜᴘᴇʀɢʀᴏᴜᴘ."
        )

    try:
        await client.get_chat_member(second_chat_id, "me")
    except Exception:
        return await message.reply_text(
            "❖ ɪ'ᴍ ɴᴏᴛ ᴀ ᴍᴇᴍʙᴇʀ ᴏғ ᴛʜᴀᴛ ɢʀᴏᴜᴘ.\n\n"
            "» ᴀᴅᴅ ᴍᴇ (ᴀɴᴅ ᴛʜᴇ ᴠᴄ ᴀssɪsᴛᴀɴᴛ) ᴛʜᴇʀᴇ ғɪʀsᴛ, ᴛʜᴇɴ ᴛʀʏ ᴀɢᴀɪɴ."
        )

    await save_gconnection(chat_id, second_chat_id)
    target_title = target_chat.title or str(second_chat_id)

    join_ok, join_warning = await ensure_assistant_joined(client, second_chat_id)

    reply = (
        "❖ ɢʀᴏᴜᴘs ᴄᴏɴɴᴇᴄᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ ✅\n\n"
        f"» ᴄᴏᴍᴍᴀɴᴅ ᴄʜᴀᴛ: `{chat_id}`\n"
        f"» ᴠᴄ ᴘʟᴀʏʙᴀᴄᴋ ᴄʜᴀᴛ: {target_title} (`{second_chat_id}`)\n\n"
        "» ɴᴏᴡ ᴜsᴇ /gplay <song / url> ʜᴇʀᴇ ᴛᴏ ᴘʟᴀʏ ᴍᴜsɪᴄ ɪɴ ᴛʜᴇ ᴄᴏɴɴᴇᴄᴛᴇᴅ ɢʀᴏᴜᴘ'ꜱ ᴠᴄ.\n"
        "» sᴀᴠᴇᴅ ᴘᴇʀᴍᴀɴᴇɴᴛʟʏ — ʏᴏᴜ ᴡᴏɴ'ᴛ ɴᴇᴇᴅ ᴛᴏ ᴄᴏɴɴᴇᴄᴛ ᴀɢᴀɪɴ."
    )
    if join_warning:
        reply += f"\n\n⚠️ {join_warning}"

    await message.reply_text(reply)


@app.on_message(
    filters.command(["gdisconnect"], prefixes=["/", "!", ".", ""])
    & filters.group
    & ~BANNED_USERS
)
async def gdisconnect_command(client, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not (is_owner_or_sudo(user_id) or await is_chat_admin(client, chat_id, user_id)):
        return await message.reply_text(
            "❖ ᴏɴʟʏ ɢʀᴏᴜᴘ ᴀᴅᴍɪɴs ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴄᴏᴍᴍᴀɴᴅ."
        )

    removed = await remove_gconnection(chat_id)
    if removed:
        return await message.reply_text("❖ ᴄᴏɴɴᴇᴄᴛɪᴏɴ ʀᴇᴍᴏᴠᴇᴅ ✅")
    return await message.reply_text("❖ ᴛʜɪs ᴄʜᴀᴛ ɪsɴ'ᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ ᴀɴʏᴛʜɪɴɢ ʏᴇᴛ.")


@app.on_message(
    filters.command(["gplay", "gvplay"], prefixes=["/", "!", ".", ""])
    & filters.group
    & ~BANNED_USERS
)
async def gplay_command(client, message: Message):
    first_chat_id = message.chat.id
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    chat_id = await get_gconnection(first_chat_id)
    if not chat_id:
        return await message.reply_text(
            "❖ ᴛʜɪs ᴄʜᴀᴛ ɪsɴ'ᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ ʏᴇᴛ.\n\n"
            "» ʀᴜɴ /gconnect <second_chat_id> ʜᴇʀᴇ ғɪʀsᴛ, ᴛʜᴇɴ ᴛʀʏ /gplay ᴀɢᴀɪɴ."
        )

    join_ok, join_warning = await ensure_assistant_joined(client, chat_id)
    if not join_ok:
        return await message.reply_text(join_warning)

    language = await get_lang(first_chat_id)
    _ = get_string(language)

    mystic = await message.reply_text("❖ sᴇᴀʀᴄʜɪɴɢ...")

    video = True if message.command[0].lower() == "gvplay" else None
    spotify = None
    streamtype = None
    details = None
    result = None

    command_name = message.command[0].lower()
    audio_telegram = None
    video_telegram = None

    reply = message.reply_to_message
    if reply and command_name == "gplay":
        audio_telegram = reply.audio or reply.voice
        if not audio_telegram and reply.document:
            file_name = (reply.document.file_name or "").lower()
            mime_type = (reply.document.mime_type or "").lower()
            audio_exts = {
                "mp3", "m4a", "aac", "flac", "wav", "ogg", "oga",
                "opus", "mka", "amr", "wma", "aiff", "alac"
            }
            ext = file_name.rsplit(".", 1)[-1] if "." in file_name else ""
            if mime_type.startswith("audio/") or ext in audio_exts:
                audio_telegram = reply.document

    elif reply and command_name == "gvplay":
        video_telegram = reply.video
        if not video_telegram and reply.document:
            file_name = (reply.document.file_name or "").lower()
            mime_type = (reply.document.mime_type or "").lower()
            ext = file_name.rsplit(".", 1)[-1] if "." in file_name else ""
            video_exts = {str(item).lower().lstrip(".") for item in formats}
            if mime_type.startswith("video/") or ext in video_exts:
                video_telegram = reply.document

    url = None
    query = None
    if len(message.command) > 1:
        raw = message.text.split(None, 1)[1]
        if re.match(r"^(https?://|www\.)", raw.strip(), re.IGNORECASE):
            url = raw.strip()
        else:
            query = raw

    if url and not is_safe_url(url):
        return await mystic.edit_text(SORRY_URL)

    try:
        if audio_telegram and command_name == "gplay":
            if audio_telegram.file_size > 2147483648:
                return await mystic.edit_text(
                    "❖ ғɪʟᴇ ɪs ᴛᴏᴏ ʙɪɢ (ᴍᴀx 2ɢʙ)."
                )
            if audio_telegram.duration > config.DURATION_LIMIT:
                return await mystic.edit_text(
                    f"❖ ᴅᴜʀᴀᴛɪᴏɴ ʟɪᴍɪᴛ ɪs {config.DURATION_LIMIT_MIN} ᴍɪɴᴜᴛᴇs."
                )
            file_path = await Telegram.get_filepath(audio=audio_telegram)
            if not await Telegram.download(_, message, mystic, file_path):
                return
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(audio_telegram, audio=True)
            dur = await Telegram.get_duration(audio_telegram, file_path)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }
            streamtype = "telegram"

        elif video_telegram and command_name == "gvplay":
            if message.reply_to_message.document:
                try:
                    ext = video_telegram.file_name.split(".")[-1]
                    if ext.lower() not in formats:
                        return await mystic.edit_text(
                            f"❖ ᴜɴsᴜᴘᴘᴏʀᴛᴇᴅ ғɪʟᴇ ᴛʏᴘᴇ.\n\n"
                            f"» sᴜᴘᴘᴏʀᴛᴇᴅ: {' | '.join(formats)}"
                        )
                except Exception:
                    return await mystic.edit_text(
                        f"❖ ᴜɴsᴜᴘᴘᴏʀᴛᴇᴅ ғɪʟᴇ ᴛʏᴘᴇ.\n\n"
                        f"» sᴜᴘᴘᴏʀᴛᴇᴅ: {' | '.join(formats)}"
                    )
            if video_telegram.file_size > 2147483648:
                return await mystic.edit_text(
                    "❖ ᴠɪᴅᴇᴏ ғɪʟᴇ ɪs ᴛᴏᴏ ʙɪɢ (ᴍᴀx 2ɢʙ)."
                )
            file_path = await Telegram.get_filepath(video=video_telegram)
            if not await Telegram.download(_, message, mystic, file_path):
                return
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(video_telegram)
            dur = await Telegram.get_duration(video_telegram, file_path)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }
            streamtype = "telegram"
            video = True

        elif url:
            if await YouTube.exists(url):
                if "playlist" in url:
                    result = await YouTube.playlist(
                        url, config.PLAYLIST_FETCH_LIMIT, user_id
                    )
                    streamtype = "playlist"
                elif "https://youtu.be" in url:
                    videoid = url.split("/")[-1].split("?")[0]
                    details, _tid = await YouTube.track(
                        f"https://www.youtube.com/watch?v={videoid}"
                    )
                    streamtype = "youtube"
                else:
                    details, _tid = await YouTube.track(url)
                    streamtype = "youtube"

            elif await Spotify.valid(url):
                spotify = True
                if not config.SPOTIFY_CLIENT_ID and not config.SPOTIFY_CLIENT_SECRET:
                    return await mystic.edit_text(
                        "❖ sᴘᴏᴛɪғʏ ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ ʏᴇᴛ."
                    )
                if "track" in url:
                    details, _tid = await Spotify.track(url)
                    streamtype = "youtube"
                elif "playlist" in url:
                    result, _pid = await Spotify.playlist(url)
                    streamtype = "playlist"
                elif "album" in url:
                    result, _pid = await Spotify.album(url)
                    streamtype = "playlist"
                elif "artist" in url:
                    result, _pid = await Spotify.artist(url)
                    streamtype = "playlist"
                else:
                    return await mystic.edit_text("❖ ᴜɴsᴜᴘᴘᴏʀᴛᴇᴅ sᴘᴏᴛɪғʏ ʟɪɴᴋ.")

            elif await Apple.valid(url):
                if "album" in url:
                    details, _tid = await Apple.track(url)
                    streamtype = "youtube"
                elif "playlist" in url:
                    spotify = True
                    result, _pid = await Apple.playlist(url)
                    streamtype = "playlist"
                else:
                    return await mystic.edit_text("❖ ᴜɴsᴜᴘᴘᴏʀᴛᴇᴅ ᴀᴘᴘʟᴇ ᴍᴜsɪᴄ ʟɪɴᴋ.")

            elif await Resso.valid(url):
                details, _tid = await Resso.track(url)
                streamtype = "youtube"

            elif await SoundCloud.valid(url):
                details, _path = await SoundCloud.download(url)
                if details["duration_sec"] > config.DURATION_LIMIT:
                    return await mystic.edit_text(
                        f"❖ ᴅᴜʀᴀᴛɪᴏɴ ʟɪᴍɪᴛ ɪs {config.DURATION_LIMIT_MIN} ᴍɪɴᴜᴛᴇs."
                    )
                streamtype = "soundcloud"

            else:
                return await mystic.edit_text(SORRY_URL)

        else:
            if not query:
                return await mystic.edit_text(
                    "❖ ɢɪᴠᴇ ᴍᴇ ᴀ sᴏɴɢ ɴᴀᴍᴇ ᴏʀ ʟɪɴᴋ.\n\n"
                    "➻ ᴇxᴀᴍᴘʟᴇ: `/gplay faded alan walker`"
                )
            sanitized = sanitize_query(query)
            if sanitized is None:
                return await mystic.edit_text(SORRY_URL)
            query = sanitized
            if "-v" in query:
                query = query.replace("-v", "").strip()
                video = True
            details, _tid = await YouTube.track(query)
            streamtype = "youtube"

        if details and streamtype in ("youtube",):
            if details.get("duration_min"):
                duration_sec = time_to_seconds(details["duration_min"])
                if duration_sec > config.DURATION_LIMIT:
                    return await mystic.edit_text(
                        f"❖ ᴅᴜʀᴀᴛɪᴏɴ ʟɪᴍɪᴛ ɪs {config.DURATION_LIMIT_MIN} ᴍɪɴᴜᴛᴇs."
                    )
            else:
                return await mystic.edit_text(
                    "❖ ʟɪᴠᴇsᴛʀᴇᴀᴍs ᴀʀᴇɴ'ᴛ sᴜᴘᴘᴏʀᴛᴇᴅ ᴡɪᴛʜ /gplay ʏᴇᴛ."
                )

        payload = result if streamtype == "playlist" else details

        await stream(
            _,
            mystic,
            user_id,
            payload,
            chat_id,
            user_name,
            first_chat_id,
            video=video,
            streamtype=streamtype,
            spotify=spotify,
            forceplay=None,
        )

    except NoActiveGroupCall:
        return await mystic.edit_text(
            "❖ sᴛᴀʀᴛ ᴀ ᴠɪᴅᴇᴏ ᴄʜᴀᴛ ɪɴ ᴛʜᴇ ᴄᴏɴɴᴇᴄᴛᴇᴅ ɢʀᴏᴜᴘ ғɪʀsᴛ."
        )
    except Exception as e:
        ex_type = type(e).__name__
        err = e if ex_type == "AssistantErr" else f"❖ ᴇʀʀᴏʀ: `{ex_type}`"
        return await mystic.edit_text(str(err))

    await mystic.delete()
    return await play_logs(message, streamtype=f"GPlay : {streamtype}")
