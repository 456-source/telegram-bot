import os
import threading
from dotenv import load_dotenv
import telebot
from telebot.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputMediaPhoto,
    InputMediaVideo
)

# ---------- ENV ----------
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")

if not TOKEN or not GROUP_ID:
    raise ValueError("❌ BOT_TOKEN или GROUP_ID не найден в .env")

GROUP_ID = int(GROUP_ID)
bot = telebot.TeleBot(TOKEN)

# ---------- ХРАНИЛИЩА ----------
albums = {}   # media_group_id -> data
album_timers = {}

# ---------- КНОПКИ ----------
def main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("📸 отправить фото / 🎥 видео"))
    kb.add(
        KeyboardButton("💸 реклама"),
        KeyboardButton("❌ удалить пост")
    )
    return kb


START_TEXT = (
    "👋Привет!👋\n\n"
    "🤖Этот бот создан для добавления постов в ТГК:\n"
    "⬇️⬇️⬇️\n"
    "@Cringe_YoshkarOla\n"
    "@Cringe_YoshkarOla\n"
    "@Cringe_YoshkarOla\n"
    "⬆️⬆️⬆️\n\n"
    "🎭Все фото и текст отправляются анонимно.\n\n"
    "✅Перед публикацией контент проверяется.\n\n"
    "❌Вы можете удалить пост за звезды.\n\n"
    "💸Здесь вы можете узнать информацию о рекламе."
)

# ---------- ВСПОМОГАТЕЛЬНОЕ ----------
def get_author(message):
    user = message.from_user
    name = user.first_name or "Без имени"
    username = f"@{user.username}" if user.username else "без username"
    return f"\n\n👤 Отправитель: {name} ({username}) | ID: {user.id}"

# ---------- START ----------
@bot.message_handler(commands=["start"])
def start(message):
    user = message.from_user

    bot.send_message(
        message.chat.id,
        START_TEXT,
        reply_markup=main_keyboard()
    )

    bot.send_message(
        GROUP_ID,
        "🆕 Новый пользователь бота\n\n"
        f"👤 Имя: {user.first_name or '—'}\n"
        f"🔗 Username: @{user.username}\n" if user.username else "🔗 Username: отсутствует\n"
        f"🆔 ID: {user.id}"
    )

# ---------- РЕКЛАМА ----------
@bot.message_handler(func=lambda m: m.text == "💸 реклама")
def advertisement(message):
    bot.send_message(
        message.chat.id,
        "💸 реклама\n\n"
        "Вы обратились в пункт \"💸 реклама\". "
        "Мы можем опубликовать ваш рекламный пост на определенный промежуток времени, "
        "выложить ваш рекламный текст в комментариях на определенный промежуток времени, "
        "либо же, если у вас есть телеграм-канал на тематику Йошкар-Олы, "
        "мы можем обсудить взаимный пиар "
        "(выкладывать в телеграм-каналах рекламные посты друг друга).\n\n"
        "По всем подробностям и ценам пишите нашему модератору.\n\n"
        "Пишите модератору: @CringeModerator"
    )

# ---------- УДАЛЕНИЕ ----------
@bot.message_handler(func=lambda m: m.text == "❌ удалить пост")
def delete_post(message):
    bot.send_message(
        message.chat.id,
        "❌ удалить пост\n\n"
        "Вы обратились в пункт \"❌ удалить пост\". "
        "Вы можете удалить любой пост (не рекламный) за определенную сумму звезд. "
        "Сумма зависит от поста, уточняйте ее у нашего модератора.\n\n"
        "Пишите модератору: @CringeModerator"
    )

# ---------- НАЧАЛО ПУБЛИКАЦИИ ----------
@bot.message_handler(func=lambda m: m.text == "📸 отправить фото / 🎥 видео")
def publish_start(message):
    bot.send_message(
        message.chat.id,
        "✅ Вы обратились в публикацию постов!\n"
        "📩 Отправьте фото/видео и текст (по желанию)"
    )

# ---------- МЕДИА ----------
@bot.message_handler(content_types=["photo", "video"])
def handle_media(message):
    if not message.media_group_id:
        send_single_media(message)
        return

    mgid = message.media_group_id

    if mgid not in albums:
        albums[mgid] = {
            "chat_id": message.chat.id,
            "media": [],
            "caption": None,
            "author": get_author(message)
        }

    data = albums[mgid]

    if message.photo:
        data["media"].append(
            InputMediaPhoto(message.photo[-1].file_id)
        )
    elif message.video:
        data["media"].append(
            InputMediaVideo(message.video.file_id)
        )

    if message.caption:
        data["caption"] = message.caption

    if mgid in album_timers:
        album_timers[mgid].cancel()

    timer = threading.Timer(0.8, send_album, args=[mgid])
    album_timers[mgid] = timer
    timer.start()

# ---------- ТЕКСТ ПОСЛЕ МЕДИА ----------
@bot.message_handler(content_types=["text"])
def handle_text(message):
    for data in albums.values():
        if data["chat_id"] == message.chat.id:
            data["caption"] = message.text
            return

# ---------- ОТПРАВКА АЛЬБОМА ----------
def send_album(mgid):
    data = albums.pop(mgid, None)
    album_timers.pop(mgid, None)

    if not data:
        return

    media = data["media"]
    caption = (data["caption"] or "") + data["author"]
    media[0].caption = caption

    bot.send_media_group(GROUP_ID, media)
    bot.send_message(data["chat_id"], "✅ Пост отправлен на проверку")

# ---------- ОДИНОЧНОЕ МЕДИА ----------
def send_single_media(message):
    caption = (message.caption or "") + get_author(message)

    if message.photo:
        bot.send_photo(
            GROUP_ID,
            message.photo[-1].file_id,
            caption=caption
        )
    elif message.video:
        bot.send_video(
            GROUP_ID,
            message.video.file_id,
            caption=caption
        )

    bot.send_message(message.chat.id, "✅ Пост отправлен на проверку")

# ---------- RUN ----------
print("✅ Бот запущен")
bot.infinity_polling()
