# CryptoSwap (FastAPI Crypto Exchange MVP)

Учебный минимальный прототип криптообменника (MVP). Служит учебным примером архитектуры FastAPI (Auth + Roles + Orders + Transactions + KYC + Analytics). **Не используйте в реальном продакшене без аудита безопасности.**

## Возможности
- Регистрация / логин (JWT)
- Роли: user / operator / admin + промоут эндпоинт
- Создание / просмотр / фильтрация заявок, статусы + транзакции
- KYC данные (хранение, статус, лимиты до верификации)
- Курсы через Binance публичный REST + Redis кэш + last_good fallback
- Управление валютами и резервами (admin/operator)
- Аналитика объёмов (график Chart.js)
- Audit лог действий
- Alembic миграции
- Простая админ панель (HTML + Tailwind + Chart.js)
- Rate limiting (in-memory, опционально)
- Глобальный обработчик ошибок, CORS, конфиг через pydantic-settings

## Стек
Backend: FastAPI, SQLAlchemy 2 (async), PostgreSQL (asyncpg), Pydantic v2.
Auth: JWT (python-jose) + bcrypt (passlib).
Caching: Redis.
Frontend: Jinja2, Tailwind CDN, Chart.js.
Infra: Docker / docker-compose, Nginx, Alembic.

## 1. Быстрый локальный старт (без Docker)
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -r crypto_exchange/requirements.txt

# Упростить: SQLite вместо PostgreSQL
echo "DATABASE_URL=sqlite+aiosqlite:///./dev.db" > crypto_exchange/.env

cd crypto_exchange
alembic upgrade head               # применить миграции (для SQLite создаст файл)
uvicorn crypto_exchange.app.main:app --reload

# Тесты (опционально из корня репо)
pytest -q
```
Открой http://127.0.0.1:8000 — кнопка Demo Login создаст пользователя.

## 2. Docker Compose (локально / staging)
```bash
cd crypto_exchange/docker
cp ../.env .env        # при необходимости отредактируй
docker compose up -d --build
docker compose logs -f api
```
Миграции (если не авто):
```bash
docker compose exec api alembic upgrade head
```
Остановить: `docker compose down`.

Переназначить порт наружу (пример): в compose заменить `"8000:8000"` на `"9000:8000"`.

### 2.1 Запуск тестов в Docker
Образ имеет stage `test`, который запускает pytest во время сборки. Ошибка тестов ломает сборку.

Быстрый прогон только тестов:
```bash
cd crypto_exchange/docker
docker build -t cryptoswap:test --target test ..
```

Через compose (профиль tests):
```bash
docker compose --profile test up --build --abort-on-container-exit --exit-code-from tests tests
```
Где сервис `tests` определён в `docker/docker-compose.yml`.

## 3. Пример .env
Файл кладём в `crypto_exchange/` рядом с `alembic.ini`.
```
APP_NAME=CryptoSwap
DEBUG=false
SECRET_KEY=СЛУЧАЙНЫЙ_64_HEX

# PostgreSQL (в Docker: host=db)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=crypto
POSTGRES_PASSWORD=crypto
POSTGRES_DB=crypto

# Альтернатива (перекрывает выше)
# DATABASE_URL=sqlite+aiosqlite:///./prod.db

REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=120
METRICS_ENABLED=true
CORS_ORIGINS=["https://example.com"]
UNVERIFIED_ORDER_MAX=1000
UNVERIFIED_DAILY_VOLUME_MAX=5000
```

## 4. Production (Ubuntu + systemd + Nginx)
### 4.1. Зависимости
```bash
sudo apt update
sudo apt install -y git python3-venv python3-pip postgresql redis-server nginx certbot python3-certbot-nginx
```
### 4.2. PostgreSQL
```bash
sudo -u postgres psql -c "CREATE USER crypto WITH PASSWORD 'crypto';"
sudo -u postgres psql -c "CREATE DATABASE crypto OWNER crypto;"
```
### 4.3. Код
```bash
sudo adduser --system --group cryptoswap
sudo mkdir -p /opt/cryptoswap
sudo chown cryptoswap:cryptoswap /opt/cryptoswap
cd /opt/cryptoswap
sudo -u cryptoswap git clone <REPO_URL> .
sudo -u cryptoswap python3 -m venv .venv
sudo -u cryptoswap bash -c 'source .venv/bin/activate && pip install -r crypto_exchange/requirements.txt'
sudo -u cryptoswap cp crypto_exchange/.env.example crypto_exchange/.env  # если есть пример
```
Отредактируй `.env`, убери строку DATABASE_URL если используешь POSTGRES_* переменные.

### 4.4. Миграции
```bash
cd /opt/cryptoswap/crypto_exchange
source ../.venv/bin/activate
alembic upgrade head
```
### 4.5. systemd unit `/etc/systemd/system/cryptoswap.service`
```
[Unit]
Description=CryptoSwap FastAPI
After=network.target

[Service]
User=cryptoswap
Group=cryptoswap
WorkingDirectory=/opt/cryptoswap/crypto_exchange
EnvironmentFile=/opt/cryptoswap/crypto_exchange/.env
ExecStart=/opt/cryptoswap/.venv/bin/uvicorn crypto_exchange.app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cryptoswap
sudo systemctl status cryptoswap
```
### 4.6. Nginx
`/etc/nginx/sites-available/cryptoswap.conf`
```
server {
	listen 80;
	server_name example.com;
	location /static/ { proxy_pass http://127.0.0.1:8000/static/; }
	location / {
		proxy_pass http://127.0.0.1:8000/;
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header X-Forwarded-Proto $scheme;
	}
}
```
```bash
sudo ln -s /etc/nginx/sites-available/cryptoswap.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d example.com -m admin@example.com --agree-tos --non-interactive
```

## 5. Основные эндпоинты

## Переменные окружения
Смотри `app/core/config.py`. Рекомендуется `.env` с:
```
SECRET_KEY=генерируй_случайно
POSTGRES_HOST=db
POSTGRES_USER=crypto
POSTGRES_PASSWORD=crypto
POSTGRES_DB=crypto
REDIS_URL=redis://redis:6379/0
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=120
CORS_ORIGINS=["https://example.com"]
```

## Эндпоинты (основные)
- POST /auth/register, /auth/login, GET /auth/me
- POST /auth/promote/{user_id}/{role}
- POST /auth/kyc/submit, POST /auth/kyc/{user_id}/status
- POST /orders, GET /orders, GET /orders/{id}, POST /orders/{id}/status, GET /orders/my/list
- POST /orders/{id}/transactions, GET /orders/{id}/transactions
- GET /orders/analytics/summary
- GET /public/rates, GET /public/pairs
- CRUD: POST /currencies, PATCH /currencies/{id}, GET /currencies

## 6. Модели
Смотри `app/models/*.py` (User, KYCData, Currency, Order, Transaction, AuditLog).

## 7. Rate Limiting
Включить: `RATE_LIMIT_ENABLED=true`. Простая in-memory реализация (один процесс). Для продакшена заменить на Redis + lua/slowlog.

## 8. Безопасность (MVP рекомендации)
- Сменить SECRET_KEY перед деплоем
- Ограничить CORS строго списком доменов
- Вынести конфигурацию в `.env` и секреты в Vault/Secrets Manager
- HTTPS через Nginx + LetsEncrypt
- Логи без PII (document_id маскируется)
- Rate limit /auth/* агрессивнее, чем общий (TODO)

## 9. Метрики и здоровье
`/health` — проверка БД и Redis. `/metrics` — простые счётчики (если включено).

## 10. Типовой пользовательский поток
1. Login или Demo Login.
2. Создание заявки (лимиты без KYC).
3. Отправка KYC → оператор подтверждает.
4. Добавление транзакций, смена статусов.
5. Аналитика и управление в админке.

## 11. Тесты
`pytest -q`. Тесты используют in-memory SQLite и dependency override.

В Docker: см. раздел 2.1 (stage `test` и сервис `tests`).

## 11.1 Healthcheck
Финальный образ содержит HEALTHCHECK, обращающийся к `/health` внутри контейнера (каждые 30 сек).

## 12. Траблшутинг
| Симптом | Причина | Решение |
|---------|---------|---------|
| Белый экран | Нет валют / ошибка JS | Проверить консоль, создать валюты |
| 500 /public/rates | Нет базовой quote (USDT) | Добавить валюту USDT |
| 429 Too Many Requests | Rate limit включён | RATE_LIMIT_ENABLED=false в .env |
| getaddrinfo failed | Postgres недоступен | Исправить HOST или SQLite |
| ModuleNotFoundError crypto_exchange | Запуск из неправильного каталога | Запустить из родительского каталога или поменять импорт |
| KYC форма не скрывается | Статус не verified | /auth/kyc/{id}/status -> verified |

## 13. Что можно улучшить
- Redis based rate limiting + Sliding Window
- Расширенные метрики (Prometheus, OpenTelemetry)
- Асинхронные задачи (Celery / RQ) для обновления курсов
- Подтверждение транзакций через blockchain API
- Полные тесты с фикстурами и mock внешнего API
- Ротация и архивирование audit логов
- UI: автообновление статусов, цветовые бейджи, локализация, пагинация
 - Собрать Tailwind (CLI / JIT) в собственный файл вместо CDN

## 15. Структура фронтенда
```
app/
	templates/
		base.html        # Общий layout, подключает tailwind + main.css + base.js
		index.html       # Страница обмена, подключает index.js
		admin.html       # Админ панель, подключает admin.js + Chart.js CDN
	static/
		css/
			main.css       # Кастомные стили / утилиты / override
		js/
			base.js        # Общий JS: auth demo, навигация, звук, глобальные хелперы
			index.js       # Логика страницы обмена: курсы, заявки, KYC, транзакции
			admin.js       # Логика админки: заказы, статусы, аналитика
```
Inline-скрипты вынесены для читаемости и кеширования.
