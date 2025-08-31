from aiogram import Router

# Note: When adding new UI handlers, import them here and include them in
# the router chain. The profile handler is responsible for the profile menu
# and order history.
from .handlers import promo, cancel, confirm, fallback, file, options, payment, back, profile, print_status, start

router = Router()

for module in (promo, cancel, file, start, payment, options, confirm, back, fallback):
    router.include_router(module.router)

# Include the print status handler.  It should be registered early so that
# its callback is caught before generic handlers.
router.include_router(print_status.router)

# Include the profile router separately. It must be registered after other
# handlers so that more specific callbacks like "orders" are caught before
# generic handlers.
router.include_router(profile.router)