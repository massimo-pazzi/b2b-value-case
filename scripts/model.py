"""Модель ценности коммерческого предложения: стоимость, выгоды, окупаемость.

Все входные допущения — в блоке ниже, с указанием происхождения. Стоимостные
показатели проекта уменьшены вдвое относительно реального предложения по
соображениям конфиденциальности; структура и логика расчёта сохранены.

Результат — CSV в data/ (для страницы кейса и для Yandex DataLens).
Запуск:  python3 scripts/model.py
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# --- Стоимость проекта (₽, без НДС; в реальном КП вдвое больше) ----------------
STAGES = [  # этап, недели, стоимость
    ("Проектирование", 2, 684_625 / 2),
    ("Разработка", 17, 5_138_349 / 2),
    ("Внедрение", 1, 575_037 / 2),
    ("Тестирование и отладка", 3, 1_132_789 / 2),
]
RISK_SHARE = 0.10            # резерв на непредвиденные расходы — как в КП
SUPPORT_PER_YEAR = 400_000   # сопровождение во 2-й и 3-й год: в КП 800 000 (следует из расчёта за 3 года)

# --- Допущения о клиенте (из предложения, помечены там как консервативная оценка) --
REQUESTS_PER_YEAR = 1000     # ~4 запроса на КП в день × 250 рабочих дней
AVG_CHECK = 10_000_000       # средний чек сделки, ₽ (медиана 8–10 млн, диапазон 8–12 млн)
CONVERSION = 0.17            # конверсия запроса в сделку — допущение КП
EXTRA_REVENUE = 1_000_000    # рост конверсии за счёт автоответа за 5 минут, ₽/год — экспертная оценка
MANAGER_SAVING = 300_000     # экономия времени менеджеров, ₽/год — экспертная оценка
NPS_BENEFIT = 500_000        # «репутация и NPS», ₽/год — экспертная оценка, в расчёте по марже не учитывается

# --- Чувствительность (в предложении не было, добавлено в кейсе) ------------------
# Доля безвозвратно потерянных среди пропущенных запросов: клиент чартера на 10 млн
# пишет в несколько компаний и может напомнить о себе, часть пропусков возвращается.
# В модели предложения эта доля молча принята за 100%.
LOST_SHARES = [1.0, 0.75, 0.5, 0.25]
CONVERSIONS = [0.10, 0.17, 0.25]

# --- Альтернатива «нанять ещё менеджера» ------------------------------------------
# ГородРабот.ру: средняя зарплата менеджера по продажам в Москве за 2025 год по вакансиям —
# 133 393 ₽ в месяц. Страховые взносы работодателя — 30% (НК РФ, ст. 425, в пределах базы).
MANAGER_SALARY_MONTH = 133_393
INSURANCE_RATE = 0.30

# --- Маржа ----------------------------------------------------------------------
# ФНС, 2024: рентабельность проданных товаров, работ, услуг в воздушном транспорте
# (ОКВЭД 51) — 4,0% (прибыль от продаж к себестоимости). Доля прибыли в выручке:
FNS_PROFITABILITY = 0.04
NET_MARGIN = FNS_PROFITABILITY / (1 + FNS_PROFITABILITY)

SCENARIOS = [("Крайне консервативный", 0.005), ("Консервативный", 0.01), ("Базовый", 0.02), ("Умеренный", 0.03)]


def costs():
    dev = sum(c for _, _, c in STAGES)
    year1 = dev * (1 + RISK_SHARE)
    return dev, year1, year1 + 2 * SUPPORT_PER_YEAR


def lost_revenue(miss_share):
    return REQUESTS_PER_YEAR * miss_share * CONVERSION * AVG_CHECK


def benefits(miss_share, margin=None):
    """Годовая выгода. margin=None — как в КП: выручка целиком плюс все экспертные оценки."""
    if margin is None:
        return lost_revenue(miss_share) + EXTRA_REVENUE + MANAGER_SAVING + NPS_BENEFIT
    return (lost_revenue(miss_share) + EXTRA_REVENUE) * margin + MANAGER_SAVING


def payback(miss_share, margin=None):
    _, year1, cost3 = costs()
    b = benefits(miss_share, margin)
    return {"Выгода в год, ₽": b, "ROI 1-го года, %": (b - year1) / year1 * 100,
            "Окупаемость, мес.": year1 / b * 12, "ROI за 3 года, %": (3 * b - cost3) / cost3 * 100}


def threshold_margin(miss_share, months=12, lost_share=1.0, conversion=CONVERSION):
    """Минимальная доля маржи в упущенной выручке, при которой проект окупается за months месяцев.

    lost_share — доля безвозвратно потерянных среди пропущенных запросов, conversion — конверсия
    запроса в сделку. Обе входят в выручку множителем, поэтому порог растёт обратно пропорционально.
    """
    _, year1, _ = costs()
    need = year1 * 12 / months - MANAGER_SAVING
    lost = REQUESTS_PER_YEAR * miss_share * conversion * lost_share * AVG_CHECK
    return need / (lost + EXTRA_REVENUE)


def manager_cost():
    """Годовая стоимость одного менеджера по продажам: зарплата плюс страховые взносы, без рабочего места."""
    return MANAGER_SALARY_MONTH * 12 * (1 + INSURANCE_RATE)


def write(name, rows):
    DATA.mkdir(exist_ok=True)
    with open(DATA / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"data/{name}: {len(rows)} строк")


def main():
    dev, year1, cost3 = costs()
    write("costs.csv", [{"Этап": n, "Недели": w, "Стоимость, ₽": round(c)} for n, w, c in STAGES] +
          [{"Этап": "Резерв на непредвиденные расходы (10%)", "Недели": "", "Стоимость, ₽": round(dev * RISK_SHARE)},
           {"Этап": "Сопровождение, годы 2–3", "Недели": "", "Стоимость, ₽": round(2 * SUPPORT_PER_YEAR)}])
    rows = []
    for name, miss in SCENARIOS:
        for view, margin in (("По выручке, как в КП", None), ("По марже отрасли (3,85%)", NET_MARGIN)):
            p = payback(miss, margin)
            rows.append({"Сценарий": name, "Доля пропущенных запросов, %": miss * 100,
                         "Пропущенных запросов в год": round(REQUESTS_PER_YEAR * miss),
                         "Упущенная выручка, ₽/год": round(lost_revenue(miss)), "Взгляд": view,
                         **{k: round(v) if "₽" in k else round(v, 1) for k, v in p.items()},
                         "Пороговая маржа для окупаемости за год, %": round(threshold_margin(miss) * 100, 1)})
    write("scenarios.csv", rows)
    curve = []
    for name, miss in SCENARIOS:
        for m in range(2, 41):
            curve.append({"Сценарий": name, "Маржа с упущенной сделки, %": m,
                          "Окупаемость, мес.": round(payback(miss, m / 100)["Окупаемость, мес."], 1)})
    write("payback_by_margin.csv", curve)
    sens = []
    for conv in CONVERSIONS:
        for share in LOST_SHARES:
            sens.append({"Конверсия запроса в сделку, %": round(conv * 100),
                         "Доля безвозвратно потерянных среди пропущенных, %": round(share * 100),
                         "Упущенная выручка в базовом сценарии, ₽/год":
                             round(REQUESTS_PER_YEAR * 0.02 * conv * share * AVG_CHECK),
                         "Пороговая маржа для окупаемости за год, %":
                             round(threshold_margin(0.02, lost_share=share, conversion=conv) * 100, 1)})
    write("sensitivity.csv", sens)
    print(f"этапы {dev:,.0f}; год 1 {year1:,.0f}; 3 года {cost3:,.0f}; доля прибыли {NET_MARGIN:.4f}")
    print(f"затраты первого года — {year1 / AVG_CHECK:.0%} одной средней сделки; "
          f"в среднем за 3 года {cost3 / 3:,.0f} ₽/год; менеджер {manager_cost():,.0f} ₽/год")


if __name__ == "__main__":
    main()
