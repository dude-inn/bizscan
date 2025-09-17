# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class CompanyBrief(BaseModel):
    name: str
    inn: str
    ogrn: Optional[str] = None
    region: Optional[str] = None
    url: Optional[str] = None

class FinanceYear(BaseModel):
    year: int
    revenue: Optional[str] = None  # Изменено на str для хранения форматированных значений
    profit: Optional[str] = None
    assets: Optional[str] = None
    liabilities: Optional[str] = None

class Flags(BaseModel):
    # Старые поля для совместимости
    arbitration: Optional[bool] = None
    bankruptcy: Optional[bool] = None
    exec_proceedings: Optional[bool] = None
    inspections: Optional[bool] = None
    
    # Новые правовые индикаторы
    mass_director: Optional[bool] = None
    mass_founder: Optional[bool] = None
    unreliable_address: Optional[bool] = None
    unreliable_director: Optional[bool] = None
    unreliable_founder: Optional[bool] = None
    tax_debt: Optional[bool] = None
    disqualified: Optional[bool] = None
    unreliable_supplier: Optional[bool] = None

class License(BaseModel):
    type: str
    number: Optional[str] = None
    date: Optional[str] = None
    authority: Optional[str] = None

class Founder(BaseModel):
    name: str
    share: Optional[str] = None

class CompanyFull(BaseModel):
    short_name: Optional[str] = None
    full_name: Optional[str] = None
    status: Optional[str] = None
    reg_date: Optional[str] = None
    address: Optional[str] = None
    director: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    ogrn: Optional[str] = None
    ogrn_date: Optional[str] = None
    okved_main: Optional[str] = None
    okved_additional: List[str] = Field(default_factory=list)  # Переименовано из okved_extra
    stats_codes: Dict[str, str] = Field(default_factory=dict)
    msp_status: Optional[str] = None
    tax_authority: Optional[str] = None
    founders: List[Founder] = Field(default_factory=list)  # Изменено на список объектов Founder
    contacts: Dict[str, List[str]] = Field(default_factory=dict)  # phone/email/site
    staff: Optional[str] = None
    avg_salary: Optional[str] = None
    finance: List[FinanceYear] = Field(default_factory=list)
    flags: Flags = Field(default_factory=Flags)
    licenses: List[License] = Field(default_factory=list)  # Новое поле для лицензий
    source_url: Optional[str] = None
    # Расширенные поля (не ломаем совместимость)
    authorized_capital: Optional[str] = None
    okved_main_code: Optional[str] = None
    okved_main_title: Optional[str] = None
    codes: Dict[str, str] = Field(default_factory=dict)
    finance_summary: Dict[str, Any] = Field(default_factory=dict)
    reliability: Dict[str, Any] = Field(default_factory=dict)
    executions: Dict[str, Any] = Field(default_factory=dict)
    procurements: Dict[str, Any] = Field(default_factory=dict)
    checks: Dict[str, Any] = Field(default_factory=dict)
    trademarks: Dict[str, Any] = Field(default_factory=dict)
    events: Dict[str, Any] = Field(default_factory=dict)
    registry_holder: Optional[str] = None
    headcount: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
