# -*- coding: utf-8 -*-
"""
Payment handlers
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from decimal import Decimal
from core.logger import get_logger
from services.robokassa import RobokassaService
from services.orders import OrderService
from core.config import load_settings

router = Router(name="payment")
log = get_logger(__name__)

settings = load_settings()
robokassa = RobokassaService(settings)
order_service = OrderService(settings.SQLITE_PATH)

@router.callback_query(F.data == "pay_report")
async def pay_report(cb: CallbackQuery, state: FSMContext):
    """Обработка оплаты отчёта"""
    try:
        await cb.answer()
    except Exception as e:
        log.warning("Could not answer callback query", error=str(e))
    if not settings.ENABLE_PAYMENTS or settings.REPORT_PRICE <= 0:
        await state.update_data(order_id=None, payment_url=None)
        await cb.message.answer("Оплата временно отключена. Формирую отчет для тестирования без платежа.")
        from bot.handlers.company import generate_report
        return await generate_report(cb, state)
    
    
    # Получаем данные из состояния
    data = await state.get_data()
    query = data.get("query")
    company_name = data.get("company_name", "Неизвестная компания")
    company_inn = data.get("company_inn", query)
    
    if not query:
        await cb.message.answer("❌ Ошибка: данные компании не найдены.")
        return
    
    try:
        # Создаём заказ
        order_id = await order_service.create_order(
            user_id=cb.from_user.id,
            company_inn=company_inn,
            company_name=company_name,
            amount=Decimal(str(settings.REPORT_PRICE))
        )
        
        # Генерируем ссылку на оплату
        payment_url = robokassa.build_payment_url(
            inv_id=order_id,
            amount=Decimal(str(settings.REPORT_PRICE)),
            description=f"Отчёт по компании {company_name} (ИНН: {company_inn})",
            email=None,
            extra_params={"shp_user": str(cb.from_user.id)}
        )
        
        # Отправляем ссылку на оплату
        from bot.keyboards.main import payment_status_kb
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data="check_payment")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
        ])
        
        await cb.message.answer(
            f"💳 **Оплата отчёта**\n\n"
            f"📄 Компания: {company_name}\n"
            f"🏢 ИНН: {company_inn}\n"
            f"💰 Стоимость: {settings.REPORT_PRICE} ₽\n\n"
            f"Нажмите кнопку ниже для перехода к оплате:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        # Сохраняем order_id в состоянии
        await state.update_data(order_id=order_id, payment_url=payment_url)
        
    except Exception as e:
        log.error("Payment setup failed", error=str(e), user_id=cb.from_user.id)
        await cb.message.answer("❌ Ошибка при создании заказа. Попробуйте позже.")



@router.callback_query(F.data == "pay_report_pdf")
async def pay_report_pdf(cb: CallbackQuery, state: FSMContext):
    await state.update_data(gamma_export_as="pdf")
    return await pay_report(cb, state)


@router.callback_query(F.data == "pay_report_pptx")
async def pay_report_pptx(cb: CallbackQuery, state: FSMContext):
    await state.update_data(gamma_export_as="pptx")
    return await pay_report(cb, state)


@router.callback_query(F.data == "check_payment")
async def check_payment(cb: CallbackQuery, state: FSMContext):
    """Проверка статуса оплаты"""
    try:
        await cb.answer()
    except Exception as e:
        log.warning("Could not answer callback query", error=str(e))
    
    data = await state.get_data()
    order_id = data.get("order_id")
    
    if not order_id:
        await cb.message.answer("❌ Заказ не найден.")
        return
    
    try:
        order = await order_service.get_order(order_id)
        if not order:
            await cb.message.answer("❌ Заказ не найден.")
            return
        
        if order["status"] == "paid":
            # Заказ оплачен, запускаем генерацию отчёта
            await cb.message.answer("✅ Оплата подтверждена! Запускаю генерацию отчёта...")
            
            # Обновляем состояние с order_id
            await state.update_data(order_id=order_id)
            
            # Переходим к генерации отчёта
            from bot.handlers.company import generate_report
            await generate_report(cb, state)
            
        elif order["status"] == "pending":
            await cb.message.answer(
                "⏳ Ожидание оплаты...\n\n"
                "Если вы уже оплатили, подождите несколько минут для обработки платежа.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Проверить снова", callback_data="check_payment")],
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")]
                ])
            )
        else:
            await cb.message.answer(f"❌ Статус заказа: {order['status']}")
            
    except Exception as e:
        log.error("Payment check failed", error=str(e), user_id=cb.from_user.id)
        await cb.message.answer("❌ Ошибка при проверке оплаты.")
