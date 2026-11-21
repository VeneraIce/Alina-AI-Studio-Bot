
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InputMediaPhoto,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

MAIN_BUTTON = "🎄 Новогодняя фотосессия"
ORDER_BUTTON = "💌 Заказать"
BACK_BUTTON = "⬅️ Назад"
HOME_BUTTON = "🏠 Главное меню"

ADMIN_ID = int(os.environ.get("TELEGRAM_ADMIN_ID", "0"))

BASE_FOLDER = Path(__file__).resolve().parent

PHOTO_FOLDER = (
    BASE_FOLDER
    / "catalog"
    / "Новогодние_фотосессии_каталог"
    / "Фотографии"
)

NUMBERED_FOLDER = BASE_FOLDER / "numbered_photos"

# Старые номера утверждённых фотографий
SELECTED_PHOTOS = [
    "01", "02", "03", "05", "06",
    "08", "10", "12", "16",
]


def make_keyboard(buttons, columns=1):
    rows = [
        buttons[i:i + columns]
        for i in range(0, len(buttons), columns)
    ]
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
    )


def prepare_photos():
    NUMBERED_FOLDER.mkdir(exist_ok=True)
    prepared = []

    for new_number, old_number in enumerate(
        SELECTED_PHOTOS, start=1
    ):
        matches = sorted(
            PHOTO_FOLDER.glob(f"{old_number}_*.jpg")
        )

        if not matches:
            raise FileNotFoundError(
                f"Не найдена фотография {old_number}"
            )

        destination = (
            NUMBERED_FOLDER / f"{new_number:02d}.jpg"
        )

        with Image.open(matches[0]) as original:
            picture = original.convert("RGB")
            picture.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            picture = picture.copy()
            width, height = picture.size
            label = f"{new_number:02d}"

            font_size = max(32, width // 18)

            font_paths = [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ]

            font = ImageFont.load_default()

            for font_path in font_paths:
                if Path(font_path).exists():
                    font = ImageFont.truetype(
                        font_path, font_size
                    )
                    break

            draw = ImageDraw.Draw(
                picture, "RGBA"
            )

            padding = max(12, width // 55)
            margin = max(16, width // 45)

            bounds = draw.textbbox(
                (0, 0), label, font=font
            )

            text_width = bounds[2] - bounds[0]
            text_height = bounds[3] - bounds[1]

            box_width = text_width + padding * 2
            box_height = text_height + padding * 2

            x = width - margin - box_width
            y = height - margin - box_height

            draw.rounded_rectangle(
                (
                    x, y,
                    x + box_width,
                    y + box_height,
                ),
                radius=padding,
                fill=(20, 20, 20, 145),
            )

            draw.text(
                (x + padding, y + padding - bounds[1]),
                label,
                font=font,
                fill=(255, 255, 255, 255),
            )

            picture.save(
                destination,
                "JPEG",
                quality=92,
            )

        prepared.append(destination)

    return prepared


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    await update.message.reply_text(
        "🤍 Добро пожаловать в "
        "Alina Kravtsova | AI Studio!\n\n"
        "✨ Выберите понравившуюся фотосессию!",
        reply_markup=make_keyboard([MAIN_BUTTON]),
    )


async def myid(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        f"Ваш Telegram ID: {update.effective_user.id}"
    )


async def show_catalog(message, context):
    context.user_data["page"] = "catalog"

    paths = context.application.bot_data["photos"]

    files = [path.open("rb") for path in paths]

    try:
        media = [
            InputMediaPhoto(media=photo)
            for photo in files
        ]

        await message.reply_media_group(media=media)

    finally:
        for photo in files:
            photo.close()

    await message.reply_text(
        "🤍 Выберите студию по номеру.",
        reply_markup=make_keyboard(
            [ORDER_BUTTON, BACK_BUTTON, HOME_BUTTON]
        ),
    )


async def messages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.message
    text = message.text or ""

    if text == HOME_BUTTON:
        await start(update, context)
        return

    if text == MAIN_BUTTON:
        await show_catalog(message, context)
        return

    if text == BACK_BUTTON:
        await start(update, context)
        return
    if text == "Готово" and context.user_data.get("page") == "order_pending":
        photos = context.user_data.get("order_photos", [])
        style = context.user_data.get("selected_style")

        if not photos:
            await message.reply_text(
                "📸 Сначала отправьте хотя бы одну фотографию."
            )
            return

        if not ADMIN_ID:
            await message.reply_text(
                "Не удалось отправить заказ. Попробуйте позже."
            )
            return

        user = update.effective_user
        username = f"@{user.username}" if user.username else "Не указан"

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "💌 НОВЫЙ ЗАКАЗ!\n\n"
                f"🎄 Студия: {style}\n"
                f"👤 Клиент: {user.full_name}\n"
                f"🔗 Telegram: {username}\n"
                f"🆔 ID клиента: {user.id}\n"
                f"📸 Фотографий: {len(photos)}"
            ),
        )

        for photo_id in photos:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=photo_id,
            )

        context.user_data.clear()

        await message.reply_text(
            "🤍 Спасибо! Ваш заказ отправлен.\n"
            "Мы свяжемся с вами в Telegram.",
            reply_markup=make_keyboard([MAIN_BUTTON]),
        )
        return
    if text == ORDER_BUTTON:
        context.user_data["page"] = "choose_style"

        numbers = [
            f"{number:02d}"
            for number in range(1, 10)
        ]

        await message.reply_text(
            "💌 Какую студию выбираете?",
            reply_markup=make_keyboard(
                numbers + [BACK_BUTTON, HOME_BUTTON],
                columns=3,
            ),
        )
        return

    if (
        context.user_data.get("page") == "choose_style"
        and text in [
            f"{number:02d}"
            for number in range(1, 10)
        ]
    ):
        context.user_data["selected_style"] = text
        context.user_data["page"] = "order_pending"

        await message.reply_text(
            f"🤍 Вы выбрали студию {text}.\n\n"
            "📸 Теперь отправьте фотографии, "
            "которые хотите использовать для фотосессии.\n\n"
            "Можно отправить несколько фотографий. "
            "Когда закончите, напишите «Готово».",
            reply_markup=make_keyboard(
                ["Готово", BACK_BUTTON, HOME_BUTTON]
            ),
        )        
        return

    await message.reply_text(
        "🤍 Выберите пункт меню.",
        reply_markup=make_keyboard([MAIN_BUTTON]),
    )

async def receive_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if context.user_data.get("page") != "order_pending":
        return

    photos = context.user_data.setdefault("order_photos", [])
    photos.append(update.message.photo[-1].file_id)

    await update.message.reply_text(
        f"📸 Фотография получена! Всего: {len(photos)}.\n\n"
        "Отправьте следующую или нажмите «Готово»."
    )
def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "Не найден TELEGRAM_BOT_TOKEN"
        )

    photos = [
        NUMBERED_FOLDER / f"{number:02d}.jpg"
        for number in range(1, 10)
    ]

    app = (
        Application.builder()
        .token(token)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .get_updates_connect_timeout(30)
        .get_updates_read_timeout(30)
        .build()
    )

    app.bot_data["photos"] = photos

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("myid", myid)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            messages,
        )
    )
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receive_photo,
        )
    )
    print("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
