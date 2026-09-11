from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

MARKET_LABELS = {
    "tonnel": "Tonnel",
    "mrkt": "MRKT",
    "portals": "Portals",
    "fragment": "Fragment",
}


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Настроить поиск")],
            [KeyboardButton(text="📊 Мои алерты")],
            [
                KeyboardButton(text="▶️ Продолжить"),
                KeyboardButton(text="⏸️ Пауза"),
            ],
            [KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True,
    )


def _build_sell_kb(
    sell: list[str], profit: float, paused: bool
) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    for name, label in MARKET_LABELS.items():
        check = "☑" if name in sell else "☐"
        buttons.append(
            [InlineKeyboardButton(
                text=f"{check} {label}",
                callback_data=f"cfg:sell:{name}",
            )]
        )
    buttons.append([
        InlineKeyboardButton(
            text=f"💰 Прибыль {profit:.0f}% −",
            callback_data=f"cfg:profit:{max(profit - 1, 0):.0f}",
        ),
        InlineKeyboardButton(
            text=f"+ 💰 Прибыль {profit:.0f}%",
            callback_data=f"cfg:profit:{profit + 1:.0f}",
        ),
    ])
    btn = "▶ Продолжить" if paused else "⏸ Пауза"
    buttons.append([InlineKeyboardButton(text=btn, callback_data="cfg:pause")])
    buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data="cfg:done")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def track_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Настроить алерт", callback_data="cfg:open")],
            [InlineKeyboardButton(text="✅ Всё ок", callback_data="cfg:done")],
        ]
    )


def yes_no(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"{prefix}:yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"{prefix}:no"),
            ]
        ]
    )
