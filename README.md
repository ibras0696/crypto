# CryptoSwap — FastAPI Crypto Exchange MVP 🪙⚡

Учебный минимальный прототип криптообменника на FastAPI. Показывает продакшн‑паттерны: JWT‑аутентификация и роли, заказы/транзакции, KYC, кэширование курсов через Redis и публичный REST Binance, миграции Alembic, простая админ‑панель на шаблонах.

Важное предупреждение: это демонстрационный MVP. Не используйте в проде без аудита безопасности и доработок.

<p align="left">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.11x-009688?logo=fastapi&logoColor=white">
  <img alt="SQLAlchemy" src="https://img.shields.io/badge/SQLAlchemy-2.x%20async-8C2728">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white">
  <img alt="Redis" src="https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white">
  <img alt="Alembic" src="https://img.shields.io/badge/Alembic-migrations-444">
  <img alt="JWT" src="https://img.shields.io/badge/Auth-JWT%20(HS256)-6C2EB9">
  <img alt="Templates" src="https://img.shields.io/badge/Jinja2-templates-FFB000">
  <img alt="Chart.js" src="https://img.shields.io/badge/Chart.js-analytics-FF6384">
  <img alt="Tests" src="https://img.shields.io/badge/pytest-ready-0A9EDC?logo=pytest&logoColor=white">
</p>

— Для найма: видно владение FastAPI/SQLAlchemy async, Redis, Alembic, аутентификацией и защитными механизмами (rate‑limit, глобальный error‑handler, CORS).  
— Для разработчиков: компактный, но показательный каркас обменника.

---

## ✨ Возможности

- Регистрация/логин (JWT, HS256), роли: user | operator | admin
- Заявки на обмен (Orders) и связанные транзакции (on‑chain/internal)
- KYC: хранение и статус, ограничения до верификации
- Курсы через Binance public REST + Redis‑кэш + fallback на last_good
- Управление валютами и резервами (для admin/operator)
- Аналитика объёмов: простые графики на Chart.js (через шаблоны)
- Audit‑лог действий (база для последующего расширения)
- Alembic‑миграции
- Rate limiting (in‑memory, для dev) и глобальный обработчик ошибок
- CORS и конфигурация через pydantic‑settings

См. код:  
- Точка входа: [app/main.py](app/main.py) — роуты, CORS, глобальный error‑handler, простой rate‑limit, метрики  
- Зависимости/утилиты: [app/core/deps.py](app/core/deps.py), [app/core/security.py](app/core/security.py)  
- Модели: [app/models](app/models) (User, KYCData, Order, Transaction, Currency)  
- Alembic: [alembic/env.py](alembic/env.py)

---

## 🧱 Архитектура

```mermaid
flowchart LR
  User --> API[FastAPI]
  API --> Auth[JWT Auth & Roles]
  API --> Services[Business logic]
  Services --> DB[(PostgreSQL/SQLite via SQLAlchemy async)]
  Services --> Cache[(Redis)]
  API --> Templates[Jinja2 + Static (Tailwind CDN/Chart.js)]
```

- Роутеры: `auth`, `orders`, `rates`, `currencies`
- Кэш и курсы: Redis + публичный REST Binance (с фолбэком)
- Метрики/ограничения: in‑memory rate limit в middleware + эндпоинт `/metrics`
- Миграции: Alembic (из коробки)

---

## 📚 Модель данных (основное)

- User: email, hashed_password, role, kyc_status, created_at; 1‑к‑1 KYCData
- KYCData: full_name, document_id, user_id
- Currency: code, name, reserve
- Order: связи user/from_currency/to_currency, amount_from/amount_to, rate, status, created_at
- Transaction: order_id, tx_hash, amount, status, created_at

Файлы:  
[app/models/user.py](app/models/user.py) · [app/models/order.py](app/models/order.py) · [app/models/transaction.py](app/models/transaction.py)

---

## 🔌 API (основные идеи)

- Auth:
  - POST `/auth/register` → создать пользователя
  - POST `/auth/login` → выдать `access_token`
- Currencies:
  - GET `/currencies` → публичный список
  - POST `/currencies` (admin/operator) → создать валюту
  - PATCH `/currencies/{id}` (admin/operator) → изменить резерв
- Orders:
  - CRUD заявок, фильтрация по статусам, создание транзакций
- Rates:
  - GET `/rates/{PAIR}` → курс с кэшированием (например, BTCUSDT), валидация по `ALLOWED_RATE_QUOTES`
- System:
  - GET `/metrics` → простые показатели (реквесты, latency) — если включено
  - Статика/шаблоны: `/` (демо‑панель), `/static/*`

Пример защиты ролей: см. `require_roles()` в [app/core/deps.py](app/core/deps.py).  
Глобальный error‑handler: в [app/main.py](app/main.py).

---

## ⚙️ Конфигурация (.env)

Основные переменные (см. `app/core/config.py`, `app/main.py`, `app/core/deps.py`):

```env
# App
APP_NAME=CryptoSwap
DEBUG=True
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]  # [] чтобы отключить

# Security
SECRET_KEY=please-change-me
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database (выберите одно)
DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/crypto
# или для локального dev:
# DATABASE_URL=sqlite+aiosqlite:///./dev.db

# Redis
REDIS_URL=redis://localhost:6379/0

# Rates provider
BINANCE_PUBLIC_URL=https://api.binance.com
ALLOWED_RATE_QUOTES=["USDT","BUSD"]
RATE_CACHE_TTL=10

# Opt-in features
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
METRICS_ENABLED=true
```

---

## 🚀 Быстрый старт (локально)

Требования: Python 3.12+, Redis (для курсов), PostgreSQL или SQLite.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# Создайте .env в корне (см. раздел выше), для простоты можно начать с SQLite
echo "DATABASE_URL=sqlite+aiosqlite:///./dev.db" >> .env
echo "REDIS_URL=redis://localhost:6379/0" >> .env
echo "SECRET_KEY=dev-secret" >> .env

# Миграции базы
alembic upgrade head

# Запуск API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Поднять инфраструктуру быстро:
```bash
# Redis
docker run -d --name redis -p 6379:6379 redis:7

# PostgreSQL (опционально, если не используете SQLite)
docker run -d --name pg \
  -e POSTGRES_PASSWORD=app -e POSTGRES_USER=app -e POSTGRES_DB=crypto \
  -p 5432:5432 postgres:16
```

Откройте http://127.0.0.1:8000 — доступна демо‑панель и интерактивная документация FastAPI (`/docs`).

---

## 🐳 Docker / Compose (пример)

Если в репозитории есть docker‑манифесты, запустите:
```bash
docker compose up -d --build
# Логи
docker compose logs -f api
# Миграции (если не применяются автоматически)
docker compose exec api alembic upgrade head
```

(При отсутствии compose‑файлов используйте обычный Dockerfile‑флоу:
соберите образ, пробросьте .env и порт, смонтируйте папку с шаблонами/статикой при необходимости.)

---

## 🧪 Тесты и качество

Dev‑набор (requirements.txt):
- pytest, pytest‑asyncio
- ruff/mypy (при желании)

Команды:
```bash
pytest -q
# опционально:
# ruff check .
# mypy .
```

---

## 🔐 Безопасность (важно для крипты)

- Меняйте `SECRET_KEY`, используйте отдельные ключи на окружение
- Пересмотрите механики ролей и доступов под реальные кейсы
- Продумайте хранение KYC и персональных данных (шифрование, ретеншн)
- В продакшене добавьте:
  - полноценный rate‑limit и WAF
  - idempotency‑ключи на критичных эндпоинтах
  - аудит, алерты, централизованные логи
  - мониторинг/метрики (Prometheus/Grafana)
  - очереди/таск‑процессы для реальных платёжных интеграций

---

## 🗺️ Roadmap (пример)

- [ ] Разделение ролей по пермишенам (RBAC полнее)
- [ ] Idempotent‑создание заявок и транзакций
- [ ] Подтверждение e‑mail и восстановление пароля
- [ ] S3‑хранилище для логов/экспортов
- [ ] Вынесение rate‑limit и метрик в prod‑grade инструменты

---

## 📂 Структура (ключевое)

```
app/
  main.py                 # FastAPI, CORS, middleware rate-limit, /metrics, шаблоны/статика
  core/
    deps.py               # Redis, текущий пользователь, роли, курсы (Binance+Redis)
    security.py           # пароли (bcrypt) и JWT
    config.py             # настройки (pydantic-settings)
    database.py           # engine/session/Base (async)
  models/
    user.py               # User, KYCData
    order.py              # Order (статусы, связи)
    transaction.py        # Transaction
    currency.py           # Currency (код/название/резерв)
  routers/
    auth.py               # регистрация/логин/JWT
    orders.py             # CRUD заказов, транзакции
    rates.py              # получение курсов
    currencies.py         # управление валютами/резервами
  templates/, static/     # простая админ/демо-панель
alembic/                  # миграции
alembic.ini
requirements.txt
```

---
