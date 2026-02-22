import sqlite3
import random
from flask import Flask
from threading import Thread
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ================== CONFIG ==================

TOKEN = "8339268119:AAF7Kdn8kn2FlPh3QuukJhwA_pecTUCsZTc"
ADMIN_ID = 7499239556
UPI_ID = "babu.440@superyes"

CHANNELS = [
    "@eraxchannal",
    "@rajaluckera7x",
    "@withrawalupi",
]

GIFT_CODES = {
    "FREE3": 3,
    "WELCOME3": 3,
    "BONUS3": 3,
}

SPIN_COST = 2
SPIN_REWARDS = [2, 4, 6, 10, 0]  # 0 = Try Again
MIN_WITHDRAW = 250
DEPOSIT_CHECK = 25

# ================== KEEP ALIVE ==================

app_flask = Flask("")

@app_flask.route("/")
def home():
    return "Bot is Online!"

def run():
    app_flask.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# ================== DATABASE ==================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    referred_by INTEGER,
    payout_info TEXT,
    joined_bonus INTEGER DEFAULT 0,
    deposit_done INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS gift_used (
    user_id INTEGER,
    code TEXT
)
""")
conn.commit()

# ================== MENU ==================

def main_menu():
    keyboard = [
        ["🎉 Gift Code", "🎁 Balance"],
        ["👫 Refer & Earn", "🎡 Spin"],
        ["🚀 Withdraw", "Payout Method 🏦"],
        ["📤 Withdrawal Proof", "🆘 Support"],
        ["📊 Stats", "📢 Broadcast"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================== FORCE JOIN CHECK ==================

async def is_joined(user_id, context):
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ================== START ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ref = int(context.args[0]) if context.args and context.args[0].isdigit() else None

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (user_id, referred_by) VALUES (?, ?)",
            (user_id, ref),
        )
        if ref and ref != user_id:
            cursor.execute(
                "UPDATE users SET balance = balance + 12 WHERE user_id=?",
                (ref,),
            )
        conn.commit()

    if not await is_joined(user_id, context):
        keyboard = [
            [
                InlineKeyboardButton("Join 1", url="https://t.me/eraxchannal"),
                InlineKeyboardButton("Join 2", url="https://t.me/rajaluckera7x"),
            ],
            [
                InlineKeyboardButton("Join 3", url="https://t.me/withrawalupi"),
            ],
            [InlineKeyboardButton("✅ Claim", callback_data="claim_join")],
        ]
        await update.message.reply_text(
            "⚠️ Pehle sabhi channels join karo",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    await update.message.reply_text(
        "👑 Welcome to Bot!",
        reply_markup=main_menu(),
    )

# ================== CLAIM JOIN BONUS ==================

async def claim_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if not await is_joined(user_id, context):
        await query.message.reply_text("❌ Pehle channels join karo")
        return

    cursor.execute(
        "SELECT joined_bonus FROM users WHERE user_id=?", (user_id,)
    )
    bonus = cursor.fetchone()[0]

    if bonus == 1:
        await query.message.reply_text(
            "❌ Join bonus already le chuke ho",
            reply_markup=main_menu(),
        )
        return

    cursor.execute(
        "UPDATE users SET balance = balance + 2, joined_bonus = 1 WHERE user_id=?",
        (user_id,),
    )
    conn.commit()

    await query.message.reply_text(
        "✅ Join bonus ₹2 mil gaya",
        reply_markup=main_menu(),
    )

# ================== MESSAGE HANDLER ==================

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    # ===== UPI submit =====
    if context.user_data.get("wait_upi"):
        cursor.execute(
            "UPDATE users SET payout_info=? WHERE user_id=?",
            (text, user_id),
        )
        conn.commit()
        context.user_data["wait_upi"] = False
        await update.message.reply_text("✅ UPI saved", reply_markup=main_menu())
        return

    # ===== withdraw amount =====
    if context.user_data.get("wait_withdraw"):
        amount = int(text)
        context.user_data["wait_withdraw"] = False

        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        bal = cursor.fetchone()[0]

        if bal < amount:
            await update.message.reply_text("❌ Insufficient balance")
            return

        cursor.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id=?",
            (amount, user_id),
        )
        conn.commit()

        await context.bot.send_message(
            ADMIN_ID,
            f"💸 Withdrawal Request\nUser: {user_id}\nAmount: ₹{amount}",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}_{amount}")
            ),
        )

        await update.message.reply_text("✅ Withdrawal submitted")
        return

    # ===== menu buttons =====
    cursor.execute("SELECT balance, payout_info, deposit_done FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    bal, upi, dep = row

    if text == "🎁 Balance":
        await update.message.reply_text(f"💰 Balance: ₹{bal}")

    elif text == "Payout Method 🏦":
        context.user_data["wait_upi"] = True
        await update.message.reply_text("📥 Apna UPI ID bhejo")

    elif text == "👫 Refer & Earn":
        bot_info = await context.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={user_id}"
        await update.message.reply_text(f"🔗 Referral:\n{link}\n💸 ₹12 per refer")

    elif text == "🎉 Gift Code":
        await update.message.reply_text("Send: /gift CODE")

    elif text == "🆘 Support":
        await update.message.reply_text("📞 Contact: @eraxayann")

    elif text == "📤 Withdrawal Proof":
        await update.message.reply_text("📢 Proof Channel:\nhttps://t.me/withrawalupi")

    elif text == "🚀 Withdraw":
        if not upi:
            await update.message.reply_text("❌ Pehle payout set karo")
        elif dep == 0:
            await update.message.reply_text(f"💳 Withdraw se pehle ₹{DEPOSIT_CHECK} deposit karo\nUPI: {UPI_ID}")
        elif bal < MIN_WITHDRAW:
            await update.message.reply_text(f"❌ Min withdraw ₹{MIN_WITHDRAW}\nBalance ₹{bal}")
        else:
            context.user_data["wait_withdraw"] = True
            await update.message.reply_text("💸 Kitna withdraw karna hai?")

    elif text == "🎡 Spin":
        if bal < SPIN_COST:
            await update.message.reply_text("❌ Spin ke liye ₹2 chahiye")
        else:
            await update.message.reply_text("🎡 Spin karne ke liye /spin_now use karo")

    elif text == "📊 Stats":
        if user_id != ADMIN_ID:
            return
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        await update.message.reply_text(f"👥 Total Users: {total}")

    elif text.startswith("/broadcast") and user_id == ADMIN_ID:
        msg = text.replace("/broadcast ","")
        cursor.execute("SELECT user_id FROM users")
        for uid in cursor.fetchall():
            try:
                await context.bot.send_message(uid[0], msg)
            except:
                continue
        await update.message.reply_text("✅ Broadcast sent")

# ================== SPIN ==================

async def spin_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]

    if bal < SPIN_COST:
        return

    bal -= SPIN_COST
    reward = random.choice(SPIN_REWARDS)
    bal += reward
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?", (bal, user_id))
    conn.commit()

    text = f"🎉 Jeete ₹{reward}" if reward > 0 else "😢 Try Again"
    await q.message.edit_text(f"{text}\n💰 Balance: ₹{bal}")

# ================== GIFT ==================

async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        return

    code = context.args[0].upper()

    if code in GIFT_CODES:
        cursor.execute(
            "SELECT * FROM gift_used WHERE user_id=? AND code=?",
            (user_id, code),
        )
        if not cursor.fetchone():
            cursor.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id=?",
                (GIFT_CODES[code], user_id),
            )
            cursor.execute("INSERT INTO gift_used VALUES (?,?)", (user_id, code))
            conn.commit()
            await update.message.reply_text(f"✅ ₹{GIFT_CODES[code]} added")

# ================== WITHDRAW APPROVE ==================

async def approve_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = int(q.data.split("_")[1])
    amount = int(q.data.split("_")[2])

    if q.from_user.id != ADMIN_ID:
        return

    await q.message.edit_text(f"✅ Withdrawal of ₹{amount} approved for User {user_id}")

# ================== MAIN ==================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gift", gift))
    app.add_handler(CallbackQueryHandler(claim_join, pattern="claim_join"))
    app.add_handler(CallbackQueryHandler(spin_now, pattern="spin_now"))
    app.add_handler(CallbackQueryHandler(approve_withdraw, pattern="approve_"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))

    print("🤖 Admin Pro Bot Running...")
    app.run_polling()

if __name__ == "__main__":
    keep_alive()
    main()
