# BizScan Bot (Telegram, Python 3.11, aiogram 3)

Профессиональный Telegram-бот для проверки компаний с парсингом **rusprofile.ru**.
- Запуск без серверов: **long polling**
- Поиск по **ИНН** и **наименованию** с **пагинацией**
- Два отчёта: **бесплатный** (базовые поля) и **платный** (полный, все данные)
- **PDF генерация** с красивым дизайном (сине-белая палитра)
- Структурированные текстовые отчёты с эмодзи и секциями
- Оплата: заглушка с будущей интеграцией **ЮKassa**
- Все настройки — в `.env` файле

## Быстрый старт

1) Установите зависимости:
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2) Создайте `.env` файл на основе `.env.example`:
```bash
cp .env.example .env
```

Заполните обязательные поля в `.env`:
- `BOT_TOKEN` - токен вашего Telegram бота
- `RUSPROFILE_SESSID` - ID сессии подписчика rusprofile
- `RUSPROFILE_CSRF` - CSRF токен подписчика rusprofile
- `BRAND_LINK` - ссылка на ваш канал/группу

3) Запуск бота:
```bash
python app.py
```

### Pre-commit (кодстайл)

Установите git‑хуки для авто‑линтинга и форматирования (ruff, black):

```bash
pip install pre-commit
pre-commit install
```

Запустить вручную на всём репозитории:

```bash
pre-commit run --all-files
```

## Новые возможности

### PDF отчёты
- **Красивый дизайн** в сине-белой палитре
- **Обложка** с названием компании и основными реквизитами
- **Структурированные секции** с карточками и таблицами
- **Автоматическая пагинация** и нумерация страниц
- **Zebra-таблицы** для финансовых данных

#### Unicode‑шрифты (DejaVu)

Для корректного отображения кириллицы в PDF используем DejaVu Sans Condensed.

1) Положите шрифты в `assets/fonts/`:
   - `DejaVuSansCondensed.ttf`
   - `DejaVuSansCondensed-Bold.ttf`

   Можно скачать автоматически:
   ```bash
   python download_fonts.py
   ```

2) В коде `reports/pdf.py` шрифты подключаются автоматически (uni=True). Если шрифты не найдены, генерация PDF прерывается, а бот отправляет текстовый отчёт вместо PDF (graceful fallback).

3) Не используем курсив, пока нет файла `DejaVuSansCondensed-Oblique.ttf`.

## Шрифты для PDF (кириллица)

- Быстрая установка:
  ```bash
  python download_fonts.py
  ```
  Скрипт скачает `DejaVuSansCondensed.ttf` и `DejaVuSansCondensed-Bold.ttf` в `assets/fonts/`.

- Если нет интернета/прокси — положите файлы вручную в `assets/fonts/`:
  - `DejaVuSansCondensed.ttf`
  - `DejaVuSansCondensed-Bold.ttf`

- Без этих шрифтов PDF не соберётся (бот отправит текстовый отчёт как graceful fallback).

## Настройки окружения (.env)

Создайте `.env` на основе `.env.example` и заполните обязательные переменные:

- `BOT_TOKEN` — токен Telegram-бота
- `RUSPROFILE_SESSID` — sessionid подписчика rusprofile (для повышенной стабильности)
- `RUSPROFILE_CSRF` — csrftoken подписчика rusprofile
- `BRAND_LINK` — ссылка на ваш бренд/канал, выводится в подписи PDF

Пример создания:
```bash
cp .env.example .env
# затем отредактируйте .env
```

### Улучшенный парсинг
- **Модульная архитектура** с отдельными extractors и validators
- **Конфигурируемые лейблы** в `scraping/labels.yaml`
- **Валидация данных** (ИНН, ОГРН, КПП, даты)
- **Дедупликация контактов** и нормализация
- **Расширенные правовые индикаторы**

### UX улучшения
- **Индикаторы загрузки** "⏳ Формирую отчёт..."
- **Кнопки скачивания PDF** после генерации отчёта
- **Структурированные текстовые отчёты** с эмодзи
- **Обработка ошибок** с понятными сообщениями

> Примечание: Парсинг выполняется напрямую с rusprofile.ru. Соблюдайте их условия использования и не превышайте разумные лимиты запросов.
