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
    либо бесплатные страницы, либо скидку. В расширенной версии бот также
    поддерживает массовую выдачу подарков: при вызове команды /gift без
    указания ID бот попросит ввести список пользовательских идентификаторов.
    Порядок состояний:

    1. entering_users – ввод списка пользователей, которым будет выдан подарок (используется,
       когда команда /gift вызвана без параметров).
    2. choosing_type – выбор типа подарка (страницы или скидка).
    3. entering_value – ввод количества страниц либо размера скидки.
    4. notify_choice – запрос, следует ли уведомить пользователя(ей).
    5. entering_message – ввод текста уведомления для пользователя(ей).

    The extra ``entering_users`` state allows an administrator to enter a comma‑ or newline‑separated
    list of user IDs. When the ``/gift`` command is invoked without specifying a user ID,
    the bot will switch to this state and wait for the admin to provide the list.
    """
    entering_users = State()
    choosing_type = State()
    entering_value = State()
    notify_choice = State()
    entering_message = State()