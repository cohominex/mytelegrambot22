import json
import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import Forbidden

# ————— تنظیمات —————
BOT_TOKEN      = "7891885018:AAHDb_2S34rcafPxU2PqlvKh3va00Fk80I8"
GROUP_CHAT_ID  = -1002876847620      # آیدی گروه شما
MESSAGE_LOG    = "messages.json"     # فایل ذخیره‌سازی پیام‌ها

# ————— راه‌اندازی لاگینگ —————
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ————— توابع ذخیره/بارگذاری —————
def load_messages():
    if os.path.isfile(MESSAGE_LOG):
        with open(MESSAGE_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_messages(data):
    with open(MESSAGE_LOG, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_message(group_msg_id: int, user_id: int):
    data = load_messages()
    data.append({
        # همیشه با کلیدِ جدید ذخیره می‌کنیم
        "group_message_id": group_msg_id,
        "user_id": user_id
    })
    save_messages(data)
    logger.info(f"Logged mapping: group_msg_id={group_msg_id} → user_id={user_id}")

def find_user_by_group_msg(msg_id: int):
    for entry in load_messages():
        # بررسی هر دو کلید (موقع آپدیت فایل‌های قدیمی)
        if entry.get("group_message_id") == msg_id or entry.get("message_id") == msg_id:
            return entry["user_id"]
    return None

# ————— هندلرها —————
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! 🌟\n"
        "برای ارسال پیشنهاد یا بازخورد، لطفاً همین‌جا پیام بفرستید.\n"
        "در صورت امکان، نام محله را ذکر کنید و اگر دوست داشتید:\n"
        "– نام خود را بنویسید (اختیاری)\n"
        "– شماره تماس (اختیاری)\n\n"
        "پس از ارسال، پاسخ‌ها در همین گروه دریافت خواهند شد."
    )

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    text = update.message.text
    display_name = user.first_name or "ناشناس"
    display_user = f"@{user.username}" if user.username else f"id={user.id}"
    group_text = (
        f"📩 پیام جدید از {display_name} ({display_user}):\n\n"
        f"{text}"
    )

    # ارسال به گروه
    sent = await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=group_text)
    logger.info(f"Sent to group: message_id={sent.message_id}")

    # ذخیره نگاشت پیام گروه ← user_id
    log_message(sent.message_id, user.id)

    # پاسخ تشکر
    await update.message.reply_text("از همکاری شما بسیار ممنونیم 🌹")

async def handle_group_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if msg.chat_id != GROUP_CHAT_ID or not msg.reply_to_message:
        return

    replied_id = msg.reply_to_message.message_id
    admin_reply = msg.text
    logger.info(f"Detected reply in group: replied_id={replied_id}, admin_reply={admin_reply!r}")

    target_user_id = find_user_by_group_msg(replied_id)
    if not target_user_id:
        logger.warning(f"No mapping found for group_msg_id={replied_id}")
        await msg.reply_text("⚠️ یافتن کاربر ناموفق بود.")
        return

    try:
        await context.bot.send_message(chat_id=target_user_id, text=f"📬 پاسخ شما:\n\n{admin_reply}")
        logger.info(f"Replied to user_id={target_user_id}")
    except Forbidden:
        logger.error(f"Forbidden: cannot send to user_id={target_user_id}")
        await msg.reply_text(
            "❌ ارسال پیام به کاربر ناموفق بود. "
            "لطفاً مطمئن شوید کاربر ربات را استارت کرده یا بلاک نکرده باشد."
        )

# ————— راه‌اندازی اپ —————
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(
        MessageHandler(filters.ChatType.PRIVATE & filters.TEXT, handle_private_message)
    )
    app.add_handler(
        MessageHandler(filters.ChatType.GROUPS & filters.TEXT & filters.REPLY, handle_group_reply)
    )

    logger.info("ربات در حال اجراست...")
    app.run_polling()
