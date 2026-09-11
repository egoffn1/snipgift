from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

MARKET_LABELS = {
    "tonnel": "Tonnel",
    "mrkt": "MRKT",
    "portals": "Portals",
    "fragment": "Fragment",
}

TOP_MODELS = ["Model 1", "Model 2", "Model 3", "Model 4", "Model 5"]
TOP_BACKDROPS = ["Backdrop 1", "Backdrop 2", "Backdrop 3", "Backdrop 4", "Backdrop 5"]
TOP_PATTERNS = ["Pattern 1", "Pattern 2", "Pattern 3", "Pattern 4", "Pattern 5"]


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Настроить поиск", callback_data="menu:settings")],
            [InlineKeyboardButton(text="📊 Мои алерты", callback_data="menu:alerts")],
            [
                InlineKeyboardButton(text="▶️ Activer scan", callback_data="menu:resume"),
                InlineKeyboardButton(text="⏸️ Pause", callback_data="menu:pause"),
            ],
            [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="menu:help")],
        ]
    )


def market_checkboxes(
    selected: list[str],
    action_prefix: str,
) -> InlineKeyboardMarkup:
    buttons = []
    for name, label in MARKET_LABELS.items():
        check = "☑️" if name in selected else "⬜"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{check} {label}",
                    callback_data=f"{action_prefix}:{name}",
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text="✅ Valider",
                callback_data=f"{action_prefix}:done",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def floor_market_choice() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Tous les marchés", callback_data="floor:all")],
            [InlineKeyboardButton(text="✍️ Choisir manuellement", callback_data="floor:manual")],
        ]
    )


def attr_options(action_prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Не важно (любой)",
                    callback_data=f"{action_prefix}:any",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✍️ Ввести вручную",
                    callback_data=f"{action_prefix}:manual",
                )
            ],
        ]
    )


def yes_no(action_prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"{action_prefix}:yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"{action_prefix}:no"),
            ]
        ]
    )


def auctions_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Аукционы вкл", callback_data="auction:on"),
                InlineKeyboardButton(text="❌ Аукционы выкл", callback_data="auction:off"),
            ]
        ]
    )


def settings_saved() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Мои настройки", callback_data="menu:show_settings")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu:main")],
        ]
    )
