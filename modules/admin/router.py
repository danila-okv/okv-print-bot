from aiogram import Router
from .handlers import (
    ban,
    control,
    promo,
    shell,
    message_user,
    gift,
    expense,
    refill,
    supplies
)

router = Router()

for module in (ban, control, promo, shell, message_user, gift, expense, refill, supplies):
    router.include_router(module.router)