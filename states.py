from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from modules.ui.handlers.main_menu import send_main_menu
from modules.analytics.logger import warning

class UserStates(StatesGroup):
    reviewing_print_details = State()
    setting_print_options = State()
    inputting_pages = State()
    inputting_copies_count = State()
    confirming_pages = State()
    selecting_print_layout = State()
    selecting_payment_option = State()
    confirming_cash_payment = State()
    confirming_card_payment = State()

class PromoStates(StatesGroup):
    """
    Состояния для создания промокода администратором.

    Порядок состояний:
    1. choosing_type – выбор типа награды (бесплатные страницы или скидка).
    2. entering_activations – ввод общего количества активаций.
    3. entering_reward_value – ввод значения награды (количество страниц или процент скидки).
    4. entering_duration – ввод срока действия в днях (можно пропустить, введя «нет»).
    5. entering_message – ввод кастомного текста для пользователя, где
       можно использовать шаблоны {value} и {date}.
    6. confirming – подтверждение создания промокода.
    """
    choosing_type = State()
    entering_activations = State()
    entering_reward_value = State()
    entering_duration = State()
    entering_message = State()
    confirming = State()

class GiftStates(StatesGroup):
    """
    Состояния для команды /gift, позволяющей администратору выдать пользователю
    либо бесплатные страницы, либо скидку. Порядок состояний:

    1. choosing_type – выбор типа подарка (страницы или скидка).
    2. entering_value – ввод количества страниц либо размера скидки.
    3. notify_choice – запрос, следует ли уведомить пользователя.
    4. entering_message – ввод текста уведомления для пользователя.
    """
    choosing_type = State()
    entering_value = State()
    notify_choice = State()
    entering_message = State()