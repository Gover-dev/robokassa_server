# FlameRP × Robokassa — Инструкция по установке

## Структура файлов

```
robokassa_server/        ← деплоишь на Railway/Render
  app.py
  requirements.txt
  Procfile

gmod_lua/
  sv_robokassa.lua  → garrysmod/addons/adonate/lua/autorun/server/
  cl_robokassa.lua  → garrysmod/addons/adonate/lua/autorun/client/
```

---

## Шаг 1 — Регистрация в Robokassa

1. Зайди на https://merchant.robokassa.ru и зарегистрируйся
2. Создай магазин → получи **MerchantLogin**, **Password1**, **Password2**
3. В настройках магазина → **Уведомления**:
   - ResultURL: `https://ВАШ_ПРОЕКТ.railway.app/robokassa/result`
   - SuccessURL: `https://ВАШ_ПРОЕКТ.railway.app/robokassa/success`
   - FailURL: `https://ВАШ_ПРОЕКТ.railway.app/robokassa/fail`
   - Метод отправки: **POST** (или GET — app.py поддерживает оба)

---

## Шаг 2 — Деплой сервера на Railway (бесплатно)

1. Зарегистрируйся на https://railway.app (через GitHub)
2. Нажми **New Project → Deploy from GitHub repo**
3. Залей папку `robokassa_server/` в новый GitHub репозиторий
4. Railway автоматически обнаружит `Procfile` и задеплоит
5. В меню проекта: **Settings → Domains** → **Generate Domain**
   - Получишь URL вида: `https://ваш-проект.railway.app`

### Переменные окружения в Railway (Settings → Variables):
```
MERCHANT_LOGIN=ВАШ_ЛОГИН
MERCHANT_PASSWORD_1=ВАШ_ПАРОЛЬ_1
MERCHANT_PASSWORD_2=ВАШ_ПАРОЛЬ_2
DB_HOST=IP_ТВОЕГО_СЕРВЕРА
DB_USER=root
DB_PASS=ПАРОЛЬ_БД
DB_NAME=flamerp
DB_PORT=3306
```

> Чтобы читать их в app.py — замени прямые строки на `os.environ.get("MERCHANT_LOGIN")`

---

## Шаг 3 — Настройка MySQL

Убедись что MySQL на твоём игровом сервере доступен извне.
В `my.cnf` / `my.ini`:
```ini
bind-address = 0.0.0.0
```
И открой порт 3306 в фаерволе/панели хостинга.

Таблица `fl_donate_queue` создаётся автоматически при старте сервера через `sv_robokassa.lua`.

---

## Шаг 4 — Установка Lua файлов

```
sv_robokassa.lua → garrysmod/addons/adonate/lua/autorun/server/sv_robokassa.lua
cl_robokassa.lua → garrysmod/addons/adonate/lua/autorun/client/cl_robokassa.lua
```

В файлах заполни секцию НАСТРОЙКИ:
- `MERCHANT_LOGIN`, `MERCHANT_PASSWORD_1`
- `RESULT_URL`, `SUCCESS_URL`, `FAIL_URL` — твой Railway URL

---

## Шаг 5 — Подключить кнопку в донат меню

В твоём `cl_adonate.lua` добавь кнопку "Пополнить баланс":

```lua
-- Найди место где рисуется шапка/баланс и добавь:
local topupBtn = vgui.Create("DButton", parent)
topupBtn:SetText("💳 Пополнить через Robokassa")
topupBtn.DoClick = function()
    rp.donate.OpenTopupMenu()
end
```

---

## Тестирование

1. Поставь `IS_TEST = 1` в `sv_robokassa.lua`
2. Зайди в игру, открой `!donate`
3. Нажми "Пополнить" → выбери сумму
4. Откроется ссылка на тестовую страницу Robokassa
5. Оплати тестовым методом (любая карта в тест-режиме)
6. Через 15 секунд FC должны появиться

После тестирования: `IS_TEST = 0` и меняй URL в Robokassa на рабочий.

---

## Схема работы

```
[Игрок] → !donate → "Пополнить" → вводит сумму
    ↓
[GMod Server] → генерирует ссылку → отправляет клиенту
    ↓
[Клиент] → открывает браузер → платит
    ↓
[Robokassa] → POST на Railway сервер (ResultURL)
    ↓
[Python/Railway] → проверяет подпись → INSERT в fl_donate_queue
    ↓
[GMod Server] → каждые 15 сек → SELECT из очереди → начисляет FC
    ↓
[Игрок] → получает уведомление в чате ✅
```
