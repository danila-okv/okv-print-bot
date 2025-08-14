from aiogram import Router

# Note: When adding new UI handlers, import them here and include them in
# the router chain. The profile handler is responsible for the profile menu
# and order history.
from .handlers import promo, cancel, confirm, fallback, file, main_menu, options, payment, back, profile

router = Router()

for module in (promo, cancel, file, main_menu, payment, options, confirm, back, fallback):
    router.include_router(module.router)

# Include the profile router separately. It must be registered after other
# handlers so that more specific callbacks like "orders" are caught before
# generic handlers.
router.include_router(profile.router)