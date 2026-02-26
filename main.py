import sqlite3
from datetime import datetime, timedelta

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters, CallbackQueryHandler
)

# ================= CONFIG =================

TOKEN = "8339268119:AAF7Kdn8kn2FlPh3QuukJhwA_pecTUCsZTc"
ADMIN_ID = 7499239556

FORCE_CHANNELS = [
    "@withrawalupi",
    "@rajaluckera7x",
    "@eraxchannal"
]

MIN_WITHDRAW = 250
DEPOSIT_REQUIRED = 25
DAILY_BONUS = 3

# ================= DATABASE =================

conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    deposited INTEGER DEFAULT 0,
    last_bonus TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS gift_codes(
    code TEXT PRIMARY KEY,
    amount INTEGER,
    max_use INTEGER,
    used INTEGER DEFAULT 0,
    expiry TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS gift_used(
    user_id INTEGER,
    code TEXT
)
""")

conn.commit()

# ================= FORCE JOIN =================

async def is_joined(user_id, bot):
    for ch in FORCE_CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

def join_keyboard():
    buttons = [[InlineKeyboardButton(f"Join {i+1}", url=f"https://t.me/{ch[1:]}")] for i, ch in enumerate(FORCE_CHANNELS)]
    buttons.append([InlineKeyboardButton("✅ Check Join", callback_data="check_join")])
    return InlineKeyboardMarkup(buttons)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()

    if not await is_joined(user_id, context.bot):
        await update.message.reply_text(
            "🚫 Pehle sab channels join karo:",
            reply_markup=join_keyboard()
        )
        return

    await update.message.reply_text(
        "🎉 Welcome!\n\n"
        "💰 /balance\n"
        "🎁 /daily\n"
        "🎁 /gift CODE\n"
        "💸 /withdraw\n"
        "📥 /deposit"
    )

# ================= CHECK JOIN =================

async def check_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if await is_joined(user_id, context.bot):
        await query.message.edit_text("✅ Joined! Type /start")
    else:
        await query.answer("❌ Abhi join nahi kiya", show_alert=True)

# ================= BALANCE =================

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    bal = cursor.fetchone()[0]
    await update.message.reply_text(f"💰 Balance: ₹{bal}")

# ================= DAILY BONUS =================

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("SELECT last_bonus FROM users WHERE user_id=?", (user_id,))
    last = cursor.fetchone()[0]

    now = datetime.now()

    if last:
        last_time = datetime.fromisoformat(last)
        if now - last_time < timedelta(hours=24):
            await update.message.reply_text("⏳ Daily already claimed")
            return

    cursor.execute(
        "UPDATE users SET balance = balance + ?, last_bonus=? WHERE user_id=?",
        (DAILY_BONUS, now.isoformat(), user_id)
    )
    conn.commit()

    await update.message.reply_text(f"✅ ₹{DAILY_BONUS} daily bonus added")

# ================= GIFT =================

async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Use: /gift CODE")
        return

    code = context.args[0].upper()

    cursor.execute("SELECT amount,max_use,used,expiry FROM gift_codes WHERE code=?", (code,))
    data = cursor.fetchone()

    if not data:
        await update.message.reply_text("❌ Invalid code")
        return

    amount, max_use, used, expiry = data

    if expiry and datetime.now() > datetime.fromisoformat(expiry):
        await update.message.reply_text("⌛ Code expired")
        return

    if used >= max_use:
        await update.message.reply_text("❌ Code finished")
        return

    cursor.execute("SELECT 1 FROM gift_used WHERE user_id=? AND code=?", (user_id, code))
    if cursor.fetchone():
        await update.message.reply_text("❌ Already used")
        return

    cursor.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
    cursor.execute("INSERT INTO gift_used VALUES(?,?)", (user_id, code))
    cursor.execute("UPDATE gift_codes SET used=used+1 WHERE code=?", (code,))
    conn.commit()

    await update.message.reply_text(f"✅ ₹{amount} added!")

# ================= WITHDRAW =================

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("SELECT balance,deposited FROM users WHERE user_id=?", (user_id,))
    bal, dep = cursor.fetchone()

    if dep < DEPOSIT_REQUIRED:
        await update.message.reply_text("❌ Withdrawal se pehle ₹25 deposit karo")
        return

    if bal < MIN_WITHDRAW:
        await update.message.reply_text("❌ Aapka amount kam hai (Min ₹250)")
        return

    context.user_data["withdraw"] = True
    await update.message.reply_text("💸 UPI ID bhejo")

# ================= DEPOSIT =================

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["deposit"] = True
    await update.message.reply_text("📥 Payment screenshot bhejo")

# ================= HANDLE MSG =================

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    admin = user_id == ADMIN_ID

    # withdraw UPI
    if context.user_data.get("withdraw"):
        upi = update.message.text
        context.user_data["withdraw"] = False

        btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"wa_{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"wr_{user_id}")
        ]])

        await context.bot.send_message(
            ADMIN_ID,
            f"💸 Withdraw Request\nUser: {user_id}\nUPI: {upi}",
            reply_markup=btn
        )
        await update.message.reply_text("⏳ Withdrawal request sent")
        return

    # deposit screenshot
    if context.user_data.get("deposit"):
        context.user_data["deposit"] = False

        btn = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Approve", callback_data=f"da_{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"dr_{user_id}")
        ]])

        await context.bot.send_message(
            ADMIN_ID,
            f"📥 Deposit Request\nUser: {user_id}",
            reply_markup=btn
        )
        await update.message.reply_text("⏳ Deposit request sent")
        return

# ================= ADMIN ACTION =================

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if query.from_user.id != ADMIN_ID:
        return

    user_id = int(data.split("_")[1])

    # deposit approve
    if data.startswith("da_"):
        cursor.execute("UPDATE users SET deposited=25 WHERE user_id=?", (user_id,))
        conn.commit()
        await context.bot.send_message(user_id, "✅ Deposit approved")
        await query.message.edit_text("Done")

    # withdraw approve
    if data.startswith("wa_"):
        cursor.execute("UPDATE users SET balance=0 WHERE user_id=?", (user_id,))
        conn.commit()
        await context.bot.send_message(user_id, "✅ Withdrawal approved")
        await query.message.edit_text("Done")

# ================= RUN =================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("balance", balance))
app.add_handler(CommandHandler("daily", daily))
app.add_handler(CommandHandler("gift", gift))
app.add_handler(CommandHandler("withdraw", withdraw))
app.add_handler(CommandHandler("deposit", deposit))

app.add_handler(CallbackQueryHandler(check_join, pattern="check_join"))
app.add_handler(CallbackQueryHandler(admin_action))

app.add_handler(MessageHandler(filters.ALL, handle_msg))

print("✅ Bot running...")
app.run_polling()
