# 🎁 SnipGift

Telegram-бот для арбитража Telegram-подарков (NFT Gifts на TON).
Мониторит рынки **Tonnel**, **MRKT**, **Portals** и **Fragment** каждые
несколько секунд, находит листинги и аукционы ниже флора, считает
прибыль с учётом комиссий маркетов и присылает алерты.

Разворачивается на **бесплатном** веб-сервисе Render + PostgreSQL (Neon.tech).

---

## 📦 Стек

- Python 3.12+
- aiogram 3.x (webhook mode)
- aiohttp (веб-сервер: webhook + healthcheck + /ping)
- SQLAlchemy 2.0 async + asyncpg → PostgreSQL (Neon.tech)
- pydantic-settings (конфиг из env)

---

## 🚀 Пошаговый деплой на Render

### 1. Создай PostgreSQL (Neon.tech — бесплатно)

1. Зарегистрируйся на https://neon.tech
2. Создай проект → в разделе **Connection Details** выбери
   **Connection String** → скопируй строку вида:
   `postgresql://user:password@ep-...neon.tech/dbname?sslmode=require`
3. Сохрани её — понадобится для `DATABASE_URL`

### 2. Получи токен бота

1. Напиши [@BotFather](https://t.me/BotFather)
2. `/newbot` → дай имя → получи токен вида `123456:ABC-DEF...`
3. Включи `/setinline` (не обязательно, но полезно)

### 3. Залей код на GitHub

```bash
git init
git add .
git commit -m "SnipGift"
git remote add origin https://github.com/YOUR_USER/snipgift.git
git push -u origin main
```

### 4. Создай Web Service на Render

1. https://dashboard.render.com → **New** → **Web Service**
2. Подключи репозиторий GitHub
3. Render сам найдёт `render.yaml` и применит настройки
   (Python, `pip install`, `python main.py`, healthcheck `/healthz`)
4. Plan: **Free**

### 5. Заполни Environment-переменные

Вкладка **Environment** в твоём веб-сервисе → **Add Environment Variable**:

| Переменная | Значение |
|---|---|
| `BOT_TOKEN` | токен из BotFather |
| `WEBHOOK_URL` | `https://<app-name>.onrender.com` (без слэша) |
| `DATABASE_URL` | строка из Neon.tech |
| `TONNEL_AUTH_DATA`, `MRKT_AUTH_DATA`, ... | (опционально) initData мини-аппов |
| `FEE_TONNEL`, `FEE_MRKT`, ... | (опционально) переопределение комиссий |

Раздел → **Manual Deploy** → **Deploy latest commit**.

### 6. Проверь, что бот стартовал

1. Открой **Logs** сервиса — должно быть:
   ```
   Starting SnipGift on 0.0.0.0:10000
   Webhook set: https://<app-name>.onrender.com/webhook
   Scanner started with markets: ['tonnel', 'mrkt', 'portals', 'fragment']
   ```
2. Перейди на `https://<app-name>.onrender.com/healthz` → увидишь `OK`
3. Напиши боту `/start` — придёт главное меню

---

## ⏰ Борьба со «сном» бесплатного инстанса

Render free «засыпает» после ~15 минут бездействия. Решение — пингер:

### Способ A: cron-job.org (рекомендуется)

1. Зарегистрируйся на https://cron-job.org
2. **Create cronjob**:
   - URL: `https://<app-name>.onrender.com/ping`
   - Schedule: **every 10 minutes**
3. Сохрани. Теперь инстанс будет просыпаться каждые 10 минут.

### Способ B: UptimeRobot

1. https://uptimerobot.com → **New monitor** → **HTTP(s)**
2. URL: `https://<app-name>.onrender.com/ping`
3. Interval: 10 minutes

### Способ C: self-ping (уже встроен)

Бот сам пингует свой `/ping` каждые `SELF_PING_INTERVAL` (600 сек).
Это страховка, но внешний пингер надёжнее — он будит инстанс, даже
если процесс упал и Render его перезапустил.

> ⚠️ Во время сна задержка ответа бота будет ~30-60 секунд (cold start).
> Это нормально для free-плана.

---

## ⚙️ Настройка бота

Отправь `/start` → кнопка **🔍 Настроить поиск** — пошаговый мастер (FSM):

1. Название подарка (например `Heart`)
2. Модель / фон / узор (или «любые»)
3. Мин/макс цена покупки в TON
4. Мин. % прибыли для алерта
5. Фильтр «красивый ID» (палиндром / повторы / <1000)
6. Маркеты ПОКУПКИ (Tonnel / MRKT / Portals / Fragment)
7. Маркеты ПРОДАЖИ
8. Маркеты для расчёта ФЛОРА (все или вручную)
9. Аукционы вкл/выкл + макс. ставка

Алерт содержит: название, модель/фон/узор, ID, цену покупки,
флор продажи, чистую прибыль в TON и %, кнопку «Открыть на маркете»
и «Mute».

---

## 🧠 Как считается прибыль

```
net_sell  = floor_sell_market_price * (1 - fee_sell_market)
profit   = net_sell - buy_price
profit%  = profit / buy_price * 100
```

- `floor_sell_market_price` — минимальная цена на выбранных маркетах продажи
- Если маркеты продажи не выбраны — берётся глобальный флор
- Выбросы: листинги более чем на 50% ниже медианы выборки отбрасываются

Комиссии по умолчанию в `utils/fees.py` и переопределяются через env.

---

## 📁 Структура

```
snipgift/
├── main.py                  # aiohttp: webhook + healthcheck + bg-задачи
├── config.py                # env-конфиг (pydantic-settings)
├── db/                      # SQLAlchemy 2.0 async models/repo
├── markets/                 # клиенты Tonnel/MRKT/Portals/Fragment
├── core/                    # scanner, analyzer, filters, floor
├── bot/                     # aiogram handlers/keyboards/middlewares
├── utils/                   # fees, id_beauty, logger
├── requirements.txt
├── render.yaml
└── .env.example
```

---

## 🧪 Локальный запуск

```bash
cd snipgift
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# без WEBSOCKET_URL и DATABASE_URL бот запустится в polling-режиме
# на временной SQLite (/tmp/snipgift.db)
BOT_TOKEN=your_token python main.py
```

Для полного локального запуска как на Render (webhook + Postgres):
`WEBHOOK_URL` и `DATABASE_URL` задай в `.env`.

---

## TODO (следующие итерации)

- [ ] Автоматическая покупка/ставки через TON Connect (Tonkeeper)
- [ ] Portals / Fragment аукционы: полная интеграция и стабильный парсер
- [ ] Обновление `authData` для маркетов без ручного копирования
- [ ] Веб-дашборд со статистикой прибыли и графиками
- [ ] Обучение цен (EMA) вместо простого медианного флора
- [ ] Telegram Premium-уведомления с фото подарка

---

## ⚠️ Дисклеймер

Бот работает только с **публичными** данными маркетплейсов.
API-эндпоинты Tonnel/MRKT — неофициальные и могут меняться.
Не является инвестиционной рекомендацией 🚫