import json
import logging
import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

BKASH = os.getenv("BKASH", "01721607574")
NAGAD = os.getenv("NAGAD", "01721607574")
BINANCE = os.getenv("BINANCE", "760440549")

USERS = "users.json"
PRODUCTS = "products.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ================= DB =================
def ensure_file(file_name):
    if not os.path.exists(file_name):
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump({}, f)


def load(file_name):
    ensure_file(file_name)
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(file_name, data):
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_admin(uid):
    return int(uid) in ADMIN_IDS


# ================= MENU =================
def menu(uid):
    buttons = [
        ["💰 My Balance", "🛒 Buy Product"],
        ["📦 My Orders", "💳 Deposit"],
        ["💬 Support"],
    ]

    if is_admin(uid):
        buttons.append(["⚙️ Admin Panel"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load(USERS)
    uid = str(update.effective_user.id)

    if uid not in users:
        users[uid] = {
            "balance": 0,
            "orders": [],
            "spent": 0,
            "blocked": False,
            "username": update.effective_user.username or "NoUsername",
        }
        save(USERS, users)

    await update.message.reply_text(
        f"""🚀 This Person Is Brand SHOP

👋 Welcome {update.effective_user.first_name}

🔥 100% genuine stock
⚡ Instant delivery
🔐 Secure balance

👇 Use buttons below""",
        reply_markup=menu(uid),
    )


# ================= TEXT =================
async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = (update.message.text or "").strip()
    uid = str(update.effective_user.id)
    uname = update.effective_user.username or "NoUsername"

    users = load(USERS)
    products = load(PRODUCTS)

    user = users.get(uid)
    if not user:
        return

    if user.get("blocked"):
        await update.message.reply_text("🚫 You are blocked")
        return

    # ===== BALANCE =====
    if txt == "💰 My Balance":
        msg = f"""👤 @{uname}
🆔 {uid}

💰 Balance: {user['balance']}
📦 Orders: {len(user['orders'])}
💸 Spent: {user['spent']}

👥 Total Users: {len(users)}"""
        await update.message.reply_text(msg)

    # ===== BUY PRODUCT =====
    elif txt == "🛒 Buy Product":
        if not products:
            await update.message.reply_text("❌ No Product Available")
            return

        msg = "🛒 Product List:\n\n"
        for pid, p in products.items():
            stock = len(p.get("stock", []))
            msg += f"{pid}. {p['name']} ({p['price']}৳) Stock:{stock}\n"

        context.user_data.clear()
        context.user_data["mode"] = "pid"
        await update.message.reply_text(msg)

    elif context.user_data.get("mode") == "pid":
        if txt not in products:
            await update.message.reply_text("❌ Invalid Product ID")
            return

        context.user_data["pid"] = txt
        context.user_data["mode"] = "qty"
        await update.message.reply_text("🔢 Enter Quantity:")

    elif context.user_data.get("mode") == "qty":
        try:
            qty = int(txt)
            if qty <= 0:
                raise ValueError

            context.user_data["qty"] = qty
            context.user_data["mode"] = "confirm"

            p = products[context.user_data["pid"]]
            total = qty * p["price"]

            await update.message.reply_text(
                f"""🛒 Confirm Buy

📦 {p['name']}
🔢 Qty: {qty}
💰 Total: {total}

Type YES"""
            )
        except Exception:
            await update.message.reply_text("❌ Invalid Quantity")

    elif context.user_data.get("mode") == "confirm":
        if txt.lower() != "yes":
            context.user_data.clear()
            await update.message.reply_text("❌ Cancelled")
            return

        pid = context.user_data.get("pid")
        qty = context.user_data.get("qty")

        if pid not in products:
            await update.message.reply_text("❌ Product Not Found")
            return

        p = products[pid]

        if qty > len(p.get("stock", [])):
            await update.message.reply_text("❌ Not Enough Stock")
            context.user_data.clear()
            return

        total = qty * p["price"]

        if not is_admin(uid):
            if user["balance"] < total:
                await update.message.reply_text("❌ Low Balance")
                context.user_data.clear()
                return

            user["balance"] -= total
            user["spent"] += total

        items = []
        for _ in range(qty):
            item = p["stock"].pop(0)
            items.append(item)
            user["orders"].append(item)

        save(USERS, users)
        save(PRODUCTS, products)

        for admin in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin,
                    f"""🛒 New Order

👤 @{uname}
🆔 {uid}
📦 {p['name']}
🔢 Qty: {qty}
💰 {total}""",
                )
            except Exception:
                pass

        filename = f"{uid}_order.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(items))

        await update.message.reply_text("✅ Order Delivered")
        await update.message.reply_document(document=open(filename, "rb"))

        try:
            os.remove(filename)
        except Exception:
            pass

        context.user_data.clear()

    # ===== ORDERS =====
    elif txt == "📦 My Orders":
        await update.message.reply_text(
            "\n".join(user.get("orders", [])) or "No Orders"
        )

    # ===== DEPOSIT =====
    elif txt == "💳 Deposit":
        await update.message.reply_text(
            f"""💳 Deposit Info

📱 bKash: {BKASH}
📱 Nagad: {NAGAD}
💰 Binance: {BINANCE}

💱 1 USD = 127-128 BDT

➡️ Send:
Amount TRX_ID Screenshot(Optional)"""
        )

    elif txt.split()[0].isdigit():
        for admin in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin,
                    f"💳 Deposit Request\n\n👤 @{uname}\n🆔 {uid}\n📩 {txt}",
                )
            except Exception:
                pass

        await update.message.reply_text("✅ Deposit Request Sent")

    # ===== SUPPORT =====
    elif txt == "💬 Support":
        context.user_data["support"] = True
        await update.message.reply_text("Send Your Problem")

    elif context.user_data.get("support"):
        for admin in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin,
                    f"💬 Support\n\n👤 @{uname}\n🆔 {uid}\n📩 {txt}",
                )
            except Exception:
                pass

        await update.message.reply_text("✅ Sent To Admin")
        context.user_data.clear()

    # ===== ADMIN PANEL =====
    elif txt == "⚙️ Admin Panel" and is_admin(uid):
        await update.message.reply_text(
            "/add /stats /approve /broadcast /replace /block /unblock"
        )

    else:
        await update.message.reply_text("OK")


# ================= ADMIN =================
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    try:
        _, pid, name, price, items = update.message.text.split(" ", 4)

        products = load(PRODUCTS)
        products[pid] = {
            "name": name,
            "price": float(price),
            "stock": items.split(","),
        }

        save(PRODUCTS, products)
        await update.message.reply_text("✅ Product Added")

    except Exception:
        await update.message.reply_text(
            "/add id name price item1,item2"
        )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    users = load(USERS)
    msg = "👥 Users List:\n\n"

    for uid, u in users.items():
        msg += f"@{u.get('username')} | {uid}\n"

    await update.message.reply_text(msg)


async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    try:
        uid = context.args[0]
        amount = float(context.args[1])

        users = load(USERS)
        if uid not in users:
            await update.message.reply_text("❌ User Not Found")
            return

        users[uid]["balance"] += amount
        save(USERS, users)

        await context.bot.send_message(
            int(uid), f"✅ {amount} Balance Added"
        )

        await update.message.reply_text("✅ Approved")

    except Exception:
        await update.message.reply_text(
            "/approve USER_ID AMOUNT"
        )


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    users = load(USERS)
    message = " ".join(context.args)

    sent = 0
    for uid in users:
        try:
            await context.bot.send_message(int(uid), f"📢 {message}")
            sent += 1
        except Exception:
            pass

    await update.message.reply_text(f"✅ Sent: {sent}")


async def replace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    try:
        uid = context.args[0]
        data = " ".join(context.args[1:])

        filename = "replace.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(data)

        await context.bot.send_document(
            int(uid), document=open(filename, "rb")
        )

        os.remove(filename)
        await update.message.reply_text("✅ Replaced")

    except Exception:
        await update.message.reply_text(
            "/replace USER_ID text"
        )


async def block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    try:
        uid = context.args[0]
        users = load(USERS)

        users[uid]["blocked"] = True
        save(USERS, users)

        await update.message.reply_text("🚫 User Blocked")
    except Exception:
        await update.message.reply_text("/block USER_ID")


async def unblock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    try:
        uid = context.args[0]
        users = load(USERS)

        users[uid]["blocked"] = False
        save(USERS, users)

        await update.message.reply_text("✅ User Unblocked")
    except Exception:
        await update.message.reply_text("/unblock USER_ID")


# ================= RUN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("approve", approve))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("replace", replace))
app.add_handler(CommandHandler("block", block))
app.add_handler(CommandHandler("unblock", unblock))

app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, text)
)

if __name__ == "__main__":
    print("Bot Started...")
    app.run_polling(drop_pending_updates=True)
