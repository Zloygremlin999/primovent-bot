import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils import executor
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен из переменной окружения
API_TOKEN = os.getenv('API_TOKEN')
if not API_TOKEN:
    logger.error("API_TOKEN не установлен! Пожалуйста, добавьте его в переменные окружения.")
    exit(1)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Главное меню
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(
    KeyboardButton("🏠 Головна"),
    KeyboardButton("🛒 Каталог")
)
main_menu.add(
    KeyboardButton("📝 Про нас"),
    KeyboardButton("📞 Контакти")
)
main_menu.add(
    KeyboardButton("🛠 Послуги"),
    KeyboardButton("💬 Відгуки")
)
main_menu.add(
    KeyboardButton("📰 Новини"),
    KeyboardButton("❓ Допомога")
)
main_menu.add(
    KeyboardButton("📦 Кошик")
)

# Категории каталога
catalog_menu = InlineKeyboardMarkup(row_width=2)
catalog_menu.add(
    InlineKeyboardButton("Кондиціонери ❄️", callback_data='category_air_conditioners'),
    InlineKeyboardButton("Вентиляція 💨", callback_data='category_ventilation'),
    InlineKeyboardButton("Опалення 🔥", callback_data='category_heating'),
    InlineKeyboardButton("Зволожувачі 💧", callback_data='category_humidifiers'),
    InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')
)

# Товары
products = {
    'category_air_conditioners': [
        {"name": "Кондиціонер General ECO RANGE ASHG09KPCA/AOHG09KPCA", "price": "25 000 грн", "callback_data": "add_general_eco"},
        {"name": "Кондиціонер LG Standard Plus PC09SQ", "price": "15 000 грн", "callback_data": "add_lg_pc09sq"},
        {"name": "Кондиціонер Daikin FTXB20C/RXB20C", "price": "18 500 грн", "callback_data": "add_daikin_ftxb20c"},
    ],
    'category_ventilation': [
        {"name": "ВЕНТС ВУТ 300-1 ВГ ЕС", "price": "63 000 грн", "callback_data": "add_vents_vut300"},
        {"name": "ВЕНТС ВУТ 2000 Г", "price": "87 500 грн", "callback_data": "add_vents_vut2000"},
    ]
}

# Корзина пользователя
user_cart = {}

# Шаги для FSM (Finite State Machine) для сбора контактных данных
class CheckoutSteps(StatesGroup):
    waiting_for_contact_info = State()
    waiting_for_confirmation = State()

# Функция для добавления товаров в корзину
def add_to_cart(user_id, item):
    if user_id not in user_cart:
        user_cart[user_id] = []
    user_cart[user_id].append(item)

# Команда старт
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Вітаємо в компанії «Пріма Вент»! Оберіть розділ:", reply_markup=main_menu)

@dp.message_handler(Text(equals="🏠 Головна"))
async def show_home(message: types.Message):
    await message.answer("Вітаємо! Оберіть розділ:", reply_markup=main_menu)

@dp.message_handler(Text(equals="🛒 Каталог"))
async def show_catalog(message: types.Message):
    await message.answer("Оберіть категорію товарів:", reply_markup=catalog_menu)

@dp.message_handler(Text(equals="📦 Кошик"))
async def view_cart(message: types.Message):
    user_id = message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if cart_items:
        cart_text = "\n".join([f"- {item['name']} ({item['price']})" for item in cart_items])
        await message.answer(f"🛒 **Ваш кошик**:\n{cart_text}\n\nДля оформлення замовлення натисніть «Оформити замовлення».", parse_mode='Markdown')
        await message.answer("🛍 Оформити замовлення")
    else:
        await message.answer("Ваш кошик порожній.")

@dp.message_handler(Text(equals="🛍 Оформити замовлення"))
async def checkout(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    cart_items = user_cart.get(user_id, [])
    if cart_items:
        cart_text = "\n".join([f"- {item['name']} ({item['price']})" for item in cart_items])
        await message.answer(f"Підтвердіть ваше замовлення:\n{cart_text}\n\nВведіть ваші контактні дані (телефон або email) для зв'язку:")
        await CheckoutSteps.waiting_for_contact_info.set()
    else:
        await message.answer("Ваш кошик порожній.")

@dp.message_handler(state=CheckoutSteps.waiting_for_contact_info, content_types=types.ContentTypes.TEXT)
async def get_contact_info(message: types.Message, state: FSMContext):
    contact_info = message.text
    await state.update_data(contact_info=contact_info)
    
    await message.answer("Підтвердіть замовлення. Натисніть «Підтвердити» для завершення замовлення.", reply_markup=InlineKeyboardMarkup().add(
        InlineKeyboardButton("Підтвердити", callback_data='confirm_order'),
        InlineKeyboardButton("Скасувати", callback_data='cancel_order')
    ))
    await CheckoutSteps.waiting_for_confirmation.set()

@dp.callback_query_handler(Text(equals='confirm_order'), state=CheckoutSteps.waiting_for_confirmation)
async def confirm_order_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    contact_info = user_data.get("contact_info")
    await bot.send_message(callback_query.from_user.id, f"Ваше замовлення підтверджено! Контакт: {contact_info}. Дякуємо за покупку!")
    user_cart[callback_query.from_user.id] = []  # Очистка корзины
    await state.finish()

# Обработчик категорий каталога
@dp.callback_query_handler(lambda c: c.data.startswith('category_'))
async def show_products(callback_query: types.CallbackQuery):
    category = callback_query.data
    items = products.get(category, [])
    if items:
        product_menu = InlineKeyboardMarkup(row_width=1)
        for item in items:
            product_button = InlineKeyboardButton(f"{item['name']} — {item['price']}", callback_data=item["callback_data"])
            product_menu.add(product_button)
        product_menu.add(InlineKeyboardButton("🔙 Назад", callback_data='back_to_catalog'))
        await bot.send_message(callback_query.from_user.id, "Оберіть товар:", reply_markup=product_menu)
    else:
        await bot.send_message(callback_query.from_user.id, "Товари в цій категорії відсутні.", reply_markup=catalog_menu)

@dp.callback_query_handler(lambda c: c.data.startswith('add_'))
async def add_to_cart_handler(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    product_code = callback_query.data[4:]
    item = next(
        (item for items in products.values() for item in items if item["callback_data"] == f"add_{product_code}"),
        None
    )
    if item:
        add_to_cart(user_id, item)
        await callback_query.answer(f"«{item['name']}» додано до кошика.")
    else:
        await callback_query.answer("Товар не знайдено.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)