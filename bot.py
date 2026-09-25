import os
import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN", "")
DB = os.getenv("DB_PATH", "bingo.db")
TICKET_PRICE = 20
PRIZE_PERCENT = 70

def db():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS players(
        user_id INTEGER PRIMARY KEY, username TEXT, tickets INTEGER DEFAULT 0
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS games(
        id INTEGER PRIMARY KEY AUTOINCREMENT, status TEXT, called TEXT DEFAULT '',
        prize_pool INTEGER DEFAULT 0
    )""")
    conn.commit()
    return conn

def make_card():
    # Standard 5x5 bingo columns: B 1-15, I 16-30, N 31-45, G 46-60, O 61-75
    cols = [
        random.sample(range(1,16), 5),
        random.sample(range(16,31), 5),
        random.sample(range(31,46), 5),
        random.sample(range(46,61), 5),
        random.sample(range(61,76), 5),
    ]
    card = [[cols[c][r] for c in range(5)] for r in range(5)]
    card[2][2] = "FREE"
    return card

def card_text(card):
    s = " B   I   N   G   O\n"
    s += "-------------------\n"
    for row in card:
        s += " ".join(f"{str(x):>4}" for x in row) + "\n"
    return s

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🎫 Demo Ticket", callback_data="ticket")],
          [InlineKeyboardButton("📋 My Card", callback_data="card")]]
    await update.message.reply_text(
        "🎉 Vammos Bingo Bot\n\n"
        f"የDemo ቲኬት: {TICKET_PRICE} ብር\n"
        "ይህ ስሪት የBingo አሰራሩን ለመሞከር ነው።\n"
        "Telebirr/CBE Birr ክፍያ እስካሁን አልተገናኘም።",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "ticket":
        conn = db()
        conn.execute(
            "INSERT INTO players(user_id, username, tickets) VALUES(?,?,1) "
            "ON CONFLICT(user_id) DO UPDATE SET tickets=tickets+1, username=excluded.username",
            (q.from_user.id, q.from_user.username or "")
        )
        conn.commit()
        conn.close()
        card = make_card()
        context.user_data["card"] = card
        await q.edit_message_text(
            "🎫 Demo Ticket ተመዝግቧል!\n\n" + card_text(card) +
            "\nቀጣይ ደረጃ: የክፍያ ማረጋገጫና የጨዋታ አስተዳደር እንጨምራለን።"
        )
    elif q.data == "card":
        card = context.user_data.get("card")
        if not card:
            await q.edit_message_text("ካርድ የለህም። /start ተጫን እና Demo Ticket ውሰድ።")
        else:
            await q.edit_message_text(card_text(card))

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Set it as an environment variable; do not put the token in the source code.")
    db().close()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
