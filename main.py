import sqlite3
import random
import asyncio
from datetime import date
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

# ================= CONFIG =================
TOKEN = "8339268119:AAF7Kdn8kn2FlPh3QuukJhwA_pecTUCsZTc"
ADMIN_ID = 7499239556
UPI_ID = "babu.440@superyes"

CHANNELS = ["@eraxchannal", "@rajaluckera7x", "@withrawalupi"]

SPIN_COST = 2
SPIN_REWARDS = [2,4,6,10,0]  # 0 = Try Again
MIN_WITHDRAW = 250
DEPOSIT_CHECK = 25
DAILY_BONUS = 3

GIFT_CODES = {
    "FREE3": 3, "WELCOME3": 3, "BONUS3": 3,
    "FIVE1": 5, "FIVE2": 5, "FIVE3": 5,
    "TEN1": 10, "TEN2": 10
}

# ================= FLASK 24/7 =================
app_flask = Flask('')
@app_flask.route('/')
def home(): return "Bot is Online!"
def run(): app_flask.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    referred_by INTEGER,
    payout_info TEXT,
    joined_bonus INTEGER DEFAULT 0,
    deposit_done INTEGER DEFAULT 0,
    last_daily TEXT DEFAULT ''
)
""")
cursor.execute("""CREATE TABLE IF NOT EXISTS gift_used(user_id INTEGER, code TEXT)""")
conn.commit()

# ================= MENU =================
def main_menu():
    keyboard = [
        ["🎁 Balance", "🎉 Gift Code"],
        ["👫 Refer & Earn", "🎡 Spin"],
        ["🚀 Withdraw", "Payout Method 🏦"],
        ["📤 Withdrawal Proof", "🆘 Support"],
        ["📊 Stats", "📢 Broadcast"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================= FORCE JOIN =================
async def is_joined(user_id, context):
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member","administrator","creator"]: return False
        except: return False
    return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ref_id = int(context.args[0]) if context.args and context.args[0].isdigit() else None
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users(user_id, referred_by) VALUES(?,?)",(user_id, ref_id))
        if ref_id and ref_id != user_id:
            ref_bonus = random.randint(24,30)
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?",(ref_bonus, ref_id))
        conn.commit()

    if not await is_joined(user_id, context):
        keyboard = [
            [InlineKeyboardButton("Join 1", url="https://t.me/eraxchannal"),
             InlineKeyboardButton("Join 2", url="https://t.me/rajaluckera7x")],
            [InlineKeyboardButton("Join 3", url="https://t.me/withrawalupi")],
            [InlineKeyboardButton("✅ Claim", callback_data="claim_join")]
        ]
        await update.message.reply_text("⚠️ Pehle sabhi channels join karo",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    await update.message.reply_text("👑 Welcome to Bot!", reply_markup=main_menu())

# ================= CLAIM JOIN BONUS =================
async def claim_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    cursor.execute("SELECT joined_bonus FROM users WHERE user_id=?",(user_id,))
    if cursor.fetchone()[0]==1:
        await query.message.reply_text("❌ Join bonus already claim ho chuka", reply_markup=main_menu())
        return
    join_bonus = random.randint(34,45)
    cursor.execute("UPDATE users SET balance = balance + ?, joined_bonus = 1 WHERE user_id=?",(join_bonus,user_id))
    conn.commit()
    await query.message.reply_text(f"✅ Join bonus ₹{join_bonus} added!", reply_markup=main_menu())

# ================= DAILY BONUS =================
async def daily(update, context):
    user_id = update.effective_user.id
    today = date.today().isoformat()
    cursor.execute("SELECT last_daily, balance FROM users WHERE user_id=?",(user_id,))
    last, bal = cursor.fetchone()
    if last==today: await update.message.reply_text("❌ Aaj ka daily bonus already claim ho chuka"); return
    bal += DAILY_BONUS
    cursor.execute("UPDATE users SET balance=?, last_daily=? WHERE user_id=?",(bal,today,user_id))
    conn.commit()
    await update.message.reply_text(f"✅ ₹{DAILY_BONUS} Daily Bonus added! Balance: ₹{bal}")

# ================= SPIN WHEEL =================
async def spin(update, context):
    user_id = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?",(user_id,))
    bal = cursor.fetchone()[0]
    if bal<SPIN_COST: await update.message.reply_text("❌ Spin ke liye ₹2 chahiye"); return
    bal -= SPIN_COST
    reward = random.choice(SPIN_REWARDS)
    if reward>0: bal += reward
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?",(bal,user_id))
    conn.commit()
    msg = await update.message.reply_text("🎡 Spinning the wheel...")
    for _ in range(10):
        await msg.edit_text(f"🎡 {random.choice(SPIN_REWARDS)} spinning...")
        await asyncio.sleep(0.2)
    await msg.edit_text(f"🎉 You won ₹{reward}!" if reward>0 else "😢 Try Again!" + f"\n💰 Balance: ₹{bal}")

# ================= HIDDEN ADMIN GIFT =================
async def gift_code(update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Ye command sirf admin ke liye hai")
        return
    available_codes = []
    for code, amt in GIFT_CODES.items():
        cursor.execute("SELECT COUNT(*) FROM gift_used WHERE code=?",(code,))
        used = cursor.fetchone()[0]
        limit = 200 if amt==3 else 50
        if used<limit: available_codes.append(f"{code} → ₹{amt} (Used {used}/{limit})")
    msg = "🎁 Available Gift Codes:\n" + "\n".join(available_codes) if available_codes else "❌ Koi valid gift code nahi hai"
    await update.message.reply_text(msg)

async def give_gift(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args)!=2: await update.message.reply_text("Usage: /give_gift USERID CODE"); return
    user_id = int(context.args[0]); code = context.args[1].upper()
    if code not in GIFT_CODES: await update.message.reply_text("❌ Invalid code"); return
    cursor.execute("SELECT * FROM gift_used WHERE user_id=? AND code=?",(user_id,code))
    if cursor.fetchone(): await update.message.reply_text("❌ User already received this code"); return
    cursor.execute("SELECT balance FROM users WHERE user_id=?",(user_id,))
    bal = cursor.fetchone()[0] + GIFT_CODES[code]
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?",(bal,user_id))
    cursor.execute("INSERT INTO gift_used(user_id, code) VALUES(?,?)",(user_id, code))
    conn.commit()
    try: await context.bot.send_message(user_id,f"🎁 You received ₹{GIFT_CODES[code]} gift!")
    except: pass
    await update.message.reply_text(f"✅ ₹{GIFT_CODES[code]} sent to {user_id}")

# ================= HANDLE MESSAGE =================
async def handle_msg(update, context):
    text = update.message.text
    user_id = update.effective_user.id
    cursor.execute("SELECT balance, payout_info, deposit_done FROM users WHERE user_id=?",(user_id,))
    bal, upi, dep = cursor.fetchone()

    if context.user_data.get("wait_upi"):
        cursor.execute("UPDATE users SET payout_info=?, deposit_done=1 WHERE user_id=?",(text,user_id))
        conn.commit(); context.user_data["wait_upi"]=False
        await update.message.reply_text(f"✅ UPI saved & Deposit ₹{DEPOSIT_CHECK} approved", reply_markup=main_menu()); return

    if context.user_data.get("wait_withdraw"):
        amount = int(text)
        context.user_data["wait_withdraw"] = False
        if bal<amount: await update.message.reply_text("❌ Insufficient balance"); return
        bal -= amount
        cursor.execute("UPDATE users SET balance=? WHERE user_id=?",(bal,user_id))
        conn.commit()
        # Admin notification with full details
        user_name = update.effective_user.full_name
        username = f"@{update.effective_user.username}" if update.effective_user.username else "No username"
        await context.bot.send_message(
            ADMIN_ID,
            f"💸 Withdraw Request\nUser ID: {user_id}\nName: {user_name}\nUsername: {username}\nRequested Amount: ₹{amount}\nRemaining Balance: ₹{bal}"
        )
        await update.message.reply_text("✅ Withdrawal submitted! Admin notified.", reply_markup=main_menu()); return

    if text=="🎁 Balance": await update.message.reply_text(f"💰 Balance: ₹{bal}")
    elif text=="Payout Method 🏦": context.user_data["wait_upi"]=True; await update.message.reply_text("📥 Apna UPI ID bhejo")
    elif text=="🚀 Withdraw":
        if not upi: await update.message.reply_text("❌ Pehle payout set karo")
        elif dep==0: await update.message.reply_text(f"💳 Withdraw se pehle ₹{DEPOSIT_CHECK} deposit karo\nUPI: {UPI_ID}")
        elif bal<MIN_WITHDRAW: await update.message.reply_text(f"❌ Min withdraw ₹{MIN_WITHDRAW}\nBalance ₹{bal}")
        else: context.user_data["wait_withdraw"]=True; await update.message.reply_text("💸 Kitna withdraw karna hai?")
    elif text=="👫 Refer & Earn":
        bot_info = await context.bot.get_me(); link = f"https://t.me/{bot_info.username}?start={user_id}"
        await update.message.reply_text(f"🔗 Referral:\n{link}\n💸 ₹24–₹30 per refer")
    elif text=="🎡 Spin": await spin(update, context)
    elif text=="🆘 Support": await update.message.reply_text("📞 Contact: @eraxayann")
    elif text=="📤 Withdrawal Proof": await update.message.reply_text("📢 Proof Channel:\nhttps://t.me/withrawalupi")
    elif text=="📊 Stats" and user_id==ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users"); total = cursor.fetchone()[0]
        await update.message.reply_text(f"👥 Total Users: {total}")
    elif text.startswith("/broadcast") and user_id==ADMIN_ID:
        msg = text.replace("/broadcast ",""); cursor.execute("SELECT user_id FROM users")
        for uid in cursor.fetchall():
            try: await context.bot.send_message(uid[0], msg)
            except: continue
        await update.message.reply_text("✅ Broadcast sent")
    elif text=="/daily": await daily(update, context)
    else: await update.message.reply_text("❌ Ye command wrong hai!")  # Unknown command reply

# ================== MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("give_gift", give_gift))
    app.add_handler(CommandHandler("gift_code", gift_code))
    app.add_handler(CallbackQueryHandler(claim_join, pattern="claim_join"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    app.add_handler(MessageHandler(filters.COMMAND, lambda u,c: u.message.reply_text("❌ Ye command wrong hai!")))
    print("🤖 Final BOT running...")
    app.run_polling()

if __name__=="__main__":
    keep_alive()
    main()
