
import os
import asyncio
from pathlib import Path

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

MAIN_BUTTON = "🎄 Новогодняя & Рождественская фотосессия"
MAIN_BUTTONS = [MAIN_BUTTON, "📸 Студийная фотосессия", "🌿 Уличная фотосессия"]
AUDIENCES = ["Женская", "Мужская", "Детская", "Семейная"]
DIRECTIONS = dict(zip(MAIN_BUTTONS, ["new_year", "studio", "outdoor"]))
DIRECTION_LABELS = dict(zip(MAIN_BUTTONS, ["🎄 Новогодняя & Рождественская фотосессия", "📸 Студийная фотосессия", "🌿 Уличная фотосессия"]))
AUDIENCE_DIRS = dict(zip(AUDIENCES, ["female", "male", "child", "family"]))
ORDER_BUTTON = "💌 Заказать"
BACK_BUTTON = "⬅️ Назад"
HOME_BUTTON = "🏠 Главное меню"

ADMIN_ID = int(os.environ.get("TELEGRAM_ADMIN_ID", "0"))

BASE_FOLDER = Path(__file__).resolve().parent

NUMBERED_FOLDER = BASE_FOLDER / "numbered_photos"


def make_keyboard(buttons, columns=1):
    rows = [
        buttons[i:i + columns]
        for i in range(0, len(buttons), columns)
    ]
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
    )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    await update.message.reply_text(
        "🤍 Добро пожаловать в "
        "Alina Kravtsova | AI Studio!\n\n"
        "✨ Выберите понравившуюся фотосессию!",
        reply_markup=make_keyboard(MAIN_BUTTONS),
    )


async def myid(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        f"Ваш Telegram ID: {update.effective_user.id}"
    )


def catalog_paths(direction, audience):
    # Готовые новогодние женский и мужской каталоги уже лежат
    # непосредственно в numbered_photos/female и numbered_photos/male.
    if direction == MAIN_BUTTON:
        folder = NUMBERED_FOLDER / AUDIENCE_DIRS[audience]
    else:
        # Для студийного и уличного направлений используем отдельные папки.
        folder = NUMBERED_FOLDER / DIRECTIONS[direction] / AUDIENCE_DIRS[audience]

    paths = [folder / f"{n:02d}.jpg" for n in range(1, 10)]
    return paths if all(path.is_file() for path in paths) else []


async def show_audiences(message, context):
    direction = context.user_data["direction"]
    context.user_data.clear()
    context.user_data.update(direction=direction, page="audience")
    await message.reply_text(
        f"{DIRECTION_LABELS[direction]}\n\n✨ Для кого хотите создать фотосессию?",
        reply_markup=ReplyKeyboardMarkup(
            [AUDIENCES[:2], AUDIENCES[2:], [HOME_BUTTON]],
            resize_keyboard=True,
        ),
    )


async def show_catalog(message, context):  
    paths = catalog_paths(context.user_data["direction"], context.user_data["audience"])
    if not paths:
        return
    context.user_data["page"] = "choose_style"
    context.user_data.pop("order_photos", None)
    context.user_data.pop("selected_style", None)

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

    numbers = [
        f"{number:02d}"
        for number in range(1, 10)
    ]

    await message.reply_text(
        "🤍 Выберите студию по номеру:",
        reply_markup=make_keyboard(
            numbers + [BACK_BUTTON, HOME_BUTTON],
            columns=3,
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

    if text in MAIN_BUTTONS:
        context.user_data.clear()
        context.user_data["direction"] = text
        await show_audiences(message, context)
        return

    page = context.user_data.get("page")
    if text in AUDIENCES and page == "audience":
        context.user_data["audience"] = text
        await show_catalog(message, context)
        return

    if text == BACK_BUTTON:
        if page == "catalog":
            await show_audiences(message, context)
        elif page == "choose_style":
            await show_catalog(message, context)
        elif page == "order_pending":
            context.user_data.pop("order_photos", None)
            context.user_data["page"] = "catalog"
            await show_catalog(message, context)
        else:
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
                f"📂 Направление: {DIRECTION_LABELS[context.user_data['direction']]}\n"
                f"Категория: {context.user_data['audience']}\n"
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
            reply_markup=make_keyboard(MAIN_BUTTONS),
        )
        return
    if text == ORDER_BUTTON and page == "catalog":
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
            "📸 Теперь отправьте фотографии, которые хотите использовать для фотосессии.\n"
            "Можно отправить несколько фотографий.",
            reply_markup=make_keyboard([BACK_BUTTON, HOME_BUTTON]),
        )
        return

    await message.reply_text(
        "🤍 Выберите пункт меню.",
        reply_markup=make_keyboard(MAIN_BUTTONS),
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
        f"📸 Фотография получена! Всего: {len(photos)}.\n"
        "Можете отправить ещё фотографии. Заказ автоматически отправится через 10 секунд после последней."
    )

    context.user_data["finish_task"] = asyncio.create_task(
        finish_order_after_delay(context, update)
    )
async def finish_order_after_delay(context, update):
    await asyncio.sleep(10)

    if context.user_data.get("finish_task") is not asyncio.current_task():
        return    

    photos = context.user_data.get("order_photos", [])
    if not photos:
        return

    user = update.effective_user
    username = f"@{user.username}" if user.username else "Не указан"
    style = context.user_data.get("selected_style")

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            "💌 НОВЫЙ ЗАКАЗ!\n\n"
            f"📂 Направление: {DIRECTION_LABELS[context.user_data['direction']]}\n"
            f"Категория: {context.user_data['audience']}\n"
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

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="💌 Спасибо! Ваш заказ отправлен.\nМы свяжемся с вами в Telegram.",
        reply_markup=make_keyboard(MAIN_BUTTONS),
    )
def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "Не найден TELEGRAM_BOT_TOKEN"
        )

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
