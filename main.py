import sqlite3
import os
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ===== WEB SERVER FOR 24/7 HOSTING =====
app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot is Online and Running 24/7!"

def run():
    app_flask.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ===== CONFIGURATION =====
TOKEN = "8339268119:AAF7Kdn8kn2FlPh3QuukJhwA_pecTUCsZTc"

SUPPORT_USERNAME = "eraxayann"

CHANNELS = [
    "https://t.me/+4phcd5DiWUBkMmY1",
    "https://t.me/rajaluckera7x",
]

GIFT_CODES = {
    "FREE3": 3,
    "WELCOME3": 3,
    "BONUS3": 3,
}

# ===== DATABASE SETUP =====
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    referred_by INTEGER,
    payout_info TEXT
)
""")
cursor.execute("CREATE TABLE IF NOT EXISTS gift_used (user_id INTEGER, code TEXT)")
conn.commit()

# ================= KEYBOARD =================
def main_menu_keyboard():
    keyboard = [
        ["🎉 Gift Code", "🎁 Balance"],
        ["👫 Refer & Earn", "🚀 Withdraw"],
        ["Payout Method 🏦", "📞 Support"],
        ["💸 Earn More 💸"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================= HANDLERS =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ref_id = int(context.args[0]) if context.args and context.args[0].isdigit() else None

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (user_id, ref_id))
        if ref_id and ref_id != user_id:
            cursor.execute("UPDATE users SET balance = balance + 12 WHERE user_id=?", (ref_id,))
        conn.commit()

    keyboard = [
        [InlineKeyboardButton("Join Channel 1", url=CHANNELS[0]),
         InlineKeyboardButton("Join Channel 2", url=CHANNELS[1])],
        [InlineKeyboardButton("🔒 Claim", callback_data="claim")],
    ]
    await update.message.reply_text(
        "👑 Hey There! Welcome To Bot !!\n\n⚪️ Join Channels to Continue",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    cursor.execute("UPDATE users SET balance = balance + 2 WHERE user_id=?", (user_id,))
    conn.commit()
    await query.message.reply_text(
        "✅ Claim successful! Bonus ₹2 added.",
        reply_markup=main_menu_keyboard()
    )

# ================= SUPPORT COMMAND =================
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📞 Need help?\nContact support:\nhttps://t.me/{SUPPORT_USERNAME}"
    )

# ================= MESSAGE HANDLER =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    # UPI Submission logic
    if context.user_data.get('waiting_for') == 'upi':
        cursor.execute("UPDATE users SET payout_info=? WHERE user_id=?", (text, user_id))
        conn.commit()
        context.user_data['waiting_for'] = None
        await update.message.reply_text(
            "✅ Aapka UPI successfully submit ho gaya hai",
            reply_markup=main_menu_keyboard()
        )
        return

    # Menu Buttons logic
    if text == "🎁 Balance":
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        bal = cursor.fetchone()[0]
        await update.message.reply_text(f"💰 Your balance: ₹{bal}")

    elif text == "🚀 Withdraw":
        cursor.execute("SELECT balance, payout_info FROM users WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        if not row[1]:
            await update.message.reply_text("❌ Pehle 'Payout Method 🏦' set karein!")
        elif row[0] < 120:
            await update.message.reply_text(f"❌ Min Withdraw ₹120. Current: ₹{row[0]}")
        else:
            await update.message.reply_text("✅ Withdrawal request submitted to Admin!")

    elif text == "Payout Method 🏦":
        context.user_data['waiting_for'] = 'upi'
        await update.message.reply_text("📝 Kripya apna UPI ID bhejein:")

    elif text == "👫 Refer & Earn":
        bot_info = await context.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={user_id}"
        await update.message.reply_text(f"👥 Referral Link:\n{link}\n💸 Per refer: ₹12")

    elif text == "🎉 Gift Code":
        await update.message.reply_text("🎁 Send code as: /gift YOURCODE")

    elif text == "📞 Support":
        await update.message.reply_text(
            f"📞 Contact support:\nhttps://t.me/{SUPPORT_USERNAME}"
        )

    elif text in ["💸 Earn More 💸"]:
        await update.message.reply_text("🚧 Coming soon!")

# ================= GIFT =================
async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return

    code = context.args[0].upper()

    if code in GIFT_CODES:
        cursor.execute("SELECT * FROM gift_used WHERE user_id=? AND code=?", (user_id, code))
        if not cursor.fetchone():
            cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id=?",
                (GIFT_CODES[code], user_id)
            )
            cursor.execute("INSERT INTO gift_used VALUES (?, ?)", (user_id, code))
            conn.commit()
            await update.message.reply_text(f"✅ ₹{GIFT_CODES[code]} Added!")
        else:
            await update.message.reply_text("❌ Code already used.")
    else:
        await update.message.reply_text("❌ Invalid gift code.")

# ================= MAIN APP =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gift", gift))
    app.add_handler(CommandHandler("support", support))
    app.add_handler(CallbackQueryHandler(claim, pattern="claim"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("🤖 Bot started...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
