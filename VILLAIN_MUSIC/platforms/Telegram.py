import asyncio
import os
import time
from typing import Union

from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Voice

import config
from VILLAIN_MUSIC import app
from VILLAIN_MUSIC.utils.formatters import (
    check_duration,
    convert_bytes,
    get_readable_time,
    seconds_to_min,
)


class TeleAPI:
    def __init__(self):
        self.chars_limit = 4096
        self.sleep = 5

    async def send_split_text(self, message, string):
        n = self.chars_limit
        out = [(string[i : i + n]) for i in range(0, len(string), n)]
        j = 0
        for x in out:
            if j <= 2:
                j += 1
                await message.reply_text(x, disable_web_page_preview=True)
        return True

    async def get_link(self, message):
        return message.link

    async def get_filename(self, file, audio: Union[bool, str] = None):
        try:
            file_name = file.file_name
            if file_name is None:
                file_name = "ᴛᴇʟᴇɢʀᴀᴍ ᴀᴜᴅɪᴏ" if audio else "ᴛᴇʟᴇɢʀᴀᴍ ᴠɪᴅᴇᴏ"
        except:
            file_name = "ᴛᴇʟᴇɢʀᴀᴍ ᴀᴜᴅɪᴏ" if audio else "ᴛᴇʟᴇɢʀᴀᴍ ᴠɪᴅᴇᴏ"
        return file_name

    async def get_duration(self, file):
        try:
            dur = seconds_to_min(file.duration)
        except:
            dur = "Unknown"
        return dur

    async def get_duration(self, filex, file_path):
        try:
            dur = seconds_to_min(filex.duration)
        except:
            try:
                dur = await asyncio.get_event_loop().run_in_executor(
                    None, check_duration, file_path
                )
                dur = seconds_to_min(dur)
            except:
                return "Unknown"
        return dur

    async def get_filepath(
        self,
        audio: Union[bool, str] = None,
        video: Union[bool, str] = None,
    ):
        if audio:
            try:
                file_name = (
                    audio.file_unique_id
                    + "."
                    + (
                        (audio.file_name.split(".")[-1])
                        if (not isinstance(audio, Voice))
                        else "ogg"
                    )
                )
            except:
                file_name = audio.file_unique_id + "." + "ogg"
            file_name = os.path.join(os.path.realpath("downloads"), file_name)
        if video:
            try:
                file_name = (
                    video.file_unique_id + "." + (video.file_name.split(".")[-1])
                )
            except:
                file_name = video.file_unique_id + "." + "mp4"
            file_name = os.path.join(os.path.realpath("downloads"), file_name)
        return file_name

    async def download(self, _, message, mystic, fname):
        lower = [0, 8, 17, 38, 64, 77, 96]
        higher = [5, 10, 20, 40, 66, 80, 99]
        checker = [5, 10, 20, 40, 66, 80, 99]
        speed_counter = {}

        # Never trust an old/partial file. Telegram downloads are written to a
        # temporary file and atomically renamed only after the complete file is
        # verified. A per-file lock also prevents two gplay requests from
        # downloading the same Telegram file at the same time.
        if not hasattr(self, "_download_locks"):
            self._download_locks = {}

        lock = self._download_locks.setdefault(fname, asyncio.Lock())
        async with lock:
            reply = message.reply_to_message
            media = None
            if reply:
                media = reply.audio or reply.voice or reply.video or reply.document

            expected_size = getattr(media, "file_size", None) if media else None

            def valid_file(path):
                try:
                    size = os.path.getsize(path)
                    if size <= 0:
                        return False
                    if expected_size and size != int(expected_size):
                        return False
                    return True
                except Exception:
                    return False

            # Existing complete file is safe to reuse.
            if os.path.isfile(fname) and valid_file(fname):
                return True

            # Remove stale/partial final and temporary files before starting.
            for path in (fname, fname + ".part"):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass

            async def down_load():
                async def progress(current, total):
                    if current == total or not total:
                        return
                    current_time = time.time()
                    start_time = speed_counter.get(message.id, current_time)
                    check_time = max(current_time - start_time, 0.001)
                    upl = InlineKeyboardMarkup(
                        [[InlineKeyboardButton(
                            text="ᴄᴀɴᴄᴇʟ",
                            callback_data="stop_downloading",
                        )]]
                    )
                    percentage = current * 100 / total
                    percentage = str(round(percentage, 2))
                    speed = current / check_time
                    eta = int((total - current) / max(speed, 1))
                    eta = get_readable_time(eta)
                    if not eta:
                        eta = "0 sᴇᴄᴏɴᴅs"
                    total_size = convert_bytes(total)
                    completed_size = convert_bytes(current)
                    speed = convert_bytes(speed)
                    percentage = int(percentage.split(".")[0])
                    for counter in range(7):
                        low = int(lower[counter])
                        high = int(higher[counter])
                        check = int(checker[counter])
                        if low < percentage <= high and high == check:
                            try:
                                await mystic.edit_text(
                                    text=_["tg_1"].format(
                                        app.mention,
                                        total_size,
                                        completed_size,
                                        percentage,
                                        speed,
                                        eta,
                                    ),
                                    reply_markup=upl,
                                )
                                checker[counter] = 100
                            except Exception:
                                pass

                speed_counter[message.id] = time.time()
                temp_path = fname + ".part"
                last_error = None

                for attempt in range(1, 4):
                    try:
                        try:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                        except Exception:
                            pass

                        await app.download_media(
                            reply,
                            file_name=temp_path,
                            progress=progress,
                        )

                        if not valid_file(temp_path):
                            raise IOError("incomplete Telegram download")

                        os.replace(temp_path, fname)

                        try:
                            elapsed = get_readable_time(
                                int(time.time() - speed_counter[message.id])
                            )
                        except Exception:
                            elapsed = "0 sᴇᴄᴏɴᴅs"
                        try:
                            await mystic.edit_text(_["tg_2"].format(elapsed))
                        except Exception:
                            pass
                        return True
                    except Exception as exc:
                        last_error = exc
                        try:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                        except Exception:
                            pass
                        if attempt < 3:
                            await asyncio.sleep(attempt)

                try:
                    await mystic.edit_text(_["tg_3"])
                except Exception:
                    pass
                return False

            try:
                result = await down_load()
            finally:
                self._download_locks.pop(fname, None)

            return bool(result)

