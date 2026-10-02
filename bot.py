import os
import random
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.getenv("BOT_TOKEN", "")
DB = os.getenv("DB_PATH", "bingo.db")


def db():
    conn = sqlite3.connect(DB)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            card TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT DEFAULT 'waiting',
            called TEXT DEFAULT ''
        )
    """)

    conn.commit()
    return conn


def make_card():
    columns = [
        random.sample(range(1, 16), 5),
        random.sample(range(16, 31), 5),
        random.sample(range(31, 46), 5),
        random.sample(range(46, 61), 5),
        random.sample(range(61, 76), 5),
    ]

    card = []

    for row in range(5):
        line = []

        for col in range(5):
            line.append(columns[col][row])

        card.append(line)

    card[2][2] = "FREE"

    return card


def card_text(card):
    text = "🎫 YOUR BINGO CARD\n\n"
    text += " B    I    N    G    O\n"
    text += "-------------------------\n"

    for row in card:
        text += " ".join(f"{str(x):>4}" for x in row)
        text += "\n"

    return text


def save_player(user_id, username, first_name, card):
    conn = db()

    conn.execute(
        """
        INSERT INTO players(user_id, username, first_name, card)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name,
            card=excluded.card
        """,
        (
            user_id,
            username,
            first_name,
            str(card),
        ),
    )

    conn.commit()
    conn.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    keyboard = [
        [
            InlineKeyboardButton(
                "🎫 JOIN GAME",
                callback_data="join_game"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 MY CARD",
                callback_data="my_card"
            )
        ],
    ]

    await update.message.reply_text(
        "🎱 VAMMOS BINGO\n\n"
        "Welcome to the Bingo game!\n\n"
        "👥 Join the game and receive your 5×5 card.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user

    if query.data == "join_game":

        card = make_card()

        save_player(
            user.id,
            user.username or "",
            user.first_name or "",
            card,
        )

        await query.edit_message_text(
            "✅ YOU JOINED THE GAME!\n\n"
            f"👤 Name: {user.first_name}\n"
            f"🆔 Telegram ID: {user.id}\n"
            f"🔗 Username: @{user.username if user.username else 'none'}\n\n"
            + card_text(card)
            + "\n🎮 Wait for the game to start."
        )

    elif query.data == "my_card":

        conn = db()

        row = conn.execute(
            "SELECT card FROM players WHERE user_id=?",
            (user.id,),
        ).fetchone()

        conn.close()

        if not row:
            await query.edit_message_text(
                "❌ You do not have a card yet.\n\n"
                "Press /start and join the game."
            )
            return

        card = eval(row[0])

        await query.edit_message_text(
            f"👤 {user.first_name}\n\n"
            + card_text(card)
        )


async def players(update: Update, context: ContextTypes.DEFAULT_TYPE):

    conn = db()

    rows = conn.execute(
        """
        SELECT user_id, username, first_name
        FROM players
        """
    ).fetchall()

    conn.close()

    if not rows:
        await update.message.reply_text(
            "👥 No players have joined yet."
        )
        return

    text = "👥 PLAYERS\n\n"

    for i, row in enumerate(rows, 1):

        user_id, username, first_name = row

        text += (
            f"{i}. {first_name}\n"
            f"   ID: {user_id}\n"
            f"   Username: @{username if username else 'none'}\n\n"
        )

    await update.message.reply_text(text)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    conn = db()

    conn.execute("DELETE FROM players")

    conn.commit()
    conn.close()

    await update.message.reply_text(
        "♻️ All demo players have been removed."
    )


def main():

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing."
        )

    db().close()

    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("players", players)
    )

    app.add_handler(
        CommandHandler("reset", reset)
    )

    app.add_handler(
        CallbackQueryHandler(button)
    )

    print("Vammos Bingo Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
