from vinted_cookies import get_cookies
from datetime import datetime, timedelta, timezone
from config import TG_TOKEN
import cv2
import asyncio
from PIL import Image
from io import BytesIO
import numpy as np
import logging
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    JobQueue,
    filters,
)
from telegram.constants import ChatAction


logging.basicConfig(level=logging.INFO)

PRICE, BRAND = range(2)
MODE, PHOTO_BRAND, PHOTO_UPLOAD = range(2, 5)


PRICE_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Under zl150", callback_data="0-150")],
    [InlineKeyboardButton("Over zl150", callback_data="150+")],
])

latest_ids = set()
user_chat_id = None
user_filters = {}

def generate_brand_filter_list(text):
    return [b.strip() for b in text.split(',') if b.strip()]

def search_vinted(filters):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "pl-PL,pl;q=0.9",
    })
    cookies = get_cookies()
    cookies["locale"] = "pl"
    session.cookies.update(cookies)
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    base_url = "INPUT here ViNtEd API"

    params = {
        "search_text": filters["keywords"],
        "per_page": 20,
        "page": 1,
        "order": "newest_first",
    }

    if filters["price"] == "0-150":
        params["price_to"] = 150
    else:
        params["price_from"] = 150

    resp = session.get(base_url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("items", [])


async def poll_vinted(application):
    global latest_ids
    if user_chat_id and user_filters:
        try:
            all_new_items = []
            for brand in user_filters["brands"]:
                filters = {"keywords": brand, "price": user_filters["price"]}
                items = await asyncio.to_thread(search_vinted, filters)
                logging.info(f"Fetched {len(items)} items from Vinted for {brand}")
                new_items = [item for item in items if item["id"] not in latest_ids]
                for item in new_items:
                    latest_ids.add(item["id"])
                all_new_items.extend(new_items)

            for item in all_new_items[:20]:
                title = item.get("title")
                url = item.get("url")
                price = item.get("price")
                time_iso = item.get("photo_highlight", {}).get("created_at", "")
                try:
                    dt = datetime.fromisoformat(time_iso.replace("Z", "+00:00"))
                    published_time = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    published_time = "Unknown"

                msg = f"{title}\nPrice: {price}\nPublished: {published_time}\n{url}"
                await application.bot.send_message(chat_id=user_chat_id, text=msg)

        except Exception as e:
            logging.error(f"Polling error: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Search by brand", callback_data="brand_search")],
        [InlineKeyboardButton("🖼️ Search by photo", callback_data="photo_search")]
    ])
    await update.message.reply_text("Choose search mode:", reply_markup=keyboard)
    return MODE

async def search_mode_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "brand_search":
        await query.edit_message_text("Select price range:", reply_markup=PRICE_KEYBOARD)
        return PRICE
    elif query.data == "photo_search":
        await query.edit_message_text("Send the brand name for the image search:")
        return PHOTO_BRAND

async def photo_brand_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["photo_brand"] = update.message.text
    await update.message.reply_text("Now send me a photo of the item.")
    return PHOTO_UPLOAD


def is_recent(item):
    time_iso = item.get("photo_highlight", {}).get("created_at", "")
    try:
        dt = datetime.fromisoformat(time_iso.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) - dt <= timedelta(hours=1)
    except:
        return False

def download_image(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        img_bytes = BytesIO(response.content)
        img = Image.open(img_bytes).convert("RGB")
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    except:
        return None

def calculate_similarity(img1, img2):
    try:
        orb = cv2.ORB_create()
        kp1, des1 = orb.detectAndCompute(img1, None)
        kp2, des2 = orb.detectAndCompute(img2, None)

        if des1 is None or des2 is None:
            return 0

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        return len(matches)
    except:
        return 0

async def photo_uploaded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    img_bytes = await photo_file.download_as_bytearray()
    nparr = np.frombuffer(img_bytes, np.uint8)
    uploaded_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    brand = context.user_data.get("photo_brand")
    filters = {"keywords": brand, "price": "0-150"}
    items = await asyncio.to_thread(search_vinted, filters)
    items = [item for item in items if is_recent(item)]

    similarities = []
    for item in items:
        image_url = item.get("photo", {}).get("url") or item.get("photo_thumb_url")
        vinted_img = download_image(image_url)
        if vinted_img is not None:
            score = calculate_similarity(uploaded_img, vinted_img)
            similarities.append((score, item))

    similarities.sort(reverse=True, key=lambda x: x[0])
    top_matches = similarities[:3]

    if not top_matches:
        await update.message.reply_text("❌ Ничего похожего не найдено.")
    else:
        for score, item in top_matches:
            msg = f"{item.get('title')}\nPrice: {item.get('price')}\n{item.get('url')}"
            await update.message.reply_text(msg)


async def price_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["price"] = query.data
    await query.edit_message_text("Now enter up to 5 brands, separated by commas (e.g., Nike, Adidas):")
    return BRAND


async def brand_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    global user_chat_id, user_filters, latest_ids
    brands = generate_brand_filter_list(update.message.text)
    if len(brands) > 5:
        await update.message.reply_text("❗️Максимум 5 брендов. Попробуй снова.")
        return BRAND

    user_chat_id = update.message.chat_id
    user_filters = {
        "brands": brands,
        "price": context.user_data["price"]
    }
    latest_ids = set()
    await update.message.reply_text("✅ Мониторинг начался. Обновления будут приходить каждые 60 секунд.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelled")
    return ConversationHandler.END


async def main():
    application = ApplicationBuilder().token(TG_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MODE: [CallbackQueryHandler(search_mode_chosen)],
            PRICE: [CallbackQueryHandler(price_chosen)],
            BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, brand_received)],
            PHOTO_BRAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, photo_brand_received)],
            PHOTO_UPLOAD: [MessageHandler(filters.PHOTO, photo_uploaded)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    application.add_handler(conv)

    application.job_queue.run_repeating(
        lambda ctx: asyncio.create_task(poll_vinted(application)),
        interval=60,
        first=1
    )

    await application.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    import asyncio

    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
