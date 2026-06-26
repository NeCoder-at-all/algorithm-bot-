import os
import re
import logging
from telegram import Update, Message
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
GROUP_ID = int(os.environ["GROUP_ID"])


def extract_user_id(text: str) -> int | None:
    match = re.search(r"id:(\d+)", text)
    return int(match.group(1)) if match else None


async def forward_to_group(context, user, original_msg: Message):
    tag = f"@{user.username}" if user.username else f"{user.first_name} (id:{user.id})"
    # id всегда в подписи — даже если есть username, чтобы extract_user_id работал
    caption_prefix = f"{tag} (id:{user.id}):\n"

    if original_msg.text:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"{caption_prefix}\n{original_msg.text}"
        )
    elif original_msg.photo:
        await context.bot.send_photo(
            chat_id=GROUP_ID,
            photo=original_msg.photo[-1].file_id,
            caption=f"{caption_prefix}{original_msg.caption or ''}"
        )
    elif original_msg.document:
        await context.bot.send_document(
            chat_id=GROUP_ID,
            document=original_msg.document.file_id,
            caption=f"{caption_prefix}{original_msg.caption or ''}"
        )
    elif original_msg.video:
        await context.bot.send_video(
            chat_id=GROUP_ID,
            video=original_msg.video.file_id,
            caption=f"{caption_prefix}{original_msg.caption or ''}"
        )
    elif original_msg.voice:
        await context.bot.send_voice(
            chat_id=GROUP_ID,
            voice=original_msg.voice.file_id,
            caption=f"{caption_prefix}{original_msg.caption or ''}"
        )
    elif original_msg.audio:
        await context.bot.send_audio(
            chat_id=GROUP_ID,
            audio=original_msg.audio.file_id,
            caption=f"{caption_prefix}{original_msg.caption or ''}"
        )
    elif original_msg.sticker:
        await context.bot.send_message(chat_id=GROUP_ID, text=caption_prefix)
        await context.bot.send_sticker(
            chat_id=GROUP_ID,
            sticker=original_msg.sticker.file_id
        )
    elif original_msg.video_note:
        await context.bot.send_message(chat_id=GROUP_ID, text=caption_prefix)
        await context.bot.send_video_note(
            chat_id=GROUP_ID,
            video_note=original_msg.video_note.file_id
        )
    else:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"{caption_prefix}\n[Неподдерживаемый тип сообщения]"
        )


async def forward_to_user(context, user_id: int, original_msg: Message):
    if original_msg.text:
        await context.bot.send_message(chat_id=user_id, text=f"{original_msg.text}")
    elif original_msg.photo:
        await context.bot.send_photo(
            chat_id=user_id,
            photo=original_msg.photo[-1].file_id,
            caption=f"{original_msg.caption or ''}"
        )
    elif original_msg.document:
        await context.bot.send_document(
            chat_id=user_id,
            document=original_msg.document.file_id,
            caption=f"{original_msg.caption or ''}"
        )
    elif original_msg.video:
        await context.bot.send_video(
            chat_id=user_id,
            video=original_msg.video.file_id,
            caption=f"{original_msg.caption or ''}"
        )
    elif original_msg.voice:
        await context.bot.send_voice(
            chat_id=user_id,
            voice=original_msg.voice.file_id,
            caption=f"{original_msg.caption or ''}"
        )
    elif original_msg.audio:
        await context.bot.send_audio(
            chat_id=user_id,
            audio=original_msg.audio.file_id,
            caption=f"{original_msg.caption or ''}"
        )
    elif original_msg.sticker:
        await context.bot.send_message(chat_id=user_id, text=prefix)
        await context.bot.send_sticker(chat_id=user_id, sticker=original_msg.sticker.file_id)
    elif original_msg.video_note:
        await context.bot.send_message(chat_id=user_id, text=prefix)
        await context.bot.send_video_note(chat_id=user_id, video_note=original_msg.video_note.file_id)


# ─── Handlers ────────────────────────────────────────────────────────────────

async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отвечаем на /start — в группу НЕ пересылаем"""
    await update.message.reply_text(
        "👋 Здравствуйте! Напишите ваш вопрос и мы ответим в ближайшее время."
    )


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.chat.type != "private":
        return

    await forward_to_group(context, msg.from_user, msg)


async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or msg.chat.id != GROUP_ID:
        return
    if not msg.reply_to_message:
        return
    if msg.reply_to_message.from_user.id != context.bot.id:
        return
    if msg.quote:
        return
        
    original_text = msg.reply_to_message.text
    user_id = extract_user_id(original_text)

    if user_id:
        try:
            await forward_to_user(context, user_id, msg)
        except Exception as e:
            await msg.reply_text(f"Не хочу {e}")
    else:
        await msg.reply_text(
            "Че?"
        )


# ─── Запуск ───────────────────────────────────────────────────────────────────

ALL_CONTENT = (
    filters.TEXT | filters.PHOTO | filters.Document.ALL |
    filters.VIDEO | filters.VOICE | filters.AUDIO |
    filters.Sticker.ALL | filters.VIDEO_NOTE
)

app = ApplicationBuilder().token(BOT_TOKEN).build()

# /start — отдельный handler, не попадает в handle_user_message
app.add_handler(CommandHandler("start", handle_start))

# Сообщения от пользователей в личке (всё кроме команд)
app.add_handler(MessageHandler(
    ALL_CONTENT & filters.ChatType.PRIVATE & ~filters.COMMAND,
    handle_user_message
))

# Реплаи в группе
app.add_handler(MessageHandler(
    ALL_CONTENT & filters.ChatType.SUPERGROUP,
    handle_group_reply
))

app.run_polling()
