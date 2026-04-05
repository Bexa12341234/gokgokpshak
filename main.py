import json
import logging
import os
import asyncio
from typing import List, Dict, Optional

# ================= TELEGRAM =================
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= SOZLAMALAR =================
TOKEN = "8314708801:AAEdB8NTdHajl_uDeGZAffc_DCn9ebHpb3E"
OWNER_USERNAME = "Bexa12341234"
OWNER_ID: Optional[int] = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "replies.json")
AUTO_DELETE = 10

# ================= LOG =================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= FILE =================
def load_replies() -> List[Dict]:
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return []

def save_replies(data: List[Dict]):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

REPLIES = load_replies()

# ================= HELPERS =================
def is_owner(update: Update) -> bool:
    u = update.effective_user
    if not u: return False
    if OWNER_ID and u.id == OWNER_ID: return True
    if u.username and u.username.lower() == OWNER_USERNAME.lower(): return True
    return False

async def delete_later(bot, chat_id, ids, delay=AUTO_DELETE):
    await asyncio.sleep(delay)
    for mid in ids:
        try:
            await bot.delete_message(chat_id, mid)
        except:
            pass

# ================= MENU =================
def reply_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Qo‘shish", callback_data="add")],
        [InlineKeyboardButton("❌ O‘chirish", callback_data="delete")],
        [InlineKeyboardButton("📋 Ro‘yxat", callback_data="list")],
        [InlineKeyboardButton("🚪 Yopish", callback_data="close")],
    ])

ADD = "add"
DEL = "del"

# ================= COMMANDS =================
async def reply_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update): return
    user_msg = update.message
    bot_msg = await user_msg.reply_text("🔧 Reply boshqaruvi", reply_markup=reply_menu_keyboard())
    asyncio.create_task(delete_later(context.bot, bot_msg.chat_id, [user_msg.message_id, bot_msg.message_id]))

# ================= BUTTON HANDLER =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ids = [q.message.message_id]

    if q.data == "add":
        context.user_data[ADD] = {"step": "trigger"}
        await q.edit_message_text("Trigger yuboring (masalan: salom)")
    elif q.data == "delete":
        context.user_data[DEL] = True
        text = "🗑 O‘chirish uchun tartib raqamini yuboring:\n"
        for i, r in enumerate(REPLIES):
            text += f"{i+1}. {r['trigger']}\n"
        await q.edit_message_text(text)
    elif q.data == "list":
        text = "📋 Mavjud replylar:\n"
        for i, r in enumerate(REPLIES):
            text += f"{i+1}. {r['trigger']}\n"
        await q.edit_message_text(text)
    elif q.data == "close":
        await q.message.delete()

# ================= TEXT HANDLER =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text: return

    # --- .send FUNKSIYASI ---
    if msg.text.startswith(".send "):
        content = msg.text[6:].strip() # ".send " dan keyingi qism
        if content:
            await context.bot.send_message(chat_id=msg.chat_id, text=content)
            try:
                await msg.delete() # Foydalanuvchi xabarini o'chirish
            except:
                pass
            return

    # --- DELETE MODE ---
    if context.user_data.get(DEL) and is_owner(update):
        if msg.text.isdigit():
            idx = int(msg.text) - 1
            if 0 <= idx < len(REPLIES):
                REPLIES.pop(idx)
                save_replies(REPLIES)
                bot_m = await msg.reply_text("✅ O‘chirildi")
                context.user_data.pop(DEL, None)
                asyncio.create_task(delete_later(context.bot, msg.chat_id, [msg.message_id, bot_m.message_id]))
        return

    # --- ADD MODE ---
    add_data = context.user_data.get(ADD)
    if add_data and is_owner(update):
        if add_data["step"] == "trigger":
            add_data["trigger"] = msg.text
            add_data["step"] = "response"
            bot_m = await msg.reply_text("Endi javob matni yoki rasmini yuboring")
            return
        
        if add_data["step"] == "response":
            entry = {"trigger": add_data["trigger"]}
            if msg.photo:
                entry.update({"type": "photo", "file_id": msg.photo[-1].file_id, "caption": msg.caption or ""})
            else:
                entry.update({"type": "text", "response": msg.text})
            
            REPLIES.append(entry)
            save_replies(REPLIES)
            context.user_data.pop(ADD, None)
            bot_m = await msg.reply_text("✅ Saqlandi")
            asyncio.create_task(delete_later(context.bot, msg.chat_id, [msg.message_id, bot_m.message_id]))
            return

    # --- AUTO REPLY ---
    text_lower = msg.text.lower()
    for r in REPLIES:
        if r["trigger"].lower() == text_lower:
            if r["type"] == "photo":
                await msg.reply_photo(r["file_id"], caption=r.get("caption", ""))
            else:
                await msg.reply_text(r["response"])
            break

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("reply", reply_menu))
    app.add_handler(CallbackQueryHandler(button_handler))
    # TEXT va PHOTO larni filtrlaymiz
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO) & ~filters.COMMAND, handle_text))
    
    print("✅ Bot ishlamoqda...")
    app.run_polling()

if __name__ == "__main__":
    main()
