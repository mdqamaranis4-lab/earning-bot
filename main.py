import sqlite3, random
from datetime import date, datetime
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ================= CONFIG =================
TOKEN = "8339268119:AAF7Kdn8kn2FlPh3QuukJhwA_pecTUCsZTc"
UPI_ID = "@babu.440@superyes"
ADMIN_ID = 7499239556

CHANNELS = ["@eraxchannal", "@rajaluckera7x", "@withrawalupi"]
MIN_WITHDRAW = 250
DAILY_BONUS = 7

# Gift codes
GIFT_CODES = {
    "FREE3":3,"WELCOME3":3,"BONUS3":3,
    "FIVE1":5,"FIVE2":5,"FIVE3":5,
    "TEN1":10,"TEN2":10,
    "BIG200":200
}

# ================= FLASK 24/7 =================
app_flask = Flask('')
@app_flask.route('/')
def home(): return "Bot Online!"
def run(): app_flask.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    balance INTEGER DEFAULT 0,
    referred_by INTEGER,
    payout_info TEXT,
    joined_bonus INTEGER DEFAULT 0,
    deposit_done INTEGER DEFAULT 0,
    last_daily TEXT DEFAULT ''
)
""")
cursor.execute("CREATE TABLE IF NOT EXISTS gift_used(user_id INTEGER, code TEXT)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS withdrawal_requests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    status TEXT DEFAULT 'pending',
    created_at TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS deposit_requests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    status TEXT DEFAULT 'pending',
    created_at TEXT
)
""")
conn.commit()

# ================= MENU =================
def main_menu(admin=False):
    keyboard = [
        ["🎁 Gift Code","🎉 Daily Bonus"],
        ["🎁 Balance","👫 Refer & Earn"],
        ["🚀 Withdraw","Payout Method 🏦"],
        ["📤 Withdrawal Proof","🆘 Support"]
    ]
    if admin:
        keyboard.append(["📊 Stats"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================= FORCE JOIN =================
async def is_joined(user_id, context):
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user_id)
            if member.status not in ["member","administrator","creator"]:
                return False
        except: return False
    return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name
    ref_id = int(context.args[0]) if context.args and context.args[0].isdigit() else None

    cursor.execute("SELECT * FROM users WHERE user_id=?",(user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users(user_id,username,full_name,referred_by) VALUES(?,?,?,?)",
                       (user_id,username,full_name,ref_id))
        conn.commit()
        joined_bonus_claimed=False
    else:
        joined_bonus_claimed = user[6]==1

    joined_all = await is_joined(user_id, context)
    if not joined_all:
        keyboard = [
            [InlineKeyboardButton("Join 1", url="https://t.me/eraxchannal"),
             InlineKeyboardButton("Join 2", url="https://t.me/rajaluckera7x")],
            [InlineKeyboardButton("Join 3", url="https://t.me/withrawalupi")],
            [InlineKeyboardButton("✅ Claim Bonus", callback_data="claim_join")]
        ]
        await update.message.reply_text(
            "⚠️ Pehle sabhi channels join karo phir bonus claim kar paoge!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if joined_bonus_claimed:
        await update.message.reply_text("❌ You already claimed joining bonus", reply_markup=main_menu(admin=(user_id==ADMIN_ID)))
    else:
        keyboard = [[InlineKeyboardButton("✅ Claim Join Bonus", callback_data="claim_join")]]
        await update.message.reply_text("🎉 Channels joined! Claim your bonus:", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= CLAIM JOIN BONUS =================
async def claim_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    cursor.execute("SELECT joined_bonus, referred_by FROM users WHERE user_id=?",(user_id,))
    joined_bonus, ref_id = cursor.fetchone()
    if joined_bonus==1:
        await query.message.reply_text("❌ You already claimed joining bonus", reply_markup=main_menu(admin=(user_id==ADMIN_ID)))
        return
    join_bonus = random.randint(34,45)
    cursor.execute("UPDATE users SET balance=balance+?, joined_bonus=1 WHERE user_id=?",(join_bonus,user_id))
    conn.commit()
    await query.message.reply_text(f"✅ Joining bonus ₹{join_bonus} added!", reply_markup=main_menu(admin=(user_id==ADMIN_ID)))

    if ref_id:
        cursor.execute("SELECT username FROM users WHERE user_id=?",(user_id,))
        user_ref_username = cursor.fetchone()[0] or "user"
        ref_bonus = random.randint(24,30)
        cursor.execute("UPDATE users SET balance=balance+? WHERE user_id=?",(ref_bonus,ref_id))
        conn.commit()
        try:
            await context.bot.send_message(ref_id,f"🎉 You received refer bonus ₹{ref_bonus} from @{user_ref_username}")
        except: pass

# ================= DAILY BONUS =================
async def daily(update,context):
    user_id = update.effective_user.id
    today = date.today().isoformat()
    cursor.execute("SELECT last_daily, balance FROM users WHERE user_id=?",(user_id,))
    last, bal = cursor.fetchone()
    if last==today:
        await update.message.reply_text("❌ Daily bonus already claimed")
        return
    bal += DAILY_BONUS
    cursor.execute("UPDATE users SET balance=?, last_daily=? WHERE user_id=?",(bal,today,user_id))
    conn.commit()
    await update.message.reply_text(f"✅ ₹{DAILY_BONUS} Daily Bonus added!\n💰 Balance: ₹{bal}")

# ================= GIFT CODE =================
async def gift_code(update,context):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("🎁 Gift code claim karne ke liye type kare:\n/gift CODE")
        return
    code = context.args[0].upper()
    if code not in GIFT_CODES:
        await update.message.reply_text("❌ Ye gift code wrong hai!")
        return

    cursor.execute("SELECT * FROM gift_used WHERE user_id=? AND code=?",(user_id,code))
    if cursor.fetchone():
        await update.message.reply_text("❌ Aapne ye code pehle hi use kar liya hai!")
        return

    amt = GIFT_CODES[code]
    if amt==200: limit=5
    elif amt==3: limit=200
    else: limit=50

    cursor.execute("SELECT COUNT(*) FROM gift_used WHERE code=?",(code,))
    used = cursor.fetchone()[0]
    if used >= limit:
        await update.message.reply_text("❌ Ye code ka limit poora ho gaya hai!")
        return

    cursor.execute("SELECT balance FROM users WHERE user_id=?",(user_id,))
    bal = cursor.fetchone()[0]+amt
    cursor.execute("UPDATE users SET balance=? WHERE user_id=?",(bal,user_id))
    cursor.execute("INSERT INTO gift_used(user_id, code) VALUES(?,?)",(user_id,code))
    conn.commit()
    await update.message.reply_text(f"✅ ₹{amt} aapke wallet me add ho gya!\n💰 Balance: ₹{bal}")

# ================= HANDLE MESSAGE =================
async def handle_msg(update,context):
    text = update.message.text
    user_id = update.effective_user.id
    cursor.execute("SELECT balance,payout_info,deposit_done FROM users WHERE user_id=?",(user_id,))
    bal, upi, dep = cursor.fetchone()
    admin = user_id==ADMIN_ID

    if context.user_data.get("wait_upi"):
        cursor.execute("UPDATE users SET payout_info=?, deposit_done=0 WHERE user_id=?",(text,user_id))
        conn.commit(); context.user_data["wait_upi"]=False
        kb = [[InlineKeyboardButton("✅ Approve",callback_data=f"d_approve_{user_id}"),
               InlineKeyboardButton("❌ Reject",callback_data=f"d_reject_{user_id}")]]
        await context.bot.send_message(ADMIN_ID,
            f"💳 Deposit request ₹25 from @{update.effective_user.username} (ID: {user_id})\nUPI: {text}",
            reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("✅ UPI submitted successfully", reply_markup=main_menu(admin=admin))
        return

    if context.user_data.get("wait_withdraw"):
        amount = int(text); context.user_data["wait_withdraw"]=False
        if bal<amount: await update.message.reply_text("❌ Insufficient balance"); return
        bal-=amount
        cursor.execute("UPDATE users SET balance=? WHERE user_id=?",(bal,user_id))
        cursor.execute("INSERT INTO withdrawal_requests(user_id,amount,created_at) VALUES(?,?,?)",
                       (user_id,amount,datetime.now().isoformat()))
        conn.commit()
        # Notify admin with UPI
        kb = [[InlineKeyboardButton("✅ Approve",callback_data=f"w_approve_{user_id}"),
               InlineKeyboardButton("❌ Reject",callback_data=f"w_reject_{user_id}")]]
        await context.bot.send_message(ADMIN_ID,
            f"💸 Withdrawal request ₹{amount} from @{update.effective_user.username} (ID: {user_id})\nUPI: {upi}",
            reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text(f"✅ Withdrawal request of ₹{amount} submitted!", reply_markup=main_menu(admin=admin))
        return

    # MENU OPTIONS
    if text=="🎉 Daily Bonus": await daily(update,context); return
    elif text=="🎁 Gift Code": await gift_code(update,context); return
    elif text=="🎁 Balance": await update.message.reply_text(f"💰 Balance: ₹{bal}")
    elif text=="Payout Method 🏦": context.user_data["wait_upi"]=True; await update.message.reply_text("📥 Apna UPI ID bhejo")
    elif text=="🚀 Withdraw":
        if not upi:
            await update.message.reply_text("❌ Pehle payout set karo")
        elif bal>=MIN_WITHDRAW and dep==0:
            await update.message.reply_text(f"💳 Withdraw se pehle ₹25 deposit karein\nUPI: {UPI_ID}")
        elif bal<MIN_WITHDRAW:
            await update.message.reply_text(f"❌ Minimum withdrawal ₹{MIN_WITHDRAW}\nBalance ₹{bal}")
        else:
            context.user_data["wait_withdraw"]=True; await update.message.reply_text("💸 Kitna withdraw karna hai?")
    elif text=="👫 Refer & Earn":
        bot_info = await context.bot.get_me(); link = f"https://t.me/{bot_info.username}?start={user_id}"
        await update.message.reply_text(f"🔗 Referral:\n{link}\n💸 ₹24–₹30 per refer")
    elif text=="🆘 Support": await update.message.reply_text("📞 Contact: @flax_truth")
    elif text=="📤 Withdrawal Proof": await update.message.reply_text("📢 Proof Channel:\nhttps://t.me/withrawalupi")
    elif admin and text=="📊 Stats":
        cursor.execute("SELECT COUNT(*) FROM users"); total_users=cursor.fetchone()[0]
        cursor.execute("SELECT SUM(balance) FROM users"); total_bal=cursor.fetchone()[0] or 0
        cursor.execute("SELECT COUNT(*) FROM withdrawal_requests"); total_withdraw=cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM deposit_requests"); total_deposit=cursor.fetchone()[0]
        await update.message.reply_text(f"📊 Bot Stats:\nTotal Users: {total_users}\nTotal Balance: ₹{total_bal}\nTotal Withdrawals Requests: {total_withdraw}\nTotal Deposit Requests: {total_deposit}")
    else: await update.message.reply_text("❌ Ye command wrong hai!")

# ================= CALLBACKS =================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query=update.callback_query
    await query.answer()
    data=query.data
    user_id=query.from_user.id

    if data=="claim_join": await claim_join(update,context); return
    if user_id!=ADMIN_ID: return

    # Admin withdraw approve/reject
    if data.startswith("w_approve_"):
        uid=int(data.split("_")[-1])
        cursor.execute("SELECT amount FROM withdrawal_requests WHERE user_id=? AND status='pending'",(uid,))
        row=cursor.fetchone()
        if row:
            amount=row[0]
            cursor.execute("UPDATE withdrawal_requests SET status='approved' WHERE user_id=? AND status='pending'",(uid,))
            conn.commit()
            try: await context.bot.send_message(uid,f"✅ Your withdrawal of ₹{amount} is approved!")
            except: pass
            await query.message.reply_text(f"✅ Withdrawal approved for user {uid}")
    elif data.startswith("w_reject_"):
        uid=int(data.split("_")[-1])
        cursor.execute("SELECT amount FROM withdrawal_requests WHERE user_id=? AND status='pending'",(uid,))
        row=cursor.fetchone()
        if row:
            amount=row[0]
            cursor.execute("UPDATE withdrawal_requests SET status='rejected' WHERE user_id=? AND status='pending'",(uid,))
            cursor.execute("UPDATE users SET balance=balance+? WHERE user_id=?",(amount,uid))
            conn.commit()
            try: await context.bot.send_message(uid,f"❌ Your withdrawal of ₹{amount} is rejected! Amount returned to wallet.")
            except: pass
            await query.message.reply_text(f"❌ Withdrawal rejected for user {uid}")

    # Admin deposit approve/reject
    elif data.startswith("d_approve_"):
        uid=int(data.split("_")[-1])
        cursor.execute("UPDATE users SET deposit_done=1 WHERE user_id=?",(uid,))
        conn.commit()
        try: await context.bot.send_message(uid,f"✅ Your deposit ₹25 approved!")
        except: pass
        await query.message.reply_text(f"✅ Deposit approved for user {uid}")
    elif data.startswith("d_reject_"):
        uid=int(data.split("_")[-1])
        cursor.execute("UPDATE users SET deposit_done=0 WHERE user_id=?",(uid,))
        conn.commit()
        try: await context.bot.send_message(uid,f"❌ Your deposit ₹25 rejected!")
        except: pass
        await query.message.reply_text(f"❌ Deposit rejected for user {uid}")

# ================= MAIN =================
def main():
    app=ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("daily",daily))
    app.add_handler(CommandHandler("gift",gift_code))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND),handle_msg))
    app.add_handler(MessageHandler(filters.COMMAND,lambda u,c:u.message.reply_text("❌ Ye command wrong hai!")))
    print("🤖 Final BOT running with Admin Panel...")
    app.run_polling()

if __name__=="__main__":
    keep_alive()
    main()
