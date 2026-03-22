from __future__ import annotations

import re
import json
from pathlib import Path
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional


@dataclass(frozen=True)
class SubscriptionCandidate:
    name: str
    price: float
    billing_cycle: str
    next_payment_date: date


RUS_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
    "янв.": 1,
    "февр.": 2,
    "марта": 3,
    "апр.": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "авг.": 8,
    "сент.": 9,
    "окт.": 10,
    "нояб.": 11,
    "дек.": 12,
}

ENG_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

script_dir = Path(__file__).parent
json_file_path = script_dir / 'supported_services.json'


def load_data():
    with json_file_path.open('r', encoding='utf-8') as f:
        data = json.load(f)
    return data['service'], data['addWord']


def normalize_service_name(name: str) -> str:
    s = str(name).lower().strip()
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _parse_amount(amount_str: str) -> Optional[float]:
    s = amount_str.strip().replace(" ", "").replace("\u00a0", "")
    if not s:
        return None

    last_dot = s.rfind(".")
    last_comma = s.rfind(",")
    if last_dot == -1 and last_comma == -1:
        try:
            return float(s)
        except Exception:
            return None

    if last_dot > last_comma:
        decimal_sep = "."
        thousand_sep = ","
    else:
        decimal_sep = ","
        thousand_sep = "."

    s = s.replace(thousand_sep, "")
    if decimal_sep == ",":
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def extract_price(text: str) -> Optional[float]:
    t = text or ""

    # Символы/слова валют.
    patterns = [
        # Валюта перед числом (€ 200, ₽ 199.99, $ 500 и т. д.)
        r"€\s*([0-9][0-9.,\s]*[0-9])",
        r"₽\s*([0-9][0-9.,\s]*[0-9])",
        r"\$\s*([0-9][0-9.,\s]*[0-9])",  # $ экранирован
        r"£\s*([0-9][0-9.,\s]*[0-9])",

        # Число + валюта (200$, 199.99 ₽, 500 EUR и т. д.)
        r"(\d+(?:[.,]\d+)?)\s*($|₽|€|£|₴|₸)",  # валюта после числа
        r"(\d+(?:[.,]\d+)?)\s*(ARS|RUB|EUR|USD|GBP|KZT|TRY)\b",
        r"\w(ARS|RUB|EUR|USD|GBP|KZT|TRY)\s*(\d+(?:[.,]\d+)?)",

        # Число + словесное обозначение валюты
        r"(\d+(?:[.,]\d+)?)\s*(rubles|ruble|roubles|руб|руб\.|рублей|рубли|dollar|dollars|euro|euros)\b"
    ]
    for pat in patterns:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            return _parse_amount(m.group(1))

    m = re.search(r"\bИтого\b.*?([0-9][0-9.,\s]*)", t, flags=re.IGNORECASE | re.DOTALL)
    if m:
        return _parse_amount(m.group(1))

    return None


def extract_billing_cycle(text: str) -> str:
    t = (text or "").lower()
    if any(k in t for k in ["yearly", "per year", "в год", "/год", "год ", "nitro yearly", "once per year", "годly", "year"]):
        return "yearly"
    if any(k in t for k in ["monthly", "per month", "в месяц", "once per month", "месяц", "month"]):
        return "monthly"
    return "monthly"


def _add_months(d: date, months: int) -> date:
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    first_next_month = date(y, m, 1) + timedelta(days=32)
    last_day = date(first_next_month.year, first_next_month.month, 1) - timedelta(days=1)
    return date(y, m, min(d.day, last_day.day))


def add_cycle(d: date, billing_cycle: str) -> date:
    if billing_cycle == "yearly":
        try:
            return date(d.year + 1, d.month, d.day)
        except ValueError:
            return date(d.year + 1, d.month, 28)
    return _add_months(d, 1)


def _parse_rus_date(match: re.Match) -> Optional[date]:
    day = int(match.group("day"))
    month_raw = match.group("month").lower().strip()
    year_raw = match.groupdict().get("year")
    month = RUS_MONTHS.get(month_raw)
    if not month:
        return None
    if year_raw:
        year = int(year_raw)
    else:
        year = None
    try:
        if year is None:
            return date(2000, month, day)
        return date(year, month, day)
    except Exception:
        return None


def _parse_any_date(text: str, default_year: int) -> Optional[date]:
    t = text or ""

    # ISO
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return date(y, mo, d)

    m = re.search(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b", t)
    if m:
        d = int(m.group(1))
        mo = int(m.group(2))
        y_raw = int(m.group(3))
        y = y_raw if y_raw >= 1000 else 2000 + y_raw
        return date(y, mo, d)

    # 3 марта 2026 / 17.09.25
    m = re.search(
        r"\b(?P<day>\d{1,2})\s*(?P<month>[а-яёa-zA-Z]+\.)?\s*(?P<month2>января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|октября|сент.|\w+)\b",
        t,
        flags=re.IGNORECASE,
    )
    m2 = re.search(
        r"\b(?P<day>\d{1,2})\s+(?P<month>января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|янв\.|февр\.|апр\.|авг\.|сент\.|окт\.|нояб\.|дек\.)\s*(?P<year>\d{4})?\b",
        t,
        flags=re.IGNORECASE,
    )
    if m2:
        d0 = _parse_rus_date(m2)
        if d0:
            y = m2.group("year")
            if y:
                return d0
            return date(default_year, d0.month, d0.day)

    m3 = re.search(
        r"\b(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(?P<day>\d{1,2})(?:,\s*)?(?P<year>\d{4})\b",
        t,
        flags=re.IGNORECASE,
    )
    if m3:
        month = ENG_MONTHS.get(m3.group("month").lower().strip("."))
        if not month:
            return None
        return date(int(m3.group("year")), month, int(m3.group("day")))

    return None


def _extract_date_near_keyword(
        text: str,
        keyword_pattern: str,
        default_year: int,
) -> Optional[date]:
    if not text:
        return None
    m = re.search(keyword_pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    window = text[m.end(): m.end() + 80]
    d = _parse_any_date(window, default_year=default_year)
    if d:
        return d
    window2 = text[m.end(): m.end() + 200]
    return _parse_any_date(window2, default_year=default_year)


def detect_service(text: str):
    t = (text or "").lower().split()
    services, addwords = load_data()
    found_service = []

    for service in services:
        if service in t:
            for word in addwords:
                if word in t:
                    found_service.append(service)
                    break

    if found_service:
        return f"{found_service[0]}".title()
    else:
        return None


def parse_subscription_candidate(
        subject: str,
        text: str,
        received_at: datetime,
) -> Optional[SubscriptionCandidate]:
    combined = f"{subject}\n{text}".strip()
    service = detect_service(combined)
    if not service:
        return None

    price = extract_price(combined)
    if price is None:
        return None

    billing_cycle = extract_billing_cycle(combined)

    default_year = received_at.year
    next_date = None
    payment_date = None

    next_date = _extract_date_near_keyword(
        combined,
        r"(auto-?renews\s+on|billed\s+for.*?\s+on|will\s+convert.*?\s+on)\s+",
        default_year=default_year,
    )

    payment_date = _extract_date_near_keyword(
        combined,
        r"(Дата\s+платежа|Дата\s+платежа:|Payment\s+Date|Дата\s+платежа\s*:)[:\s]*",
        default_year=default_year,
    )

    if payment_date is None:
        payment_date = _extract_date_near_keyword(
            combined,
            r"(Списание\s+денег|Дата\s+и\s+время|Списание\s+денег\s+за\s+подписку)[:\s]*",
            default_year=default_year,
        )

    if payment_date is None and service == "Yandex Plus":
        payment_date = _extract_date_near_keyword(
            combined,
            r"(Смена|Смена\s+\w*?)[:\s]*",
            default_year=default_year,
        )

    if next_date:
        next_payment_date = next_date
    elif payment_date:
        next_payment_date = add_cycle(payment_date, billing_cycle)
    else:
        next_payment_date = add_cycle(received_at.date(), billing_cycle)

    return SubscriptionCandidate(
        name=service,
        price=price,
        billing_cycle=billing_cycle,
        next_payment_date=next_payment_date,
    )
