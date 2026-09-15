from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import ChatAdminRequired, UserNotParticipant, ChatWriteForbidden
from pyrogram.enums import ParseMode  # ✅ Use Enum instead of raw string
from VILLAIN_MUSIC import app

MUST_JOIN = "iamvillain77"  # Username or chat ID

@app.on_message(filters.incoming & filters.private, group=-1)
async def must_join_channel(app: Client, msg: Message):
    if not MUST_JOIN:
        return

    try:
        try:
            await app.get_chat_member(MUST_JOIN, msg.from_user.id)

        except UserNotParticipant:
            if str(MUST_JOIN).startswith("@") or str(MUST_JOIN).isalpha():
                link = f"https://t.me/{MUST_JOIN.lstrip('@')}"
            else:
                chat_info = await app.get_chat(MUST_JOIN)
                link = chat_info.invite_link

            try:
                await msg.reply_photo(
                    photo="https://files.catbox.moe/67ta52.jpg",
                    caption=(
                        "❖ <b>According to my database</b>, <b>you haven’t joined</b> "
"<b><a href='https://t.me/iamvillain77'>our support channel</a></b> <b>yet.</b>\n"
"➥ <b>If you want to use me, please join</b> "
"<b><a href='https://t.me/odsnetwork'>our support group</a></b> <b>and start me again.</b>"
                        
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [InlineKeyboardButton("📢 Join Updates", url="https://t.me/iamvillain77")],
                            [InlineKeyboardButton("💬 Join Support", url=link)]
                        ]
                    ),
                    parse_mode=ParseMode.HTML  # ✅ Correct way in Pyrogram v2+
                )
                await msg.stop_propagation()

            except ChatWriteForbidden:
                pass

    except ChatAdminRequired:
        print(f"❖ Promote me as an admin in the MUST_JOIN chat: {MUST_JOIN}")
        
