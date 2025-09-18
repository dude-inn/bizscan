# -*- coding: utf-8 -*-
"""
Доменные модели для агрегации данных о компаниях
"""
from datetime import date, datetime
from typing import Literal, Optional, List, Dict
from decimal import Decimal

from pydantic import BaseModel, Field


class CompanyBase(BaseModel):
    """Базовая информация о компании"""
    inn: str = Field(..., description="ИНН компании")
    ogrn: Optional[str] = Field(None, description="ОГРН компании")
    kpp: Optional[str] = Field(None, description="КПП компании")
    name_full: str = Field(..., description="Полное наименование")
    name_short: Optional[str] = Field(None, description="Краткое наименование")
    registration_date: Optional[date] = Field(None, description="Дата регистрации")
    liquidation_date: Optional[date] = Field(None, description="Дата ликвидации")
    status: Literal["ACTIVE", "LIQUIDATING", "LIQUIDATED", "UNKNOWN"] = Field(
        "UNKNOWN", description="Статус компании"
    )
    okved: Optional[str] = Field(None, description="Основной ОКВЭД")
    address: Optional[str] = Field(None, description="Адрес")
    address_qc: Optional[str] = Field(None, description="Код качества адреса от DaData")
    management_name: Optional[str] = Field(None, description="ФИО руководителя")
    management_post: Optional[str] = Field(None, description="Должность руководителя")
    authorized_capital: Optional[str] = Field(None, description="Уставный капитал")


class MsmeInfo(BaseModel):
    """Информация о статусе МСП"""
    is_msme: bool = Field(False, description="Является ли субъектом МСП")
    category: Optional[Literal["micro", "small", "medium"]] = Field(
        None, description="Категория МСП"
    )
    period: Optional[str] = Field(None, description="Период данных (YYYY-MM)")


class BankruptcyInfo(BaseModel):
    """Информация о банкротстве"""
    has_bankruptcy_records: bool = Field(False, description="Есть ли записи о банкротстве")
    records: List[Dict] = Field(default_factory=list, description="Список записей")


class ArbitrationInfo(BaseModel):
    """Информация об арбитражных делах"""
    total: int = Field(0, description="Общее количество дел")
    cases: List[Dict] = Field(default_factory=list, description="Список дел")


class FinanceSnapshot(BaseModel):
    """Финансовые показатели компании"""
    period: str = Field(..., description="Период (YYYY или YYYY-MM)")
    revenue: Optional[Decimal] = Field(None, description="Выручка")
    net_profit: Optional[Decimal] = Field(None, description="Чистая прибыль")
    assets: Optional[Decimal] = Field(None, description="Активы")
    equity: Optional[Decimal] = Field(None, description="Капитал")
    liabilities_short: Optional[Decimal] = Field(None, description="Краткосрочные обязательства")
    liabilities_long: Optional[Decimal] = Field(None, description="Долгосрочные обязательства")
    source: Optional[str] = Field(None, description="Источник данных (GIRBO)")


class ProcurementStats(BaseModel):
    """Статистика по госзакупкам"""
    total_contracts: int = Field(0, description="Общее количество контрактов")
    total_amount: Optional[Decimal] = Field(None, description="Общая сумма контрактов")
    last_contract_date: Optional[date] = Field(None, description="Дата последнего контракта")
    source: Optional[str] = Field(None, description="Источник данных (ZAKUPKI)")


class License(BaseModel):
    """Лицензия компании"""
    registry: Literal["FSRAR"] = Field(..., description="Реестр лицензий")
    number: str = Field(..., description="Номер лицензии")
    activity: Optional[str] = Field(None, description="Вид деятельности")
    issued_at: Optional[date] = Field(None, description="Дата выдачи")
    valid_to: Optional[date] = Field(None, description="Дата окончания")
    status: Optional[str] = Field(None, description="Статус лицензии")


class CompanyAggregate(BaseModel):
    """Агрегированная информация о компании"""
    base: CompanyBase = Field(..., description="Базовая информация")
    msme: Optional[MsmeInfo] = Field(None, description="Информация о МСП")
    bankruptcy: Optional[BankruptcyInfo] = Field(None, description="Информация о банкротстве")
    arbitration: Optional[ArbitrationInfo] = Field(None, description="Информация об арбитраже")
    finances: List[FinanceSnapshot] = Field(default_factory=list, description="Финансовые показатели")
    procurement: Optional[ProcurementStats] = Field(None, description="Статистика по госзакупкам")
    licenses: List[License] = Field(default_factory=list, description="Лицензии")
    fetched_at: datetime = Field(default_factory=datetime.now, description="Время получения данных")
    sources: Dict[str, str] = Field(default_factory=dict, description="Источники данных")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
        }