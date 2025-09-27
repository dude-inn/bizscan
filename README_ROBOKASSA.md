# Robokassa Integration

## Настройка

1. **Добавьте ключи в `.env`:**
```bash
# Robokassa settings
ROBOKASSA_MERCHANT_LOGIN=your_merchant_login
ROBOKASSA_PASSWORD1=your_password1
ROBOKASSA_PASSWORD2=your_password2
ROBOKASSA_IS_TEST=True
ROBOKASSA_BASE_URL=https://auth.robokassa.ru/Merchant/Index.aspx
RESULT_URL=https://your.domain/robokassa/result
SUCCESS_URL=https://your.domain/robokassa/success
FAIL_URL=https://your.domain/robokassa/fail
ROBOKASSA_REFUND_URL=https://services.robokassa.ru/PartnerRegisterService/api/Operation/RefundOperation
ROBOKASSA_PARTNER_ID=your_partner_id
```

2. **Запустите FastAPI сервер для колбеков:**
```bash
python run_api.py
```

3. **Запустите бота:**
```bash
python app.py
```

## Функции

### Оплата отчётов
- Пользователь выбирает "💳 Оплатить и сформировать отчёт"
- Создаётся заказ в БД
- Генерируется ссылка на оплату Robokassa
- После оплаты автоматически запускается генерация отчёта

### Автоматический возврат
- При ошибке генерации отчёта средства автоматически возвращаются
- Используется Robokassa Refund API
- Логируется причина возврата

### Статистика
- Команда `/stats` для админов
- Трекинг событий: поиски, отчёты, конверсия
- Ежедневная статистика и топ-часы

### Кеширование
- FSM кеш для последнего отчёта
- Флаг "building" против дублирования
- Ретраи отправки файлов при таймаутах

## API Endpoints

- `POST/GET /robokassa/result` - подтверждение платежа
- `GET /robokassa/success` - успешная оплата
- `GET /robokassa/fail` - неудачная оплата

## Безопасность

- Проверка подписи Robokassa
- Валидация параметров
- Логирование всех операций
- Защита от дублирования заказов



