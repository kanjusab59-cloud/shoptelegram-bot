# pip install python-telegram-bot==20.7

import json, os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8673127228:AAEue-xyJECIWMyLwMabLmpEyRPr7iN7-iU"
ADMIN_IDS = [1978055060, 6697028067]

BKASH = "01721607574"
NAGAD = "01721607574"
BINANCE = "760440549"

USERS = "users.json"
PRODUCTS = "products.json"

# ---------- DB ----------
def load(file):
    if not os.path.exists(file):
        return {}
    try:
        return json.load(open(file))
    except:
        return {}

def save(file, data):
    json.dump(data, open(file, "w"), indent=2)

def is_admin(uid):
    return int(uid) in ADMIN_IDS

# ---------- MENU ----------
def menu(uid):
    btn = [
        ["💰 My Balance", "🛒 Buy Product"],
        ["📦 My Orders", "💳 Deposit"],
        ["💬 Support"]
    ]
    if is_admin(uid):
        btn.append(["⚙️ Admin Panel"])
    return ReplyKeyboardMarkup(btn, resize_keyboard=True)

# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load(USERS)
    uid = str(update.effective_user.id)

    if uid not in users:
        users[uid] = {
            "balance":0,
            "orders":[],
            "spent":0,
            "blocked":False,
            "username": update.effective_user.username or "NoUsername"
        }
        save(USERS, users)

    await update.message.reply_text(
f"""🚀 This Person Is Brand SHOP

👋 Welcome {update.effective_user.first_name}

🔥 100% genuine stock
⚡ Instant delivery
🔐 Secure balance

👇 Use buttons below""",
reply_markup=menu(uid))

# ---------- MAIN ----------
async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
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

    # ===== BUY =====
    elif txt == "🛒 Buy Product":
        if not products:
            await update.message.reply_text("No product")
            return

        msg = "🛒 Product List:\n\n"
        for pid,p in products.items():
            msg += f"{pid}. {p['name']} ({p['price']}৳) Stock:{len(p['stock'])}\n"

        context.user_data.clear()
        context.user_data["mode"] = "pid"
        await update.message.reply_text(msg)

    elif context.user_data.get("mode") == "pid":
        if txt not in products:
            await update.message.reply_text("❌ Invalid ID")
            return

        context.user_data["pid"] = txt
        context.user_data["mode"] = "qty"
        await update.message.reply_text("🔢 Enter quantity:")

    elif context.user_data.get("mode") == "qty":
        try:
            qty = int(txt)
            context.user_data["qty"] = qty
            context.user_data["mode"] = "confirm"

            p = products[context.user_data["pid"]]

            await update.message.reply_text(
                f"""🛒 Confirm Buy

📦 {p['name']}
🔢 Qty: {qty}
💰 Total: {qty*p['price']}

Type YES"""
            )
        except:
            await update.message.reply_text("❌ Invalid quantity")

    elif context.user_data.get("mode") == "confirm":
        if txt.lower() != "yes":
            context.user_data.clear()
            await update.message.reply_text("❌ Cancelled")
            return

        pid = context.user_data["pid"]
        qty = context.user_data["qty"]
        p = products[pid]

        if qty > len(p["stock"]):
            await update.message.reply_text("❌ Not enough stock")
            context.user_data.clear()
            return

        total = qty * p["price"]

        if not is_admin(uid):
            if user["balance"] < total:
                await update.message.reply_text("❌ Balance low")
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

        # ADMIN NOTIFY
        for admin in ADMIN_IDS:
            await context.bot.send_message(
                admin,
                f"""🛒 New Order

👤 @{uname}
🆔 {uid}
📦 {p['name']}
🔢 Qty: {qty}
💰 {total}"""
            )

        with open(f"{uid}.txt","w") as f:
            f.write("\n".join(items))

        await update.message.reply_document(open(f"{uid}.txt","rb"))
        context.user_data.clear()

    # ===== ORDERS =====
    elif txt == "📦 My Orders":
        await update.message.reply_text("\n".join(user["orders"]) or "No orders")

    # ===== DEPOSIT =====
    elif txt == "💳 Deposit":
        await update.message.reply_text(
f"""💳 Deposit Info

📱 bKash: {BKASH}
📱 Nagad: {NAGAD}
💰 Binance: {BINANCE}

💱 1 USD = 127-128 BDT

➡️ Send:
Amount [space] TRX ID [space] Screenshot [Optional]"""
        )

    elif txt.split()[0].isdigit():
        for admin in ADMIN_IDS:
            await context.bot.send_message(
                admin,
                f"""💳 Deposit Request

👤 @{uname}
🆔 {uid}
📩 {txt}"""
            )
        await update.message.reply_text("✅ Sent to admin")

    # ===== SUPPORT =====
    elif txt == "💬 Support":
        context.user_data["support"] = True
        await update.message.reply_text("Send your problem")

    elif context.user_data.get("support"):
        for admin in ADMIN_IDS:
            await context.bot.send_message(
                admin,
                f"""💬 Support

👤 @{uname}
🆔 {uid}
📩 {txt}"""
            )
        await update.message.reply_text("✅ Sent")
        context.user_data.clear()

    # ===== ADMIN PANEL =====
    elif txt == "⚙️ Admin Panel" and is_admin(uid):
        await update.message.reply_text(
            "/add /stats /approve /broadcast /replace /block /unblock"
        )

    else:
        await update.message.reply_text("OK")

# ---------- ADMIN ----------
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    try:
        _, pid, name, price, items = update.message.text.split(" ",4)
        products = load(PRODUCTS)

        products[pid] = {
            "name": name,
            "price": float(price),
            "stock": items.split(",")
        }

        save(PRODUCTS, products)
        await update.message.reply_text("✅ Product Added")
    except:
        await update.message.reply_text("/add id name price item1,item2")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    users = load(USERS)
    msg = "👥 Users List:\n\n"
    for uid,u in users.items():
        msg += f"@{u.get('username')} | {uid}\n"

    await update.message.reply_text(msg)

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    uid = context.args[0]
    amount = float(context.args[1])

    users = load(USERS)
    users[uid]["balance"] += amount
    save(USERS, users)

    await update.message.reply_text("✅ Balance Added")

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
        except:
            pass

    await update.message.reply_text(f"✅ Sent: {sent}")

async def replace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    uid = context.args[0]
    data = " ".join(context.args[1:])

    with open("replace.txt","w") as f:
        f.write(data)

    await context.bot.send_document(int(uid), open("replace.txt","rb"))
    await update.message.reply_text("✅ Replaced")

async def block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    uid = context.args[0]
    users = load(USERS)

    users[uid]["blocked"] = True
    save(USERS, users)

    await update.message.reply_text("🚫 User Blocked")

async def unblock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    uid = context.args[0]
    users = load(USERS)

    users[uid]["blocked"] = False
    save(USERS, users)

    await update.message.reply_text("✅ User Unblocked")

# ---------- RUN ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("approve", approve))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("replace", replace))
app.add_handler(CommandHandler("block", block))
app.add_handler(CommandHandler("unblock", unblock))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

app.run_polling()