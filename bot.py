import os
import logging
from telegram import Update, Message
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
GROUP_ID = int(os.environ["GROUP_ID"])


def extract_user_id(text: str) -> int | None:
    """Извлекаем user_id из текста сообщения в группе"""
    for part in text.split():
        clean = part.strip("():")
        if clean.isdigit():
            # Проверяем что это именно id: часть
            if f"id:{clean}" in text or f"id: {clean}" in text:
                return int(clean)
    # Запасной вариант — ищем напрямую
    import re
    match = re.search(r"id:(\d+)", text)
    return int(match.group(1)) if match else None


async def forward_to_group(context, user, original_msg: Message):
    """Пересылаем любой тип сообщения в группу с подписью"""
    tag = f"@{user.username}" if user.username else f"{user.first_name} (id:{user.id})"
    caption_prefix = f"📩 От {tag}:\n"

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
        # Стикер — сначала текст с подписью, потом сам стикер
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
    """Пересылаем ответ из группы обратно пользователю"""
    prefix = "💬 Ответ от поддержки:\n"

    if original_msg.text:
        # Убираем первую строку (она содержит команду оператора, если есть)
        await context.bot.send_message(chat_id=user_id, text=f"{prefix}\n{original_msg.text}")

    elif original_msg.photo:
        await context.bot.send_photo(
            chat_id=user_id,
            photo=original_msg.photo[-1].file_id,
            caption=f"{prefix}{original_msg.caption or ''}"
        )

    elif original_msg.document:
        await context.bot.send_document(
            chat_id=user_id,
            document=original_msg.document.file_id,
            caption=f"{prefix}{original_msg.caption or ''}"
        )

    elif original_msg.video:
        await context.bot.send_video(
            chat_id=user_id,
            video=original_msg.video.file_id,
            caption=f"{prefix}{original_msg.caption or ''}"
        )

    elif original_msg.voice:
        await context.bot.send_voice(
            chat_id=user_id,
            voice=original_msg.voice.file_id,
            caption=f"{prefix}{original_msg.caption or ''}"
        )

    elif original_msg.audio:
        await context.bot.send_audio(
            chat_id=user_id,
            audio=original_msg.audio.file_id,
            caption=f"{prefix}{original_msg.caption or ''}"
        )

    elif original_msg.sticker:
        await context.bot.send_message(chat_id=user_id, text=prefix)
        await context.bot.send_sticker(chat_id=user_id, sticker=original_msg.sticker.file_id)

    elif original_msg.video_note:
        await context.bot.send_message(chat_id=user_id, text=prefix)
        await context.bot.send_video_note(chat_id=user_id, video_note=original_msg.video_note.file_id)


# ─── Handlers ────────────────────────────────────────────────────────────────

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Любое сообщение в личку → пересылаем в группу"""
    msg = update.message
    if not msg or msg.chat.type != "private":
        return

    await forward_to_group(context, msg.from_user, msg)
    await msg.reply_text("✅ Сообщение получено! Скоро ответим.")


async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Реплай в группе → пересылаем пользователю"""
    msg = update.message
    if not msg or msg.chat.id != GROUP_ID:
        return
    if not msg.reply_to_message:
        return

    original_text = msg.reply_to_message.text or msg.reply_to_message.caption or ""
    user_id = extract_user_id(original_text)

    if user_id:
        try:
            await forward_to_user(context, user_id, msg)
        except Exception as e:
            await msg.reply_text(f"⚠️ Не удалось отправить пользователю: {e}")
    else:
        await msg.reply_text(
            "⚠️ Не найден ID пользователя.\n"
            "Убедитесь что отвечаете реплаем на сообщение вида: 📩 От ... (id:XXXXXX)"
        )


# ─── Запуск ───────────────────────────────────────────────────────────────────

ALL_CONTENT = (
    filters.TEXT | filters.PHOTO | filters.Document.ALL |
    filters.VIDEO | filters.VOICE | filters.AUDIO |
    filters.Sticker.ALL | filters.VIDEO_NOTE
)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(ALL_CONTENT & filters.ChatType.PRIVATE, handle_user_message))
app.add_handler(MessageHandler(ALL_CONTENT & filters.ChatType.GROUP, handle_group_reply))
app.run_polling()
