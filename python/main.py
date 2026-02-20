from telethon import TelegramClient, events, types, Button
from datetime import datetime, timezone, timedelta
import telebot as tb  # Создаем алиас
import asyncio
import random
import aiohttp
import time
import json
import os
import logging
import re
import requests
import threading
import data_handler
import admin

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Настройки логирования
LOG_ALL_MESSAGES = True  # Логировать все сообщения
LOG_DICE_EVENTS = True   # Логировать dice события

# Класс менеджера таймера
class TimerManager:
    def __init__(self):
        self.is_running = True
        self.start_time = time.time()
        self.remaining_time = 3600  # начальное время в секундах
        self.timer_task = None

    async def start_timer(self):
        self.timer_task = asyncio.create_task(self._check_timer())

    async def _check_timer(self):
        while self.is_running:
            elapsed = time.time() - self.start_time
            if elapsed >= self.remaining_time:
                self.is_running = False
                print('Время работы бота истекло. Остановка...')
                break
            await asyncio.sleep(1)

    def set_new_time(self, new_time):
        elapsed = time.time() - self.start_time
        self.remaining_time = new_time + (self.remaining_time - elapsed)
        self.start_time = time.time()

    def get_remaining_time(self):
        if not self.is_running:
            return 0
        elapsed = time.time() - self.start_time
        return max(0, self.remaining_time - elapsed)

    def format_time(self):
        remaining = self.get_remaining_time()
        h = int(remaining // 3600)
        m = int((remaining % 3600) // 60)
        s = int(remaining % 60)
        return f"{h} ч {m} мин {s} сек"

# Создаем экземпляр менеджера
timer_manager = TimerManager()

# Ваши учётные данные
api_id = 27056864
api_hash = '938810633f3dfb944b2cae141c0520c2'
bot_token = '8318160592:AAFW70-IjNWu2vv5rdqpF_DMRzyed4mva0E'

# Инициализация клиентов
bot = TelegramClient('bot_session', api_id, api_hash)
bot2 = tb.TeleBot(bot_token)  # Теперь используем алиас tb

# Конфигурация API
TELEGRAM_API_BASE = f'https://api.telegram.org/bot{bot_token}/'
REFUND_URL = f"{TELEGRAM_API_BASE}refundStarPayment"

BASE_URL = "https://api.cuplegend.ru:80"  # Единый базовый URL для CupLegend API

# Эндпоинты API
ENDPOINT_MY_SELF = "/app/myself/201%3AUDDkdHhcCO"
ENDPOINT_INVOICES_CREATE = "/invoices/create/201%3AUDDkdHhcCO/{amount}/{price}"
ENDPOINT_INVOICES_GET = "/invoices/get/201%3AUDDkdHhcCO/{invoice_code}"
ENDPOINT_CHECKS_CREATE = "/checks/create/201%3AUDDkdHhcCO/{amount}/{price}"

# Формируемые URL
CUPLEGEND_API_URL = f"{BASE_URL}{ENDPOINT_MY_SELF}"

# Прочие настройки
API_TOKEN = "201:UDDkdHhcCO"
CHAT_ID = -1002758838415  # ID вашего канала
BUSINESS_CONNECTION_ID = "QYf19Ac8UUmcDgAA8XqxGGmwtE4"  # Ваш ID подключения

# Настройки администраторов
ADMINS = [
    6403893359,    # ID первого админа
    1763784339,    # ID второго админа
]

# Настройки эмодзи
EMOJIS = {
    'medal': "<tg-emoji emoji-id=\"5474355475711562313\">🏅</tg-emoji>",
    'red': "<tg-emoji emoji-id=\"5019523782004441717\">🔴</tg-emoji>",
    'green': "<tg-emoji emoji-id=\"5021905410089550576\">🟢</tg-emoji>",
    'board': "<tg-emoji emoji-id=\"5197269100878907942\">📋</tg-emoji>",
    'hello': "<tg-emoji emoji-id=\"5472055112702629499\">👋</tg-emoji>",
    'warning': "<tg-emoji emoji-id=\"5462935376714802451\">⚠️</tg-emoji>"
}

# Функция получения эмодзи
def get_emoji(name):
    return EMOJIS.get(name, '')
        
# Функция проверки прав администратора
def is_admin(user_id):
    return user_id in ADMINS
    
# Функция создания inline-кнопки
def create_inline_button(text, callback_data, icon_id=None):
    button = Button.inline(text, data=callback_data)
    if icon_id:
        button.icon_custom_emoji_id = str(icon_id)
    return button

# Функция создания URL-кнопки
def create_url_button(text, url, icon_id=None):
    button = Button.url(text, url)
    if icon_id:
        button.icon_custom_emoji_id = str(icon_id)
    return button
    
# Функция для получения упоминания пользователя
def get_user_mention(user_id, first_name):
    return f'<a href="tg://user?id={user_id}">{user_info['first_name']}</a>'

# Настройки хранения данных
USER_DATA_FILE = 'user_data.json'

# Функция загрузки данных
def save_user_data(data):
    try:
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(
                data, 
                f, 
                ensure_ascii=False,
                indent=4,
                sort_keys=True
            )
    except IOError as e:
        logging.error(f"Ошибка записи в файл: {str(e)}")
    except TypeError as e:
        logging.error(f"Ошибка сериализации данных: {str(e)}")
    except Exception as e:
        logging.error(f"Неизвестная ошибка при сохранении: {str(e)}")
        
def load_user_data():
    try:
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def get_user_data(user_id):
    user_data = load_user_data()
    return user_data.get(str(user_id), {
        'gems': 0,
        'xp': 0,
        'click_count': 0,
        'first_name': 'Неизвестный пользователь',
        'spin_count': 0,
        'stars': 0
    })

# Функция обновления данных пользователя
async def update_user_data(source, **kwargs):
    try:
        # Определяем user_id и first_name в зависимости от источника
        if hasattr(source, 'sender_id'):  # Telethon
            user_id = str(source.sender_id)
            # Получаем имя через более надёжный способ
            first_name = await get_user_first_name(source.sender_id)
        elif hasattr(source, 'chat'):  # TeleBot
            user_id = str(source.chat.id)
            first_name = getattr(source.from_user, 'first_name', 'Неизвестный пользователь')
        else:
            raise ValueError("Неизвестный источник данных")

        # Если first_name пустое, используем запасной вариант
        if not first_name:
            first_name = 'Неизвестный пользователь'

        # Загружаем текущие данные
        data = load_user_data()
        
        # Создаем или получаем данные пользователя
        user_info = data.get(user_id, {
            'gems': 0,
            'xp': 0,
            'click_count': 0,
            'first_name': first_name,
            'spin_count': 0,
            'stars': 0
        })
        
        # Обновляем first_name, если он пустой
        if not user_info['first_name']:
            user_info['first_name'] = first_name
        
        # Обновляем переданные параметры
        for key, value in kwargs.items():
            if key in ['gems', 'xp', 'click_count', 'first_name', 'spin_count', 'stars']:
                user_info[key] = value
        
        # Сохраняем изменения
        data[user_id] = user_info
        save_user_data(data)
        
    except Exception as e:
        logging.error(f"Ошибка при обновлении данных пользователя: {str(e)}")

# Дополнительная функция для получения имени пользователя
async def get_user_first_name(user_id):
    try:
        # Получаем информацию о пользователе
        user = await bot.get_entity(user_id)
        return user.first_name or 'Неизвестный пользователь'
    except Exception as e:
        logging.error(f"Ошибка при получении имени пользователя: {str(e)}")
        return 'Неизвестный пользователь'
        
# Функция добавления валюты
def add_currency(event, gems=0, xp=0, stars=0):
    try:
        user_id = event.sender_id
        user_info = get_user_data(user_id)
        
        # Обновляем значения с проверкой
        new_gems = user_info['gems'] + gems
        new_xp = user_info['xp'] + xp
        new_stars = user_info['stars'] + stars
        
        # Сохраняем все изменения
        update_user_data(
            event,
            gems=new_gems,
            xp=new_xp,
            stars=new_stars
        )
        
    except Exception as e:
        logging.error(f"Ошибка при добавлении валюты: {str(e)}")
        
# Функция обновления еженедельного прогресса
def update_user_progress(user_id, **kwargs):
    progress = load_user_progress()
    
    if user_id not in progress:
        progress[user_id] = {
            'startweek_click': 0,
            'currentweek_click': 0,
            'endweek_click': WEEKLY_TARGETS['clicks'],
            'startweek_gems': 0,
            'currentweek_gems': 0,
            'endweek_gems': WEEKLY_TARGETS['gems'],
            'startweek_xp': 0,
            'currentweek_xp': 0,
            'endweek_xp': WEEKLY_TARGETS['xp'],
            'last_click_time': 0,
            'click_cooldown': 120  # Кулдаун в секундах (2 минуты)
        }
    
    # Обновляем переданные параметры
    for key, value in kwargs.items():
        if key in progress[user_id]:
            progress[user_id][key] = value
    
    save_user_progress(progress)
        
def get_top_users(category, limit=10):
    try:
        # Допустимые категории для топа
        allowed_categories = ['gems', 'xp', 'click_count', 'spin_count', 'stars']
        
        if category not in allowed_categories:
            raise ValueError(f"Недопустимая категория: {category}")
            
        data = load_user_data()
        
        if not isinstance(data, dict) or not data:
            raise ValueError("Данные пользователей имеют некорректный формат или пустые")
            
        # Сортируем пользователей по выбранной категории
        sorted_users = sorted(
            data.items(),
            key=lambda x: x[1].get(category, 0),
            reverse=True
        )
        
        # Фильтруем только тех пользователей, у которых есть значение в категории
        filtered_users = [
            user for user in sorted_users 
            if user[1].get(category, 0) > 0 and user[1].get('first_name')
        ]
        
        # Возвращаем отфильтрованный список
        return filtered_users[:limit]
        
    except Exception as e:
        logging.error(f"Ошибка при получении топа: {str(e)}")
        return []

# Настройки клика
CLICK_COOLDOWN = 120  # Время между кликами в секундах (1 час)
CLICK_FILE = 'click_times.json'

# Функция форматирования времени в формат ЧЧ:ММ:СС
def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

# Функции работы с файлами для времени кликов
def load_click_times():
    try:
        with open(CLICK_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_click_times(data):
    with open(CLICK_FILE, 'w') as f:
        json.dump(data, f)

# Получаем время последнего клика пользователя
def get_last_click(user_id):
    click_times = load_click_times()
    return click_times.get(str(user_id), 0)

# Сохраняем время клика
def set_last_click(user_id, timestamp):
    click_times = load_click_times()
    click_times[str(user_id)] = timestamp
    save_click_times(click_times)

# Функция проверки возможности клика
def can_click(user_id):
    current_time = time.time()
    last_click = get_last_click(user_id)
    return current_time - last_click >= CLICK_COOLDOWN

# Функция обновления времени клика
def update_click_time(user_id):
    set_last_click(user_id, time.time())
    
# Файл для хранения активности пользователей
MAU_FILE = 'user_activity.json'

def load_mau_data():
    try:
        with open(MAU_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_mau_data(data):
    with open(MAU_FILE, 'w') as f:
        json.dump(data, f)

def update_user_activity(user_id):
    activity_data = load_mau_data()
    activity_data[str(user_id)] = int(time.time())
    save_mau_data(activity_data)

def get_mau():
    activity_data = load_mau_data()
    current_time = int(time.time())
    thirty_days_ago = current_time - (30 * 24 * 60 * 60)
    active_users = 0
    for timestamp in activity_data.values():
        if timestamp >= thirty_days_ago:
            active_users += 1
    return active_users

# Функция обновления MAU в мониторинге
def update_monitoring_mau():
    monitoring_data = load_data()  # Используем общую функцию загрузки
    monitoring_data["monitoring_mau"] = get_mau()
    monitoring_data["last_updated"] = datetime.now().strftime("%d.%m.%Y в %H:%M:%S")
    save_data(monitoring_data)  # Используем общую функцию сохранения
    
# Функции загрузки/сохранения данных
def load_data(filename="monitoring_data.json"):
    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print(f"Файл {filename} не найден. Создаётся пустой словарь.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Ошибка декодирования JSON: {e}")
        return {}

def save_data(data, filename="monitoring_data.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
    print(f"Данные успешно сохранены в {filename}")

# Список разрешенных chat_id для обработки
ALLOWED_CHATS = [
    -1003361985420,  # групповой чат
    1763784339,       # личный чат
    -1003059841629,   # групповой чат
    # Добавьте сюда ID чатов для gems и stars
]

# Настройки
WEEK_DURATION = 604800  # 7 дней в секундах
PROGRESS_FILE = 'weekprogress_file.json'
USER_PROGRESS_FILE = 'progressuser.json'
UTC_OFFSET = 7  # UTC+7

# Настройки для целей события
WEEKLY_TARGETS = {
    'clicks': 50,  # Целевое количество кликов
    'gems': 500,   # Целевое количество гемов
    'xp': 500      # Целевой опыт
}

# Функции работы с файлами
def load_weekly_timer():
    try:
        with open(PROGRESS_FILE, 'r') as f:
            data = json.load(f)
            return data.get('week_timer', None)
    except:
        return None

def save_weekly_timer(timestamp):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({'week_timer': timestamp}, f)

def load_user_progress():
    try:
        with open(USER_PROGRESS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_user_progress(data):
    with open(USER_PROGRESS_FILE, 'w') as f:
        json.dump(data, f)

# Функция расчета оставшегося времени для еженедельного события
def get_weekly_remaining_time():
    start_time = load_weekly_timer()
    if not start_time:
        return None
    
    current_time = time.time()
    end_time = start_time + WEEK_DURATION
    remaining = end_time - current_time
    
    if remaining <= 0:
        return None
    
    return remaining

# Функция форматирования времени
def format_datetime(dt):
    return dt.astimezone(timezone(timedelta(hours=UTC_OFFSET))).strftime('%d.%m.%YT%H:%M')

def format_time(seconds):
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{days} д {hours:02} ч {minutes:02} м {seconds:02} с"

# Проверка активного события
def is_weekly_event_active():
    start_time = load_weekly_timer()
    if not start_time:
        return False
    current_time = time.time()
    end_time = start_time + WEEK_DURATION
    return current_time < end_time

# Функция запуска события
def start_weekly_event():
    now = datetime.now(timezone(timedelta(hours=UTC_OFFSET)))
    current_weekday = now.weekday()
    days_to_monday = (7 - current_weekday) % 7
    next_monday = now + timedelta(days=days_to_monday)
    start_time = next_monday.replace(
        hour=21, 
        minute=0, 
        second=0, 
        microsecond=0
    )
    if now.hour >= 21:
        start_time += timedelta(weeks=1)
    
    # Обновляем цели для всех пользователей
    progress = load_user_progress()
    for user_id in progress:
        progress[user_id]['endweek_click'] = WEEKLY_TARGETS['clicks']
        progress[user_id]['endweek_gems'] = WEEKLY_TARGETS['gems']
        progress[user_id]['endweek_xp'] = WEEKLY_TARGETS['xp']
    save_user_progress(progress)
    
    save_weekly_timer(int(start_time.timestamp()))
    print(f"Событие запущено. Начало: {format_datetime(start_time)}")

# Каталог товаров
products = [
    {"idbuy": 1, "title": "test1", "amount": 1, "currency": "XTR"},
    {"idbuy": 2, "title": "test2", "amount": 1, "currency": "XTR"},
    {"idbuy": 3, "title": "test3", "amount": 1, "currency": "XTR"},
    {"idbuy": 4, "title": "test4", "amount": 1, "currency": "XTR"},
    {"idbuy": 5, "title": "test5", "amount": 1, "currency": "XTR"},
    {"idbuy": 6, "title": "test6", "amount": 1, "currency": "XTR"},
    {"idbuy": 7, "title": "test7", "amount": 1, "currency": "XTR"},
    {"idbuy": 8, "title": "test8", "amount": 1, "currency": "XTR"},
    {"idbuy": 9, "title": "test9", "amount": 1, "currency": "XTR"},
    {"idbuy": 10, "title": "test10", "amount": 1, "currency": "XTR"}
]

async def create_shop_keyboard(page_number):
    try:
        logging.info(f"Создание клавиатуры для страницы {page_number}")
        buttons = []
        start_index = (page_number - 1) * 9
        end_index = start_index + 9
        
        # Проверяем наличие товаров
        if not products:
            logging.warning("Список товаров пуст")
            return []
            
        # Проверяем корректность индексов
        if start_index >= len(products):
            logging.warning(f"Некорректный индекс: {start_index}")
            return []
            
        # Создаем кнопки товаров
        for i in range(start_index, min(end_index, len(products))):
            product = products[i]
            
            # Проверяем наличие необходимых полей
            if not all(key in product for key in ['idbuy', 'title', 'amount']):
                logging.warning(f"Неполный товар: {product}")
                continue
                
            buttons.append(
                Button.inline(
                    f"{product['title']} ({product['amount']} XTR)",
                    data=f"shop_buy{product['idbuy']}"
                )
            )
            
        # Проверяем, что кнопки созданы
        if not buttons:
            logging.warning("Кнопки не созданы")
            return []
            
        # Формируем сетку 3x3
        product_keyboard = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
        
        # Создаем навигацию
        navigation_buttons = []
        total_pages = (len(products) + 8) // 9
        
        if page_number > 1:
            navigation_buttons.append(Button.inline("⬅️", data=f"shop_page{page_number-1}"))
            
        # Заменяем Button.text на Button.inline
        navigation_buttons.append(Button.inline(
            f"{page_number}/{total_pages}", 
            data="page_info"  # Добавляем data для корректной работы
        ))
            
        if page_number < total_pages:
            navigation_buttons.append(Button.inline("➡️", data=f"shop_page{page_number+1}"))
            
        # Объединяем клавиатуру
        keyboard = product_keyboard + [navigation_buttons]
        
        logging.info(f"Создана клавиатура: {keyboard}")
        return keyboard
        
    except Exception as e:
        logging.error(f"Ошибка при создании клавиатуры: {str(e)}")
        return []

# Константы для системы призов
SPIN_BONUS = 100  # Бонус за каждый спин

async def update_api_data():
    try:
        # Загружаем текущие данные мониторинга
        monitoring_data = load_data()
        
        async with aiohttp.ClientSession() as session:
            # Запрос к CupLegend
            async with session.get(CUPLEGEND_API_URL) as response:
                cup_data = await response.json()
                monitoring_data["monitoring_bank_gems"] = cup_data.get("balance", 0)
                print(f"Данные CupLegend: {cup_data}")
                
            # Запрос к Telegram Stars
            async with session.get(
                f"{TELEGRAM_API_BASE}getBusinessAccountStarBalance",
                params={"business_connection_id": BUSINESS_CONNECTION_ID}
            ) as response:
                stars_data = await response.json()
                print(f"Данные Stars: {stars_data}")
                monitoring_data["monitoring_bank_stars"] = stars_data.get("result", {}).get("amount", 0)
                
            # Обновляем время
            monitoring_data["last_updated"] = datetime.now().strftime("%d.%m.%Y в %H:%M:%S")
            
            # Сохраняем изменения
            save_data(monitoring_data)
            
    except Exception as e:
        logging.error(f"Ошибка при получении API данных: {str(e)}")
        
# Функция проверки интернет-соединения
async def check_internet_connection():
    try:
        # Попытка подключения к тестовому URL
        await bot.loop.run_in_executor(
            None, 
            lambda: requests.head('https://google.com', timeout=5)
        )
        return True
    except Exception as e:
        logging.error(f"Ошибка проверки соединения: {str(e)}")
        return False
        
# Функция для создания счета (POST запрос)
async def create_invoice(amount, price, username=None):
    try:
        url = BASE_URL + f"/invoices/create/{API_TOKEN}/{amount}/{price}"
        
        # Добавляем параметр username если он указан
        if username:
            url += f"?username={username}"
            
        async with aiohttp.ClientSession() as session:
            # Отправляем POST запрос
            async with session.post(url) as response:
                data = await response.json()
                
                if data.get("status_code") == 200:
                    # Сохраняем код счёта
                    invoice_code = data.get('code')
                    if not invoice_code:
                        logging.error("Не получен код счёта при создании")
                        return None
                        
                    # Добавляем код счёта в ответ
                    data['invoice_code'] = invoice_code
                    return data
                else:
                    logging.error(f"Ошибка создания счета: {data.get('msg')}")
                    return None
                    
    except Exception as e:
        logging.error(f"Ошибка при создании счета: {str(e)}")
        return None

# Функция для проверки статуса счета (GET запрос)
async def check_invoice(invoice_code):
    try:
        url = BASE_URL + f"/invoices/get/{API_TOKEN}/{invoice_code}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                
                if data.get("status_code") == 200:
                    return data
                else:
                    logging.error(f"Ошибка проверки счета: {data.get('msg')}")
                    return None
                    
    except Exception as e:
        logging.error(f"Ошибка при проверке счета: {str(e)}")
        return None

# Функция для создания чека (POST запрос)
async def create_check(amount, price, username=None):
    try:
        url = BASE_URL + f"/checks/create/{API_TOKEN}/{amount}/{price}"
        
        # Добавляем параметр username если он указан
        if username:
            url += f"?username={username}"
            
        async with aiohttp.ClientSession() as session:
            async with session.post(url) as response:
                data = await response.json()
                
                if data.get("status_code") == 200:
                    return data
                else:
                    logging.error(f"Ошибка создания чека: {data.get('msg')}")
                    return None
                    
    except Exception as e:
        logging.error(f"Ошибка при создании чека: {str(e)}")
        return None

# Хендлер /start
@bot.on(events.NewMessage(pattern=r'^/start$'))
async def start_handler(event):
    try:
        # Создаем кнопки
        buttons = [
            [
                create_inline_button("Главное меню", callback_data='main_menu'),
                create_inline_button("Профиль", callback_data='profile')
            ],
            [
                create_inline_button("Магазин", callback_data='shop')  # Возвращаем просто 'shop'
            ]
        ]
        
        welcome_message = (
            f"{get_emoji('hello')} Добро пожаловать в наш бот!\n\n"
            "Выберите действие:"
        )
        
        await event.reply(
            welcome_message,
            buttons=buttons,
            parse_mode='html'
        )
        
    except Exception as e:
        logging.error(f"Ошибка в /start: {str(e)}")
        await event.reply("Произошла ошибка при запуске бота")

# Обновляем профиль
@bot.on(events.NewMessage(pattern=r'^/profile$'))
async def profile_handler(event):
    try:
        user_id = event.sender_id
        user_info = get_user_data(user_id)
        
        # Создаем кнопки для профиля
        buttons = [
    [
        create_inline_button("Мои гемы", 'gems', icon_id=5413794461152978282),
        create_inline_button("Статистика", 'stats', icon_id=5413794461152978282)
    ],
    [
        create_inline_button("Назад", 'back', icon_id=5413794461152978282)
    ]
]
        
        await event.reply(
            f"{get_emoji('board')} Ваш профиль:\n"
            f"Гемы: {user_info['gems']} 💎\n"
            f"Опыт: {user_info['xp']} ⭐\n"
            f"Клики: {user_info['click_count']} 📊\n"
            f"Спины: {user_info['spin_count']} 🎰\n"
            f"Донат звёзды: {user_info['stars']} ⭐\n",
            buttons=buttons,  # Добавляем кнопки
            parse_mode='html'
        )
    except Exception as e:
        await event.reply(f"Произошла ошибка: {str(e)}")

# Хендлер /links
@bot.on(events.NewMessage(pattern=r'^/links$'))
async def links_handler(event):
    buttons = [
        [
            create_url_button(
                "Перейти в канал", 
                url='https://t.me/your_channel',
                icon_id=5413794461152978282
            ),
            create_url_button(
                "Сайт", 
                url='https://yoursite.com',
                icon_id=5413794461152978282
            )
        ]
    ]
    
    await event.reply(
        "Полезные ссылки:",
        buttons=buttons
    )

# Объединяем все в один обработчик callback-запросов (без функционала магазина)
@bot.on(events.CallbackQuery())
async def callback_handler(event):
    data = event.data.decode('utf-8')

    try:
        if data == 'main_menu':
            await event.answer('🏷 Переключение в главное меню...')


        elif data == 'profile':
            user_id = event.sender_id
            user_info = get_user_data(user_id)
            await event.answer(
                f'👥 Ваш профиль:\n'
                f'Гемы: {user_info["gems"]} 💎\n'
                f'Опыт: {user_info["xp"]} ⭐'
            )

        elif data == 'gems':
            try:
                user_id = event.sender_id
                user_info = get_user_data(user_id)

                if 'gems' in user_info and 'xp' in user_info and 'click_count' in user_info:
                    alert_text = (
                        f"🎯 Ваш баланс:\n\n"
                        f"💎 Гемы: {user_info['gems']}\n"
                        f"⭐ Опыт: {user_info['xp']}\n"
                        f"🎰 Спины: {user_info['spin_count']}\n"
                        f"⭐ Донат звёзды: {user_info['stars']}\n\n"
                        f"📊 Всего кликов: {user_info['click_count']}"
                    )
                    await event.answer(
                alert_text,
                alert=True
            )
                else:
                    await event.answer("Ошибка: данные пользователя не найдены")
            except Exception as e:
                await event.answer(f"Произошла ошибка: {str(e)}")

        elif data == 'stats':
            await event.answer('📊 Открываем статистику...')

        elif data == 'back':
            await event.answer('↩️ Возвращаемся назад...')

        # Новый блок: обработка прогресса события
        elif data == 'progress':
            try:
                user_id = event.sender_id
                user_info = get_user_data(user_id)
                progress = load_user_progress()

                if not user_info:
                    await event.answer("❌ Ваш профиль не найден в базе данных.", alert=True)
                    return

                # Получаем прогресс пользователя (если нет — инициализируем)
                if str(user_id) not in progress:
                    progress[str(user_id)] = {
                        'currentweek_click': 0,
                        'endweek_click': WEEKLY_TARGETS['clicks'],
                        'currentweek_gems': 0,
                        'endweek_gems': WEEKLY_TARGETS['gems'],
                        'currentweek_xp': 0,
                        'endweek_xp': WEEKLY_TARGETS['xp']
                    }
                    save_user_progress(progress)

                user_progress = progress[str(user_id)]

                # Расчёт процентов прогресса
                click_percent = int((user_progress['currentweek_click'] / user_progress['endweek_click']) * 100) if user_progress['endweek_click'] > 0 else 0
                gems_percent = int((user_progress['currentweek_gems'] / user_progress['endweek_gems']) * 100) if user_progress['endweek_gems'] > 0 else 0
                xp_percent = int((user_progress['currentweek_xp'] / user_progress['endweek_xp']) * 100) if user_progress['endweek_xp'] > 0 else 0

                first_name = user_info.get('first_name', str(user_id)).strip()

                # Формируем текст для alert (без прогресс‑баров и фото)
                alert_text = (
                    f"📊 Прогресс события для {first_name}\n\n"
                    f"🖱 Клики: {user_progress['currentweek_click']}/{user_progress['endweek_click']} ({click_percent}%)\n"
            f"💎 Гемы: {user_progress['currentweek_gems']}/{user_progress['endweek_gems']} ({gems_percent}%)\n"
            f"⭐ Опыт: {user_progress['currentweek_xp']}/{user_progress['endweek_xp']} ({xp_percent}%)"
                )

                await event.answer(
                    alert_text,
            alert=True
        )
            except Exception as e:
                await event.answer(f"Произошла ошибка при загрузке прогресса: {str(e)}", alert=True)

        else:
            await event.answer('❌ Неизвестная команда')

    except Exception as e:
        await event.answer(f'Произошла ошибка: {str(e)}')  

@bot.on(events.NewMessage(pattern=r'^/monitoring$'))
async def stats_handler(event):
    try:
        # Загружаем основные данные
        user_data = load_user_data()
        await update_api_data()
        monitoring_data = load_data()  # Обновляем данные после API запроса
        
        # Собираем все необходимые данные
        total_users = len(user_data)
        total_clicks = sum(user['click_count'] for user in user_data.values())
        total_gems = sum(user['gems'] for user in user_data.values())
        total_xp = sum(user['xp'] for user in user_data.values())
        
        # Формируем ответ по новому шаблону
        response = (
            "👁‍🗨 Статистика бота 👁‍🗨\n"
            f"<blockquote>👤 Игроков » <code>{total_users}</code>\n"
            f"  ⤷ MAU » <code>{monitoring_data.get('monitoring_mau', 0)}</code>\n\n"
            
            f"🖱️ Опыт » <code>{total_xp}</code>\n"
            f"  ⤷ Получено » <code>{monitoring_data['monitoring_xp']}</code>\n\n"
            
            f"⭐ Звезды » <code>{monitoring_data['monitoring_stars']}</code>\n"
            f"  ⤷ Пополнено » <code>{monitoring_data['monitoring_payed_stars']}</code>\n"
            f"  ⤷ Выведено » <code>{monitoring_data['monitoring_withdraw_stars']}</code>\n"
            f"  ⤷ В банке » <code>{monitoring_data['monitoring_bank_stars']}</code>\n\n"
            
            f"💎 Гемы » <code>{total_gems}</code>\n"
            f"  ⤷ Пополнено » <code>{monitoring_data['monitoring_payed_gems']}</code>\n"
            f"  ⤷ Выведено » <code>{monitoring_data['monitoring_withdraw_gems']}</code>\n"
            f"  ⤷ В банке » <code>{monitoring_data['monitoring_bank_gems']}</code>\n\n"
            
            f"🎰 Спины » <code>{monitoring_data['monitoring_spin_count']}</code>\n"
            f"  ⤷ Выиграно » <code>{monitoring_data['monitoring_win_spin_count']}</code>\n"
            f"  ⤷ Проиграно » <code>{monitoring_data['monitoring_lose_spin_count']}</code>\n</blockquote>\n"
            
            f"⏳ Статистика обновлена <code>{monitoring_data['last_updated']}</code>"
        )
        
        await event.reply(response, parse_mode='html')
        
    except Exception as e:
        await event.reply(f"Ошибка при сборе статистики: {str(e)}")
        
@bot.on(events.NewMessage(pattern=r'^/click_up$'))
async def click_up_handler(event):
    try:
        # Получаем user_id безопасным способом
        if hasattr(event, 'sender_id'):
            user_id = str(event.sender_id)
        elif hasattr(event, 'chat'):
            user_id = str(event.chat.id)
        else:
            raise ValueError("Не удалось определить user_id")

        # Загружаем данные прогресса события
        progress = load_user_progress()
        
        # Создаем начальные данные если их нет
        if user_id not in progress:
            progress[user_id] = {
                'startweek_click': 0,
                'currentweek_click': 0,
                'endweek_click': WEEKLY_TARGETS['clicks'],
                'startweek_gems': 0,
                'currentweek_gems': 0,
                'endweek_gems': WEEKLY_TARGETS['gems'],
                'startweek_xp': 0,
                'currentweek_xp': 0,
                'endweek_xp': WEEKLY_TARGETS['xp']
            }
            save_user_progress(progress)

        # Получаем текущие данные прогресса
        user_progress = progress[user_id]

        # Проверяем возможность клика
        if not can_click(user_id):
            last_click = get_last_click(user_id)
            time_left = CLICK_COOLDOWN - (time.time() - last_click)
            await event.reply(
                f"⏰ Подождите {format_time(time_left)} до следующего клика",
                parse_mode='html'
            )
            return

        # Генерируем награды
        gems_to_add = random.randint(1, 10)
        xp_to_add = random.randint(1, 10)
        user_data = get_user_data(user_id)
        new_click_count = user_data.get('click_count', 0) + 1
        
        # Обновляем данные пользователя
        await update_user_data(
            event,
            click_count=new_click_count,
            gems=user_data['gems'] + gems_to_add,
            xp=user_data['xp'] + xp_to_add
        )
        
        # Обновляем счетчики события
        user_progress['currentweek_click'] += 1
        user_progress['currentweek_gems'] += gems_to_add
        user_progress['currentweek_xp'] += xp_to_add
        
        # Обновляем мониторинг
        monitoring_data = load_data()
        monitoring_data["monitoring_click_count"] += 1
        monitoring_data["monitoring_gems"] += gems_to_add
        monitoring_data["monitoring_xp"] += xp_to_add
        monitoring_data["last_updated"] = datetime.now().strftime("%d.%m.%Y в %H:%M:%S")
        save_data(monitoring_data)
        
        # Сохраняем время клика
        current_time = time.time()
        user_progress['last_click_time'] = current_time
        save_user_progress(progress)
        set_last_click(user_id, current_time)

        await event.reply(
            f"🎉 Вы успешно получили {gems_to_add} гемсов!\n"
            f"Следующий клик доступен через {format_time(CLICK_COOLDOWN)}\n"
            f"Всего кликов: {new_click_count}\n"
            f"Прогресс события: {user_progress['currentweek_click']} кликов\n"
            f"Накоплено гемов в событии: {user_progress['currentweek_gems']}\n"
            f"Накоплено опыта в событии: {user_progress['currentweek_xp']}",
            parse_mode='html'
        )
    
    except Exception as e:
        logging.error(f"Ошибка в хендлере кликов: {str(e)}")
        await event.reply("Произошла ошибка при обработке клика", parse_mode='html')
        
# Обновляем MAU при клике
@bot.on(events.NewMessage(pattern=r'^/click_up$'))
async def click_up_handler(event):
    try:
        # [весь существующий код обработки клика]
        update_user_activity(event.sender_id)
        update_monitoring_mau()
        # [продолжение существующего кода]
    except Exception as e:
        logging.error(f"Ошибка при обработке клика: {str(e)}")

# Команда для ручного обновления MAU
@bot.on(events.NewMessage(pattern=r'^/update_mau$'))
async def update_mau_command(event):
    if is_admin(event.sender_id):
        update_monitoring_mau()
        await event.reply("MAU обновлено!")
    else:
        await event.reply("Доступ запрещен")

#Команда shop

# Обновляем справку в админ-панели
@bot.on(events.NewMessage(pattern=r'^/admin_panel$'))
async def admin_handler(event):
    if is_admin(event.sender_id):
        await event.reply(
            f"🎖 Добро пожаловать в админ-панель!\n\n"
            f"Доступные команды:\n"
            f"🎁 /add_gems <id> <количество> - добавить гемы\n"
            f"💸 /delete_gems <id> <количество> - списать гемы\n\n"
            f"📅 /startprogressweek - запустить еженедельное событие\n\n"
            f"Пример: /add_gems 1763784339 100",
            parse_mode='html'
        )
    else:
        await event.reply("⚠️ У вас нет прав доступа")
                
@bot.on(events.NewMessage(pattern=r'^/add_gems\s+(\d+)\s+(\d+)$'))
async def add_gems_handler(event):
    try:
        # Получаем параметры из сообщения
        match = event.pattern_match
        target_id = match.group(1)
        amount = match.group(2)
        
        # Проверяем права доступа
        if not is_admin(event.sender_id):
            await event.reply("🚫 Доступ запрещен")
            return
            
        # Преобразуем в числа
        try:
            target_id = int(target_id)
            amount = int(amount)
        except ValueError:
            await event.reply("❌ Неверный формат команды! Используйте: /add_gems <id> <количество>")
            return
            
        if amount <= 0:
            await event.reply("❌ Количество должно быть положительным!")
            return
            
        # Загружаем текущие данные
        data = load_user_data()
        target_id_str = str(target_id)
        
        # Получаем информацию о пользователе
        user_info = data.get(target_id_str, {
            'gems': 0,
            'xp': 0,
            'click_count': 0,
            'first_name': 'Неизвестный пользователь',
            'spin_count': 0,
            'stars': 0
        })
        
        # Обновляем гемы
        current_gems = user_info.get('gems', 0)
        new_gems = current_gems + amount
        user_info['gems'] = new_gems
        
        # Сохраняем изменения
        data[target_id_str] = user_info
        save_user_data(data)
        
        # Формируем ответ с упоминанием пользователя
        mention_link = f"tg://user?id={target_id}"
        formatted_name = f"<a href=\"{mention_link}\">{user_info['first_name']}</a>"
        
        await event.reply(
            f"{EMOJIS['green']} Добавлено {amount} 💎\n"  # Добавляем зеленый чекмарк
            f"Новый баланс: {new_gems} 💎\n"
            f"Пользователь: {formatted_name}",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"Ошибка при добавлении гемсов: {str(e)}")
        await event.reply(
            f"{EMOJIS['warning']} Ошибка обновления баланса!",
            parse_mode="HTML"
        )

@bot.on(events.NewMessage(pattern=r'^/delete_gems\s+(\d+)\s+(\d+)$'))
async def delete_gems_handler(event):
    try:
        # Получаем параметры из сообщения
        match = event.pattern_match
        target_id = match.group(1)
        amount = match.group(2)
        
        # Проверяем права доступа
        if not is_admin(event.sender_id):
            await event.reply("🚫 Доступ запрещен")
            return
            
        # Преобразуем в числа
        try:
            target_id = int(target_id)
            amount = int(amount)
        except ValueError:
            await event.reply("❌ Неверный формат команды! Используйте: /delete_gems <id> <количество>")
            return
            
        if amount <= 0:
            await event.reply("❌ Количество должно быть положительным!")
            return
            
        # Загружаем текущие данные
        data = load_user_data()
        target_id_str = str(target_id)
        
        # Проверяем существование пользователя
        if target_id_str not in data:
            await event.reply("❌ Пользователь не найден!")
            return
            
        # Получаем информацию о пользователе
        user_info = data[target_id_str]
        
        # Проверяем достаточно ли гемсов
        current_gems = user_info.get('gems', 0)
        if current_gems < amount:
            await event.reply(
                f"❌ Недостаточно гемсов для списания!\n"
                f"Текущий баланс: {current_gems} 💎"
            )
            return
            
        # Обновляем гемы
        new_gems = current_gems - amount
        user_info['gems'] = new_gems
        data[target_id_str] = user_info
        
        # Сохраняем изменения
        save_user_data(data)
        
        # Формируем ссылку на пользователя
        mention_link = f"tg://user?id={target_id}"
        formatted_name = f"<a href=\"{mention_link}\">{user_info['first_name']}</a>"
        
        await event.reply(
            f"{EMOJIS['red']} Списано {amount} 💎\n"  # Добавляем красный крестик
            f"Новый баланс: {new_gems} 💎\n"
            f"Пользователь: {formatted_name}",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logging.error(f"Ошибка при списании гемсов: {str(e)}")
        await event.reply(
            f"{EMOJIS['warning']} Ошибка обновления баланса!",
            parse_mode="HTML"
        )

# Функция проверки интернет-соединения с измерением пинга
async def check_internet_connection():
    hosts = ['google.com', 'yandex.ru', 'github.com']
    success_count = 0
    ping_results = {}
    
    for host in hosts:
        try:
            # Проверка доступности
            await bot.loop.run_in_executor(
                None, 
                lambda h=host: requests.head(f'https://{h}', timeout=3)
            )
            success_count += 1
            
            # Измерение пинга
            try:
                ping_output = os.popen(f'ping -c 3 {host}').read()
                if 'time=' in ping_output:
                    # Извлекаем все времена отклика
                    times = [float(line.split('time=')[1].split(' ms')[0]) 
                            for line in ping_output.split('\n') 
                            if 'time=' in line]
                    avg_ping = sum(times) / len(times) if times else 0
                    ping_results[host] = f"{avg_ping:.1f} мс"
                else:
                    ping_results[host] = "Не удалось измерить"
            except Exception as e:
                logging.error(f"Ошибка измерения пинга для {host}: {str(e)}")
                ping_results[host] = "Ошибка"
                
        except Exception as e:
            logging.error(f"Ошибка проверки {host}: {str(e)}")
            ping_results[host] = "Недоступно"
            continue
            
    return success_count > 0, ping_results

# Обновлённая команда проверки
@bot.on(events.NewMessage(pattern=r'^/check_connection$'))
async def connection_check(event):
    is_connected, pings = await check_internet_connection()
    
    if is_connected:
        ping_report = "\n".join([f"- {host}: {ping}" for host, ping in pings.items()])
        await event.reply(
            f"✅ Интернет-соединение стабильно\n"
            f"Результаты пинга:\n"
            f"{ping_report}"
        )
    else:
        await event.reply("❌ Проблемы с интернет-соединением")

@bot.on(events.NewMessage(chats=ALLOWED_CHATS))
async def handle_dice(event):
    try:
        formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not event.message.dice:
            return
        
        user = await event.get_sender()
        user_id = str(user.id)
        user_data = get_user_data(user_id)
        
        # Инициализация необходимых полей
        if 'spin_count' not in user_data:
            user_data['spin_count'] = 0
        if 'gems' not in user_data:
            user_data['gems'] = 0
        if 'xp' not in user_data:
            user_data['xp'] = 0
            
        spin_count = user_data['spin_count']
        mention_link = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
        
        dice_emoticon = event.message.dice.emoticon
        dice_value = event.message.dice.value
        
        # Загружаем данные мониторинга
        monitoring_data = load_data()
        
        if LOG_DICE_EVENTS:
            logging.info(f"DICE EVENT: Пользователь {user.id} ({mention_link}) выбросил {dice_value} (эмодзи: {dice_emoticon})")
        
        if dice_emoticon == '🎰':
            # Обновляем счётчики в мониторинге
            monitoring_data["monitoring_spin_count"] += 1
            monitoring_data["monitoring_lose_spin_count"] += 1  # Учитываем как проигрыш по умолчанию
            
            # Обновляем XP
            new_xp = user_data['xp'] + 1
            
            # Обновляем спин счётчик
            new_spin_count = spin_count + 1
            
            try:
                # Обновляем данные пользователя
                await update_user_data(event, spin_count=new_spin_count, xp=new_xp)
                
                updated_user_data = get_user_data(user_id)
                actual_spin_count = updated_user_data['spin_count']
                actual_xp = updated_user_data['xp']
                
                if actual_spin_count != new_spin_count or actual_xp != new_xp:
                    raise ValueError("Ошибка сохранения данных")
                    
                # Сохраняем изменения в мониторинге
                save_data(monitoring_data)
                
            except Exception as e:
                logging.error(f"Ошибка обновления данных: {str(e)}")
                await event.reply("Произошла ошибка при сохранении данных", parse_mode='html')
                return
            
            if dice_value == 64:
                try:
                    # Обновляем мониторинг выигрыша
                    monitoring_data["monitoring_win_spin_count"] += 1
                    monitoring_data["monitoring_lose_spin_count"] -= 1  # Корректируем проигрыш
                    
                    bonus = spin_count * SPIN_BONUS
                    total_prize = 100 + bonus
                    await asyncio.sleep(2)
                    
                    new_gems = user_data['gems'] + total_prize
                    
                    # Обновляем данные пользователя
                    await update_user_data(event, gems=new_gems, spin_count=0)
                    
                    # Сохраняем изменения в мониторинге
                    save_data(monitoring_data)
                    
                    winner_message = (
                        f"🎉 <b>Поздравляем победителя!</b>\n\n"
                        f"{mention_link}, Вы выиграли <b>{total_prize}</b> 💎! в 🎰\n\n"
                        f"Бонус за {spin_count} спинов: <b>{bonus}</b> 💎\n\n"
                        f"Спасибо за участие в розыгрыше!"
                    )
                    
                    with open('winners.txt', 'a', encoding='utf-8') as f:
                        f.write(
                            f"Ник TG: {user.first_name} | "
                            f"ID: {user.id} | "
                            f"Время выигрыша: {formatted_time} | "
                            f"Бонус: {bonus} | "
                            f"Всего: {total_prize}\n"
                        )
                    
                    await event.reply(winner_message, parse_mode='html')
                    logging.info(f"ВЫИГРЫШ! Пользователь {user.id} получил приз: {total_prize} 💎")
                
                except Exception as e:
                    logging.error(f"Ошибка при обработке выигрыша: {str(e)}")
                    await event.reply("Произошла ошибка при обработке выигрыша", parse_mode='html')

    except Exception as e:
        logging.error(f"Критическая ошибка в handle_dice: {str(e)}")
        await event.reply("Произошла непредвиденная ошибка", parse_mode='html')

# Пример использования в хендлере
@bot.on(events.NewMessage(pattern=r'^/top_gems$'))
async def show_gems_top(event):
    try:
        top_gems = get_top_users('gems', limit=10)
        
        if not top_gems:
            await event.reply("Топ пока пуст", parse_mode='html')
            return
            
        gems_text = []
        
        for i, (user_id, info) in enumerate(top_gems):
            first_name = info.get('first_name', 'Неизвестный пользователь')
            mention = f"<a href=\"tg://user?id={user_id}\">{first_name}</a>"
            gems_text.append(f"{i+1}. {mention}: <b>{info['gems']}</b> 💎")
            
        response = (
            "🏆 <b>Топ-10 по гемсам</b>\n\n" +
            "\n".join(gems_text)
        )
        await event.reply(response, parse_mode='html')
        
    except Exception as e:
        await event.reply(f"Произошла ошибка: {str(e)}", parse_mode='html')
        
# Пример использования в хендлере
@bot.on(events.NewMessage(pattern=r'^/top_xp$'))
async def show_xp_top(event):
    try:
        top_xp = get_top_users('xp', limit=10)
        
        if not top_xp:
            await event.reply("Топ пока пуст", parse_mode='html')
            return
            
        xp_text = []
        
        for i, (user_id, info) in enumerate(top_xp):
            first_name = info.get('first_name', 'Неизвестный пользователь')
            mention = f"<a href=\"tg://user?id={user_id}\">{first_name}</a>"
            xp_text.append(f"{i+1}. {mention}: <b>{info['xp']}</b> 👑")
            
        response = (
            "🏆 <b>Топ-10 по опыту</b>\n\n" +
            "\n".join(xp_text)
        )
        await event.reply(response, parse_mode='html')
        
    except Exception as e:
        await event.reply(f"Произошла ошибка: {str(e)}", parse_mode='html')
        
# Пример использования в хендлере
@bot.on(events.NewMessage(pattern=r'^/top_clicks$'))
async def show_click_count_top(event):
    try:
        top_click_count = get_top_users('click_count', limit=10)
        
        if not top_click_count:
            await event.reply("Топ пока пуст", parse_mode='html')
            return
            
        click_count_text = []
        
        for i, (user_id, info) in enumerate(top_click_count):
            first_name = info.get('first_name', 'Неизвестный пользователь')
            mention = f"<a href=\"tg://user?id={user_id}\">{first_name}</a>"
            click_count_text.append(f"{i+1}. {mention}: <b>{info['click_count']}</b> 🖱️")
            
        response = (
            "🏆 <b>Топ-10 по кликам</b>\n\n" +
            "\n".join(click_count_text)
        )
        await event.reply(response, parse_mode='html')
        
    except Exception as e:
        await event.reply(f"Произошла ошибка: {str(e)}", parse_mode='html')
        
# Пример использования в хендлере
@bot.on(events.NewMessage(pattern=r'^/top_star_donate$'))
async def show_stars_top(event):
    try:
        top_stars = get_top_users('stars', limit=10)
        
        if not top_stars:
            await event.reply("Топ пока пуст", parse_mode='html')
            return
            
        stars_text = []
        
        for i, (user_id, info) in enumerate(top_stars):
            first_name = info.get('first_name', 'Неизвестный пользователь')
            mention = f"<a href=\"tg://user?id={user_id}\">{first_name}</a>"
            stars_text.append(f"{i+1}. {mention}: <b>{info['stars']}</b> ⭐")
            
        response = (
            "🏆 <b>Топ-10 по донату звёздам</b>\n\n" +
            "\n".join(stars_text)
        )
        await event.reply(response, parse_mode='html')
        
    except Exception as e:
        await event.reply(f"Произошла ошибка: {str(e)}", parse_mode='html')

# Основная команда для отображения списка доступных топов
@bot.on(events.NewMessage(pattern=r'^/top$'))
async def show_top_menu(event):
    try:
        response = (
            "Доступные топы:\n\n"
            "• /top_gems - Топ по гемсам\n"
            "• /top_xp - Топ по опыту\n"
            "• /top_clicks - Топ по кликам\n"
            "• /top_star_donate - Топ по донату звёзд"
        )
        await event.reply(response)
    except Exception as e:
        await event.reply(f"Произошла ошибка: {str(e)}")

@bot.on(events.NewMessage(pattern=r'^/refund\s+(\d+)\s+(.+)$'))
async def handle_refund(event):
    try:
        # Получаем параметры из сообщения
        match = event.pattern_match
        user_id = match.group(1)
        payment_id = match.group(2)
        
        if not user_id or not payment_id:
            await event.reply("Используйте формат: /refund <user_id> <payment_id>")
            return
        
        async with aiohttp.ClientSession() as session:
            params = {
                'user_id': user_id,
                'telegram_payment_charge_id': payment_id
            }
            
            async with session.post(REFUND_URL, params=params) as response:
                data = await response.json()
                
                if data.get('ok'):
                    if data.get('result'):
                        await event.reply("Возврат выполнен успешно!")
                    else:
                        await event.reply("Ошибка при выполнении возврата")
                        
                else:
                    error_code = data.get('error_code')
                    description = data.get('description')
                    
                    if error_code == 400:
                        if 'CHARGE_ALREADY_REFUNDED' in description:
                            await event.reply("Этот платеж уже был возвращен")
                        elif 'CHARGE_ID_EMPTY' in description:
                            await event.reply("Неверный ID операции")
                        else:
                            await event.reply(f"Произошла ошибка: {description}")
                    else:
                        await event.reply("Произошла неизвестная ошибка")
                        
    except Exception as e:
        logging.error(f"Ошибка при возврате: {str(e)}")
        await event.reply("Произошла ошибка при обработке запроса")

# Команда запуска события
@bot.on(events.NewMessage(pattern=r'^/startprogressweek$'))
async def handle_start_event(event):
    if not is_admin(event.sender_id):
        await event.reply("🚫 Доступ запрещен", parse_mode='html')
        return
        
    if is_weekly_event_active():
        await event.reply("🔄 Событие уже активно!", parse_mode='html')
        return
        
    try:
        start_weekly_event()
        await event.reply("✅ Еженедельное событие запущено!", parse_mode='html')
    except Exception as e:
        logging.error(f"Ошибка при запуске события: {str(e)}")
        await event.reply("❌ Ошибка при запуске события", parse_mode='html')

# Команда проверки прогресса
@bot.on(events.NewMessage(pattern=r'^/progressweek$'))
async def show_progress(event):
    try:
        remaining = get_weekly_remaining_time()
        
        if not remaining:
            await event.reply("Событие не активно!", parse_mode='html')
            return
        
        user_id = str(event.sender_id)
        progress = load_user_progress()
        
        if user_id not in progress:
            progress[user_id] = {
                'startweek_click': 0,
                'currentweek_click': 0,
                'endweek_click': WEEKLY_TARGETS['clicks'],
                'startweek_gems': 0,
                'currentweek_gems': 0,
                'endweek_gems': WEEKLY_TARGETS['gems'],
                'startweek_xp': 0,
                'currentweek_xp': 0,
                'endweek_xp': WEEKLY_TARGETS['xp']
            }
            save_user_progress(progress)
        
        user_progress = progress[user_id]
        
        # Рассчитываем проценты
        click_percent = int((user_progress['currentweek_click'] / user_progress['endweek_click']) * 100) if user_progress['endweek_click'] > 0 else 0
        gems_percent = int((user_progress['currentweek_gems'] / user_progress['endweek_gems']) * 100) if user_progress['endweek_gems'] > 0 else 0
        xp_percent = int((user_progress['currentweek_xp'] / user_progress['endweek_xp']) * 100) if user_progress['endweek_xp'] > 0 else 0
        
        # Добавляем визуальные индикаторы
        click_bar = "█" * (click_percent // 10)  # 1 бар = 5%
        gems_bar = "█" * (gems_percent // 10)
        xp_bar = "█" * (xp_percent // 10)
        
        response = (
            f"⏰ До окончания события осталось: <b>{format_time(remaining)}</b>\n\n"
            f"📊 Ваш прогресс:\n"
            f"🖱 Клики: <b>{user_progress['currentweek_click']}/{user_progress['endweek_click']}</b> (<b>{click_percent}%</b>) | {click_bar}\n"
            f"💎 Гемы: <b>{user_progress['currentweek_gems']}/{user_progress['endweek_gems']}</b> (<b>{gems_percent}%</b>) | {gems_bar}\n"
            f"🎯 Опыт: <b>{user_progress['currentweek_xp']}/{user_progress['endweek_xp']}</b> (<b>{xp_percent}%</b>) | {xp_bar}\n\n"
            
            f"📅 Начало события: <i>{format_datetime(datetime.fromtimestamp(load_weekly_timer()))}</i>"
        )
        
        await event.reply(response, parse_mode='html')
    
    except Exception as e:
        logging.error(f"Ошибка при отображении прогресса: {str(e)}")
        await event.reply("❌ Произошла ошибка при получении данных", parse_mode='html')
        
@bot.on(events.NewMessage(pattern=r'^/help$'))
async def help_handler(event):
    try:
        help_message = (
            "🆔 Список доступных команд:\n\n"
            
            "• Основные команды:\n"
            "/start - запустить бота\n"
            "/profile - открыть профиль\n"
            "/links - полезные ссылки\n"
            "/help - показать список команд\n\n"
            
            "• Игровые команды:\n"
            "/click_up - получить награду\n"
            "/shop - открыть магазин\n\n"
            
            "• Статистика:\n"
            "/top - показать список топов\n"
            "/progressweek - проверить прогресс события\n\n"
            
            "• Админ-панель:\n"
            "/admin_panel - доступ к админ-функциям\n"
            "/add_gems <id> <кол-во> - добавить гемы\n"
            "/delete_gems <id> <кол-во> - удалить гемы\n"
            "/startprogressweek - запуск события\n"
            "/update_mau - обновление статистики\n"
            "/refund <id> <payment_id> - возврат платежа\n\n"
            
            "• Топы:\n"
            "/top_gems - топ по гемсам\n"
            "/top_xp - топ по опыту\n"
            "/top_clicks - топ по кликам\n"
            "/top_star_donate - топ донатеров\n\n"
            
            "• Управление клавиатурой:\n"
            "/hide_keyboard - скрыть клавиатуру\n"
            "/show_keyboard - показать клавиатуру\n\n"
            
            "• Дополнительные функции:\n"
            "/check_connection - проверка интернет-соединения\n"
            "/monitoring - просмотр статистики бота\n\n"
            "• Оплата и финансы:\n"
"/create_invoice <сумма> - создать счет на оплату\n"
"  • Можно указать получателя через параметр username\n"
"/check_invoice <код> - проверить статус счета\n"
"  • Узнаете статус оплаты и историю платежей\n"
"/create_check <сумма> - создать чек\n"
"  • Можно создать чек для конкретного пользователя\n"
"/check_payment - проверить историю платежей\n"
"  • Просмотр всех ваших операций\n\n"

        )
        
        await event.reply(help_message, parse_mode='html')
        
    except Exception as e:
        logging.error(f"Ошибка в хендлере help: {str(e)}")
        await event.reply("Произошла ошибка при отображении справки")

@bot.on(events.InlineQuery)
async def inline_handler(event):
    try:
        raw_query = event.query.query or ""  # Защита от None

        # Шаг 1. Оставляем только разрешённые символы
        allowed_chars = (
            'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'  # Кириллица строчная
            'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'  # Кириллица заглавная
            'abcdefghijklmnopqrstuvwxyz'          # Латиница строчная
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ'          # Латиница заглавная
            '0123456789'                           # Цифры
            '.,-+()#@=_/:?&{}\"[]'
            ' \t\n'                              # Пробелы/табуляция
        )

        cleaned = ''.join(char for char in raw_query if char in allowed_chars)

        # Шаг 2. Приводим к нижнему регистру и убираем лишние пробелы
        query = cleaned.strip().lower()

        print(f"[inline] Исходный: '{raw_query}' → Очищенный: '{query}'")

        results = []

        # 1. Магазин
        if query == "магазин":
            results.append(await event.builder.article(
                title="Открыть магазин",
                description="Перейти в каталог товаров",
                text="Нажмите, чтобы открыть магазин",
                buttons=[Button.inline("Открыть каталог", data="shop_main")]
            ))

        # 2. Свой профиль (компактный, с фото)
        elif query == "профиль":
            user_id = event.sender_id
            user_info = get_user_data(user_id)
            progress = load_user_progress()

            if not user_info:
                results.append(await event.builder.article(
                    title="Профиль не найден",
            description="Не удалось загрузить ваш профиль",
            text="❌ Ваш профиль не найден в базе данных."
                ))
                await event.answer(results)
                return

            # Получаем прогресс пользователя (если нет — инициализируем)
            if str(user_id) not in progress:
                progress[str(user_id)] = {
                    'currentweek_click': 0,
            'endweek_click': WEEKLY_TARGETS['clicks'],
            'currentweek_gems': 0,
            'endweek_gems': WEEKLY_TARGETS['gems'],
            'currentweek_xp': 0,
            'endweek_xp': WEEKLY_TARGETS['xp']
                }
                save_user_progress(progress)

            user_progress = progress[str(user_id)]

            first_name = user_info.get('first_name', str(user_id)).strip()
            user_mention = f'<a href="tg://user?id={user_id}">{first_name}</a>'

            # Формируем текст только с основными данными (без прогресса события)
            text = (
                f"<b>📊 Ваш профиль ({user_mention})</b>\n\n"
                f"💎 Гемы: {user_info['gems']}\n"
                f"⭐ Опыт: {user_info['xp']}\n"
                f"📊 Клики: {user_info['click_count']}\n"
                f"🎰 Спины: {user_info['spin_count']}\n"
                f"🌟 Донат‑звёзды: {user_info['stars']}"
            )

            # Генерируем URL для изображения (как в блоке progress)
            aers = f"Прогресс%20события:%0AКлики:%20{user_progress['currentweek_click']}%0AГемы:%20{user_progress['currentweek_gems']}%0AОпыт:%20{user_progress['currentweek_xp']}%0A"
            image_url = (
                f'https://old.fonts-online.ru/img_fonts.php?'
                f'id=18318&t={aers}&f=000000'
            )

            buttons = [
                [Button.inline("Мои гемы", data="gems"), Button.inline("Статистика", data="stats")],
                [Button.inline("Прогресс события", data="progress"), Button.inline("Назад", data="back")]
            ]

            results.append(await event.builder.photo(
                file=image_url,
                text=text,
                buttons=buttons,
                parse_mode='html'
            ))

        # 3. Чужой профиль по ID (компактный, с фото)
        elif query.startswith("профиль "):
            id_part = query[len("профиль "):].strip()
            if id_part.isdigit():
                user_id = int(id_part)
                user_info = get_user_data(user_id)
                progress = load_user_progress()

                if not user_info:
                    results.append(await event.builder.article(
                        title="Профиль не найден",
                        description=f"Пользователь {user_id} не существует",
                        text=f"❌ Профиль с ID {user_id} не найден."
                    ))
                    await event.answer(results)
                    return

                # Получаем прогресс пользователя (если нет — показываем нули)
                user_progress = progress.get(str(user_id), {
                    'currentweek_click': 0,
            'endweek_click': WEEKLY_TARGETS['clicks'],
            'currentweek_gems': 0,
            'endweek_gems': WEEKLY_TARGETS['gems'],
            'currentweek_xp': 0,
            'endweek_xp': WEEKLY_TARGETS['xp']
                })

                first_name = user_info.get('first_name', str(user_id)).strip()
                user_mention = f'<a href="tg://user?id={user_id}">{first_name}</a>'

                # Текст только с основными данными профиля (без прогресса)
                text = (
                    f"<b>Профиль {user_mention}</b>\n\n"
                    f"💎 Гемы: {user_info['gems']}\n"
            f"⭐ Опыт: {user_info['xp']}\n"
            f"📊 Клики: {user_info['click_count']}\n"
            f"🎰 Спины: {user_info['spin_count']}\n"
            f"🌟 Донат‑звёзды: {user_info['stars']}"
                )

                # Генерируем URL для изображения
                aers = f"Прогресс%20события:%0AКлики:%20{user_progress['currentweek_click']}%0AГемы:%20{user_progress['currentweek_gems']}%0AОпыт:%20{user_progress['currentweek_xp']}%0A"
                image_url = (
                    f'https://old.fonts-online.ru/img_fonts.php?'
            f'id=18318&t={aers}&f=000000'
        )

                buttons = [
                    [Button.inline("Мои гемы", data="gems"), Button.inline("Статистика", data="stats")],
            [Button.inline("Прогресс события", data="progress"), Button.inline("Назад", data="back")]
                ]

                results.append(await event.builder.photo(
                    file=image_url,
            text=text,
            buttons=buttons,
            parse_mode='html'
                ))
            else:
                results.append(await event.builder.article(
                    title="Неверный формат",
            description="Укажите ID после 'профиль'",
            text="🚫 Используйте: @bot Профиль 12345"
        ))
        

        # 4. Прогресс события (новый блок!)
        elif query in ("progress", "прогресс"):
            user_id = str(event.sender_id)  # строка, как в /progressweek
            progress = load_user_progress()


            if user_id not in progress:
                progress[user_id] = {
                    'currentweek_click': 0,
            'endweek_click': WEEKLY_TARGETS['clicks'],
            'currentweek_gems': 0,
            'endweek_gems': WEEKLY_TARGETS['gems'],
            'currentweek_xp': 0,
            'endweek_xp': WEEKLY_TARGETS['xp']
                }
                save_user_progress(progress)

            user_progress = progress[user_id]
            aers = f"Прогресс%20события:%0AКлики:%20{user_progress['currentweek_click']}%0AГемы:%20{user_progress['currentweek_gems']}%0AОпыт:%20{user_progress['currentweek_xp']}%0A"

            # Расчёт процентов (с защитой от деления на 0)
            click_percent = int((user_progress['currentweek_click'] / user_progress['endweek_click']) * 100) if user_progress['endweek_click'] > 0 else 0
            gems_percent = int((user_progress['currentweek_gems'] / user_progress['endweek_gems']) * 100) if user_progress['endweek_gems'] > 0 else 0
            xp_percent = int((user_progress['currentweek_xp'] / user_progress['endweek_xp']) * 100) if user_progress['endweek_xp'] > 0 else 0

            # Визуализация прогресса (1 блок = 10%)
            click_bar = "█" * (click_percent // 10)
            gems_bar = "█" * (gems_percent // 10)
            xp_bar = "█" * (xp_percent // 10)

            # Формирование текста ответа (остаётся прежним)
            text = (
                f"📊 <b>Прогресс недели</b>\n\n"
                f"🖱 Клики: <b>{user_progress['currentweek_click']}/{user_progress['endweek_click']}</b> ({click_percent}%) | {click_bar}\n"
                f"💎 Гемы: <b>{user_progress['currentweek_gems']}/{user_progress['endweek_gems']}</b> ({gems_percent}%) | {gems_bar}\n"
                f"⭐ Опыт: <b>{user_progress['currentweek_xp']}/{user_progress['endweek_xp']}</b> ({xp_percent}%) | {xp_bar}"
            )

            # Извлекаем URL из a href
            image_url = f'https://old.fonts-online.ru/img_fonts.php?id=18318&t={aers}&f=000000'

            # Добавляем результат в виде фото с текстом
            results.append(await event.builder.photo(
                file=image_url,
                text=text,
                parse_mode='html'
            ))
            
        # 5. Клик (обработка inline‑запроса на выполнение клика)
        elif query in ("click", "клик"):
            # Получаем user_id безопасным способом
            if hasattr(event, 'sender_id'):
                user_id = str(event.sender_id)
            else:
                # Ошибка: не удалось определить ID — текстом
                results.append(await event.builder.article(
                    title="Ошибка",
                    description="Не удалось определить пользователя",
                    text="❌ Не удалось определить ваш ID. Попробуйте позже."
                ))
                await event.answer(results)
                return

            # Загружаем данные прогресса события
            progress = load_user_progress()

            # Создаём начальные данные, если их нет
            if user_id not in progress:
                progress[user_id] = {
                    'startweek_click': 0,
                    'currentweek_click': 0,
                    'endweek_click': WEEKLY_TARGETS['clicks'],
                    'startweek_gems': 0,
                    'currentweek_gems': 0,
                    'endweek_gems': WEEKLY_TARGETS['gems'],
                    'startweek_xp': 0,
                    'currentweek_xp': 0,
                    'endweek_xp': WEEKLY_TARGETS['xp']
                }
                save_user_progress(progress)

            # Получаем текущие данные прогресса
            user_progress = progress[user_id]

            # Проверяем кулдаун (как в /click_up)
            if not can_click(user_id):
                last_click = get_last_click(user_id)
                if last_click is None:
                    # Если клик ещё не совершался — разрешаем
                    pass
                else:
                    time_left = CLICK_COOLDOWN - (time.time() - last_click)
                    if time_left > 0:
                        # Кулдаун активен — текстом
                        results.append(await event.builder.article(
                            title="Кулдаун клика",
                            description=f"Подождите {format_time(time_left)} до следующего клика",
                            text=f"⏰ Подождите {format_time(time_left)} до следующего клика",
                            parse_mode='html'
                        ))
                        await event.answer(results)
                        return

            # Генерируем награды
            gems_to_add = random.randint(1, 10)
            xp_to_add = random.randint(1, 10)
            user_data = get_user_data(user_id)
            new_click_count = user_data.get('click_count', 0) + 1

            # Обновляем данные пользователя
            await update_user_data(
                event,
                click_count=new_click_count,
                gems=user_data['gems'] + gems_to_add,
                xp=user_data['xp'] + xp_to_add
            )

            # Обновляем счётчики события
            user_progress['currentweek_click'] += 1
            user_progress['currentweek_gems'] += gems_to_add
            user_progress['currentweek_xp'] += xp_to_add

            # Добавляем обновление мониторинга
            try:
                # Загружаем данные мониторинга
                monitoring_data = load_data()
                
                # Обновляем счетчики
                monitoring_data["monitoring_click_count"] += 1
                monitoring_data["monitoring_gems"] += gems_to_add
                monitoring_data["monitoring_xp"] += xp_to_add
                
                # Обновляем время
                monitoring_data["last_updated"] = datetime.now().strftime("%d.%m.%Y в %H:%M:%S")
                
                # Сохраняем изменения
                save_data(monitoring_data)
            except Exception as e:
                logging.error(f"Ошибка при обновлении мониторинга: {str(e)}")

            # Сохраняем время клика
            current_time = time.time()
            user_progress['last_click_time'] = current_time
            save_user_progress(progress)
            set_last_click(user_id, current_time)  # старая система

            # Формируем строку для изображения
            aers = (
                f"Прогресс%20события:%0A"
                f"Клики:%20{user_progress['currentweek_click']}%0A"
                f"Гемы:%20{user_progress['currentweek_gems']}%0A"
                f"Опыт:%20{user_progress['currentweek_xp']}%0A"
            )
            image_url = f'https://old.fonts-online.ru/img_fonts.php?id=18318&t={aers}&f=000000'

            # Текст подписи под фото
            caption = (
                f"🎉 Вы получили {gems_to_add} гемсов и {xp_to_add} опыта!\n"
                f"Всего кликов: {new_click_count}"
            )

            # Отправляем результат как фото
            results.append(await event.builder.photo(
                file=image_url,
                text=caption,
                parse_mode='html'
            ))
            await event.answer(results)  # Эта строка должна быть на уровне elif

        # 6. Пустой запрос или неизвестная команда
        else:
            if not query:
                results.append(await event.builder.article(
                    title="Привет!",
                    description="Введите команду",
                    text="👋 Для начала работы:\n• @bot магазин — магазин\n• @bot профиль — ваш профиль\n• @bot профиль <ID> — чужой профиль\n• @bot progress / прогресс — прогресс недели"
                ))
            else:
                results.append(await event.builder.article(
                    title="Не найдено",
                    description="Попробуйте другой запрос",
                    text="🚫 Команда не распознана\n\nПопробуйте:\n• магазин\n• профиль\n• профиль <ID>\n• progress / прогресс"
                ))

            await event.answer(results[:50])

    except Exception as e:
        print(f"[inline_handler] Ошибка: {e}")
        await event.answer([])

# Храним ID сообщения с товарами
current_message_id = None

@bot.on(events.CallbackQuery(pattern=r'shop_main'))
async def handle_shop_main(event):
    try:
        keyboard = await create_shop_keyboard(1)
        
        if not keyboard:
            await event.answer('Ошибка загрузки товаров', alert=True)
            return
            
        # Исправленный формат ответа
        await event.answer(
            message="🎯 Каталог товаров:",
            cache_time=0
        )
        await event.edit(
            message="🎯 Каталог товаров:",
            buttons=keyboard
        )
        
    except Exception as e:
        logging.error(f"Ошибка при открытии магазина: {str(e)}")
        await event.answer("Произошла ошибка при загрузке магазина", cache_time=0)

@bot.on(events.CallbackQuery(pattern=r'shop_page(\d+)'))
async def handle_shop_page(event):
    try:
        page_number = int(event.pattern_match.group(1))
        
        total_products = len(products)
        
        if page_number < 1 or page_number > (total_products // 3) + 1:
            await event.answer('Неверный номер страницы', alert=True)
            return
            
        keyboard = await create_shop_keyboard(page_number)
        
        if not keyboard:
            await event.answer('Страница не найдена', alert=True)
            return
            
        navigation_buttons = []   
            
        # Исправленный формат редактирования
        await event.answer(
            message=f"🛒 Магазин - страница {page_number}",
            cache_time=0
        )
        await event.edit(
            message=f"🛒 Магазин - страница {page_number}",
            buttons=keyboard + [navigation_buttons]
        )
        
    except Exception as e:
        logging.error(f"Ошибка при обработке страницы: {str(e)}")
        await event.answer('Ошибка обработки запроса', cache_time=0)

# Функция для создания счета с указанием суммы
@bot.on(events.NewMessage(pattern=r'^/create_invoice (\d+)$'))
async def test_invoice_handler(event):
    try:
        amount = int(event.pattern_match.group(1))
        
        if amount <= 0:
            await event.reply("Сумма должна быть больше нуля")
            return
            
        result = await create_invoice(1, amount)  # Сумма = количеству
        
        if result and result.get('status_code') == 200:
            invoice_code = result.get('code')
            
            # Создаем кнопку проверки оплаты с передачей количества гемов
            buttons = [
                [Button.inline("✅ Проверить оплату", 
                               data=f"check_invoice={invoice_code}|gems={amount}")]
            ]
            
            await event.reply(
                f"Счёт создан успешно!\n"
                f"Код: {invoice_code}\n"
                f"Ссылка: {result.get('link')}",
                buttons=buttons
            )
        else:
            await event.reply(f"Ошибка при создании счёта: {result.get('msg', 'Неизвестная ошибка')}")
            
    except Exception as e:
        await event.reply(f"Произошла ошибка: {str(e)}")

# Функция проверки существования счёта
async def invoice_exists(invoice_code):
    try:
        check_result = await check_invoice(invoice_code)
        return check_result and check_result.get('status_code') == 200
    except Exception as e:
        logging.error(f"Ошибка проверки счёта {invoice_code}: {str(e)}")
        return False

# Обработчик callback для проверки оплаты
@bot.on(events.CallbackQuery(pattern=r'check_invoice=(.*)\|gems=(\d+)'))
async def check_invoice_callback_handler(event):
    try:
        invoice_code, gems = event.pattern_match.groups()
        invoice_code = invoice_code.decode('utf-8')
        gems = int(gems)
        
        logging.info(f"Получен код счёта: {invoice_code}, гемов: {gems}")
        
        if not await invoice_exists(invoice_code):
            await event.answer("Счёт не найден", cache_time=0)
            return
            
        result = await check_invoice(invoice_code)
        
        if result and result.get('status_code') == 200:
            payed = result.get('payed')
            
            if payed:
                # Обновляем мониторинг
                monitoring_data = load_data()
                monitoring_data['monitoring_payed_gems'] += gems
                save_data(monitoring_data)
                
                # Обновляем баланс пользователя
                user_id = str(event.sender_id)
                user_data = get_user_data(user_id)
                new_gems = user_data['gems'] + gems
                
                await update_user_data(
                    event,
                    gems=new_gems
                )
                
                # Показываем уведомление без редактирования сообщения
                await event.edit(
                    f"Оплата подтверждена!\n"
                    f"Вам начислено {gems} гемов.\n"
                    f"Новый баланс: {new_gems} 💎",
                )
                
            else:
                await event.answer("Счёт ещё не оплачен", alert=True, cache_time=0)
                
        else:
            await event.answer("Ошибка проверки", cache_time=0)
            
    except Exception as e:
        logging.error(f"Произошла ошибка: {str(e)}")
        await event.answer(
            f"Произошла ошибка: {str(e)}", 
            cache_time=0
        )
        
@bot.on(events.NewMessage(pattern=r'^/check_invoice (\w+)$'))
async def check_invoice_handler(event):
    try:
        invoice_code = event.pattern_match.group(1)
        
        # Получаем статус счёта
        result = await check_invoice(invoice_code)
        
        if result and result.get('status_code') == 200:
            payed = result.get('payed')
            payments = result.get('payments', {})
            
            response = (
                f"Статус счета:\n"
                f"Оплачен: {payed}\n\n"
                f"Платежи:\n"
            )
            
            if payments:
                payment_number = 1
                for payment_id, payment_data in payments.items():
                    for payment_num, details in payment_data.items():
                        response += (
                            f"<blockquote>Платеж №{payment_number} от <a href='https://t.me/CupLegendBot?start=Account={payment_id}'>{payment_id}</a>:\n"
                            f"  Дата: {details.get('date', {}).get('date')} "
                            f"{details.get('date', {}).get('time')}\n"
                            f"  Сумма: {details.get('summa')} 💎\n"
                            f"  Комментарий: {details.get('comment')}</blockquote>\n"
                        )
                        payment_number += 1
                        
            await event.reply(response, parse_mode='html', link_preview=False)
            
        elif result and result.get('status_code') == 404:
            await event.reply("Счёт не найден")
            
        else:
            await event.reply("Ошибка проверки статуса счёта")
            
    except Exception as e:
        await event.reply(f"Произошла ошибка: {str(e)}")

# Функция для создания чека с суммой и опциональным username
@bot.on(events.NewMessage(pattern=r'^/create_check (\d+) ?(.*)?$'))
async def test_check_handler(event):
    try:
        amount = int(event.pattern_match.group(1))
        username = event.pattern_match.group(2).strip() or None
        
        if amount == 0:
            await event.reply("Сумма не может быть нулевой")
            return
            
        if username and len(username) < 3:
            await event.reply("Некорректный username")
            return
            
        # Загружаем данные мониторинга для проверки баланса
        monitoring_data = load_data()
        current_bank_balance = monitoring_data.get('monitoring_bank_gems', 0)
        
        # Проверяем баланс пользователя
        user_data = load_user_data()
        user_id = str(event.sender_id)
        user_gems = user_data.get(user_id, {}).get('gems', 0)
        
        # Проверяем возможность операции
        if amount > 0:  # Вывод средств
            if amount > current_bank_balance:
                await event.reply(f"Недостаточно средств в банке ({current_bank_balance} 💎)")
                return
                
            if amount > user_gems:
                await event.reply(f"Недостаточно личных гемов ({user_gems} 💎)")
                return
        else:  # Внесение средств (отрицательное значение)
            if current_bank_balance + amount < 0:
                await event.reply("Операция приведет к отрицательному балансу банка")
                return
                
        # Обновляем баланс банка
        new_bank_balance = current_bank_balance - amount
        monitoring_data['monitoring_bank_gems'] = new_bank_balance
        
        # Обновляем счетчик вывода
        if amount > 0:
            monitoring_data['monitoring_withdraw_gems'] += amount
        
        save_data(monitoring_data)
        
        # Обновляем баланс пользователя при выводе
        if amount > 0:
            new_user_gems = user_gems - amount
            await update_user_data(
                event,
                gems=new_user_gems
            )
        
        result = await create_check(1, abs(amount), username)  # Передаем абсолютное значение
        
        if result and result.get('status_code') == 200:
            await event.reply(
                f"Операция выполнена успешно!\n"
                f"Новый баланс банка: {new_bank_balance} 💎\n"
                f"Выведено гемов: {monitoring_data['monitoring_withdraw_gems']} 💎\n"
                f"Код: {result.get('code')}\n"
                f"Ссылка: {result.get('link')}"
            )
        else:
            await event.reply(f"Ошибка при создании чека: {result.get('msg', 'Неизвестная ошибка')}")
            
    except Exception as e:
        await event.reply(f"Произошла ошибка: {str(e)}")

# Функция для скрытия клавиатуры
@bot2.message_handler(commands=['hide_keyboard'])
def hide_keyboard(message):
    remove_keyboard = tb.types.ReplyKeyboardRemove()
    bot2.reply_to(message, "Клавиатура скрыта", reply_markup=remove_keyboard)

# Функция для создания клавиатуры из JSON
def create_keyboard_from_json(json_data):
    try:
        keyboard_data = json.loads(json_data)
        keyboard = tb.types.ReplyKeyboardMarkup(resize_keyboard=True)
        
        # Создаем кнопки из JSON
        for row in keyboard_data['keyboard']:
            buttons_row = []
            for button_text in row:
                buttons_row.append(tb.types.KeyboardButton(button_text))
            keyboard.row(*buttons_row)
            
        return keyboard
    except Exception as e:
        logging.error(f"Ошибка при создании клавиатуры: {str(e)}")
        return None

# Пример JSON для клавиатуры
KEYBOARD_JSON = '''
{
    "keyboard": [
        ["Кнопка 1", "Кнопка 2"]
    ],
    "resize_keyboard": true
}
'''

@bot2.message_handler(commands=['show_keyboard'])
def show_keyboard(message):
    try:
        # Загружаем клавиатуру из JSON
        keyboard = create_keyboard_from_json(KEYBOARD_JSON)
        
        if keyboard:
            bot2.reply_to(
                message, 
                "Клавиатура показана", 
                reply_markup=keyboard
            )
        else:
            bot2.reply_to(message, "Не удалось создать клавиатуру")
            
    except Exception as e:
        logging.error(f"Ошибка в show_keyboard: {str(e)}")
        bot2.reply_to(message, "Произошла ошибка")

# Функция для сохранения JSON-клавиатуры в файл
def save_keyboard_json(filename, json_data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(json_data)
        return True
    except Exception as e:
        logging.error(f"Ошибка сохранения JSON: {str(e)}")
        return False

# Функция для загрузки JSON-клавиатуры из файла
def load_keyboard_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Ошибка загрузки JSON: {str(e)}")
        return None

# Если нужно убрать клавиатуру при определенном действии
@bot2.message_handler(func=lambda message: True)
def handle_messages(message):
    if "убрать клавиатуру" in message.text.lower():
        remove_keyboard = tb.types.ReplyKeyboardRemove()
        bot2.reply_to(message, "Клавиатура скрыта", reply_markup=remove_keyboard)

async def run_telethon():
    try:
        await bot.start()
        print("Telethon запущен")
        await bot.run_until_disconnected()
    except Exception as e:
        logging.error(f"Ошибка Telethon: {str(e)}")

def run_telebot():
    try:
        # Настройка TeleBot
        bot2.enable_save_next_step_handlers(False)
        bot2.infinity_polling(timeout=10, long_polling_timeout=5)
        print("TeleBot запущен")
    except Exception as e:
        logging.error(f"Ошибка TeleBot: {str(e)}")

def run_admin_console():
    try:
        admin.admin_console()
    except Exception as e:
        logging.error(f"Ошибка административной консоли: {str(e)}")

async def main():
    try:
        # Запускаем TeleBot в отдельном потоке
        telebot_thread = threading.Thread(target=run_telebot)
        telebot_thread.daemon = True
        telebot_thread.start()
        
        # Запускаем административную консоль в отдельном потоке
        admin_thread = threading.Thread(target=run_admin_console)
        admin_thread.daemon = True
        admin_thread.start()
        
        # Запускаем Telethon
        await run_telethon()
        
    except Exception as e:
        logging.error(f"Критическая ошибка: {str(e)}")
    finally:
        print("Бот остановлен")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Остановка бота по команде пользователя")
