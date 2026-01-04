import logging
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIG ---
TOKEN = "8132107960:AAEveI9VfRJqhaCY01h88U9KTr8qoUrLZWY"
ADMIN_ID = 2007081642
UPI_ID = "rishabhkapoor098@okhdfcbank" 
QR_MESSAGE = f"💰 **Payment Info**\n\nUpar QR Code scan karein.\nYa iss ID par pay karein: `{UPI_ID}`\n\nPayment karne ke baad screenshot yahan bhejein."

# --- DB SETUP ---
DB_NAME = "chocolate_shop.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS coupons (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, code TEXT, status TEXT DEFAULT 'available')''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS prices (category TEXT PRIMARY KEY, price INTEGER)''')
    c.execute("INSERT OR IGNORE INTO prices VALUES (?, ?)", ("BB Chocolate", 100))
    conn.commit()
    conn.close()

def get_stock(category):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM coupons WHERE category=? AND status='available'", (category,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_multiple_codes(category, qty):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, code FROM coupons WHERE category=? AND status='available' LIMIT ?", (category, qty))
    rows = c.fetchall()
    if len(rows) < qty:
        conn.close()
        return None
    codes, ids = [row[1] for row in rows], [row[0] for row in rows]
    c.execute(f"UPDATE coupons SET status='sold' WHERE id IN ({','.join(['?']*len(ids))})", ids)
    conn.commit()
    conn.close()
    return codes

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [["🛒 Buy BB Chocolate", "📦 Stock Status"]]
    await update.message.reply_text("✨ **WELCOME TO BB PREMIUM BOT** ✨", 
                                   reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), 
                                   parse_mode="Markdown")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🛒 Buy BB Chocolate":
        context.user_data['buying'] = "BB Chocolate"
        await update.message.reply_text("🔢 **Quantity Enter Karein**\nAapko kitne codes chahiye? (Sirf number likhein):")
    elif text == "📦 Stock Status":
        s = get_stock("BB Chocolate")
        await update.message.reply_text(f"📦 **Available Stock:** {s} Codes")
    elif text.isdigit():
        cat = context.user_data.get('buying')
        if not cat: return
        qty = int(text)
        stock = get_stock(cat)
        if qty > stock:
            await update.message.reply_text(f"❌ Sirf {stock} available hain.")
            return
        context.user_data['qty'] = qty
        total = qty * 100
        await update.message.reply_text(f"🛒 **Summary**\nItem: {qty}x {cat}\nTotal: **₹{total}**\n\n{QR_MESSAGE}", parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat, qty = context.user_data.get('buying'), context.user_data.get('qty')
    if not cat or not qty: return
    kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"app_{update.effective_user.id}_{cat}_{qty}")],
          [InlineKeyboardButton("❌ Decline", callback_data=f"dec_{update.effective_user.id}")]]
    await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, 
                                 caption=f"💰 **Payment!**\nUser: {update.effective_user.first_name}\nQty: {qty}\nAmt: ₹{qty*100}", 
                                 reply_markup=InlineKeyboardMarkup(kb))
    await update.message.reply_text("✅ Payment proof sent to Admin.")

async def admin_btns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split("_")
    if data[0] == "app":
        codes = get_multiple_codes(data[2], int(data[3]))
        if codes:
            msg = "✅ **Payment Verified!**\n\nCodes:\n" + "\n".join([f"`{c}`" for c in codes])
            await context.bot.send_message(int(data[1]), msg, parse_mode="Markdown")
            await query.edit_message_caption("✅ Approved.")
    elif data[0] == "dec":
        await context.bot.send_message(int(data[1]), "❌ Payment Declined.")
        await query.edit_message_caption("❌ Declined.")

def main():
    init_db()
    app = Application.builder().token(TOKEN).connect_timeout(30).read_timeout(30).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(admin_btns))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("🚀 Bot Started...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
  
