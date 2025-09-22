# -*- coding: utf-8 -*-
"""
Рендер секции с проверками - максимально простой
"""
from typing import Dict, Any
from .simple_company_renderer import format_value, format_dict_item


def render_inspect(data: Dict[str, Any]) -> str:
    """
    Рендерит проверки с сокращенным форматом
    
    Args:
        data: Данные проверок
        
    Returns:
        Информация о проверках
    """
    lines = []
    aliases = load_inspect_aliases()
    
    # Обрабатываем данные проверок
    if 'data' in data and data['data']:
        try:
            header_added = False
            records = data['data'].get('Записи', []) if isinstance(data['data'], dict) else data['data']
            if isinstance(records, list) and records:
                # Фильтруем проверки за последние 5 лет
                current_year = 2025
                min_year = current_year - 5  # 2020
                filtered_records = []
                for inspection in records:
                    if not isinstance(inspection, dict):
                        continue
                    inspection_date = inspection.get('ДатаНач', '')
                    if inspection_date:
                        try:
                            year = int(str(inspection_date).split('-')[0])
                            if year >= min_year:
                                filtered_records.append(inspection)
                        except (ValueError, IndexError):
                            filtered_records.append(inspection)
                    else:
                        filtered_records.append(inspection)
                records = filtered_records

                lines.append("ПРОВЕРКИ")
                lines.append("=" * 50)
                header_added = True

                # Статистика (защита от не-словарей)
                total_inspections = len(records)
                completed = sum(1 for insp in records if isinstance(insp, dict) and insp.get('Заверш', False))
                with_violations = sum(1 for insp in records if isinstance(insp, dict) and insp.get('Наруш', False))
                planned = sum(1 for insp in records if isinstance(insp, dict) and insp.get('ТипРасп') == 'Плановая проверка')

                lines.append(f"Всего проверок: {total_inspections}")
                lines.append(f"Завершено: {completed}")
                lines.append(f"С нарушениями: {with_violations}")
                lines.append(f"Плановых: {planned}")
                lines.append("")

                # Список проверок
                lines.append("Список проверок:")
                for i, inspection in enumerate(records, 1):
                    if not isinstance(inspection, dict):
                        continue
                    org = inspection.get('ОргКонтр') or {}
                    org_name = org.get('Наим') if isinstance(org, dict) else str(org)
                    if isinstance(org_name, str) and len(org_name) > 50:
                        org_name = org_name[:47] + "..."
                    goal = inspection.get('Цель', 'N/A')
                    if isinstance(goal, str) and len(goal) > 60:
                        goal = goal[:57] + "..."
                    violations = inspection.get('Наруш', False)
                    violations_text = "Нарушения: есть" if violations else "Нарушений нет"
                    inspection_line = (
                        f"{i}. {inspection.get('Номер', 'N/A')} | {inspection.get('Статус', 'N/A')} | "
                        f"{inspection.get('ТипРасп', 'N/A')} | {inspection.get('ДатаНач', 'N/A')} | "
                        f"{org_name} | {goal} | {violations_text}"
                    )
                    lines.append(inspection_line)
            else:
                lines.append("ПРОВЕРКИ")
                lines.append("=" * 50)
                lines.append("Данные недоступны")
        except Exception as e:
            if not lines or lines[-1] != "=" * 50:
                lines.append("ПРОВЕРКИ")
                lines.append("=" * 50)
            lines.append(f"Ошибка обработки данных: {str(e)}")
    else:
        lines.append("ПРОВЕРКИ")
        lines.append("=" * 50)
        lines.append("Данные недоступны")
    
    return "\n".join(lines)


def load_inspect_aliases() -> Dict[str, str]:
    """Алиасы для проверок"""
    return {
        'company': 'Компания',
        'data': 'Данные проверок',
        'meta': 'Метаданные',
        # Добавить остальные поля по мере необходимости
    }