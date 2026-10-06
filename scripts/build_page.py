"""Собирает страницу кейса index.html из report/case.md и расчётов scripts/model.py.

Места для инфографики отмечены в тексте комментариями <!-- fig:имя -->. Все
цифры на схемах берутся из модели — при изменении допущений страница
пересобирается без ручных правок.

Запуск:  .venv/bin/python scripts/build_page.py
"""

import base64
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import model  # noqa: E402

MD = ROOT / "report" / "case.md"
OUT = ROOT / "index.html"
REPO = "https://github.com/massimo-pazzi/b2b-value-case"
FNS_URL = "https://www.consultant.ru/document/cons_doc_LAW_55729/0e9f3c6aeb49362ca20996710a02f80c375b0ef4/"
SALARY_URL = "https://moskva.gorodrabot.ru/salaries/menedzher-po-prodazham?y=2025"
INSURANCE_URL = "https://www.nalog.gov.ru/rn77/taxation/insprem/"
# Публичный дашборд и чарты в Yandex DataLens (домен datalens.yandex разрешает встраивание).
DL = "https://datalens.yandex/"
DL_DASH = DL + "kpjn9qs3sice3"
DL_CHARTS = {"two_views": "7c69qvvq7bl4q", "price": "w1vym3y2qwfuf"}


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rub(x):
    return f"{x:,.0f}".replace(",", " ")


def mln(x, nd=1):
    return f"{x / 1e6:.{nd}f}".replace(".", ",")


def pct(x, nd=1):
    return f"{x:.{nd}f}".replace(".", ",").replace("-", "−")


def figure(title, body, note=""):
    n = f'<p class="note">{note}</p>' if note else ""
    return f'<figure class="chart"><figcaption class="chart-title">{title}</figcaption>{body}{n}</figure>'


def table(head, rows, cls=""):
    return (f'<div class="table-wrap"><table class="{cls}"><thead><tr>' + "".join(f"<th>{h}</th>" for h in head) +
            "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) +
            "</tbody></table></div>")


DEV, YEAR1, COST3 = model.costs()
BASE = 0.02


# ---------------------------------------------------------------- инфографика

def fig_summary():
    steps = [("Входящая почта", "50–200 писем в день: запросы, спам, рассылки, внутренняя переписка"),
             ("ИИ-фильтр", "отличает запрос на перевозку от остальной почты; порог настроен «не пропустить»"),
             ("Лид в CRM", "ответственный и задача со сроком 24 часа создаются сами"),
             ("Клиенту и руководителю", "автоответ за несколько минут; вечерний отчёт по всем запросам")]
    html = '<div class="flow">' + "".join(
        (f'<div class="arrow" aria-hidden="true">→</div>' if i else "") +
        f'<div class="flow-col{" core" if i == 1 else ""}"><div class="flow-h">{esc(h)}</div><p>{esc(t)}</p></div>'
        for i, (h, t) in enumerate(steps)) + "</div>"
    return figure("Что получил клиент: от письма до лида без ручной сортировки", html)


def fig_funnel():
    rows = [("Писем в год", "12–50 тыс.", "50–200 в день × 250 рабочих дней", 100),
            ("Запросов на КП в год", f"~{rub(model.REQUESTS_PER_YEAR)}", "2–6 в день", 34),
            ("Сделок в год", f"~{rub(model.REQUESTS_PER_YEAR * model.CONVERSION)}", f"конверсия {pct(model.CONVERSION * 100, 0)}%", 14),
            ("Упущено при 2% пропусков", f"~{rub(model.REQUESTS_PER_YEAR * BASE * model.CONVERSION)} сделки",
             f"≈ {mln(model.lost_revenue(BASE), 0)} млн ₽ выручки", 5)]
    html = '<div class="funnel">' + "".join(
        f'<div class="fn-row"><div class="fn-bar" style="width:{w}%"><span>{esc(v)}</span></div>'
        f'<div class="fn-l"><strong>{esc(n)}</strong><span>{esc(d)}</span></div></div>' for n, v, d, w in rows) + "</div>"
    return figure("Почтовый поток клиента: где теряются деньги", html,
                  "Оценка по данным предложения: объём писем и запросов — со слов клиента, конверсия и доля пропусков — допущения.")


def fig_alternatives():
    Y, P, N = '<span class="y">да</span>', '<span class="p">частично</span>', '<span class="n">нет</span>'
    rows = [("Запросы не теряются в общем потоке", N, P, N + " — шум в CRM", Y),
            ("Ответ за сутки ночью, в выходные, в отпуск", N, P, N, Y),
            ("В CRM попадают только запросы", "—", "—", N, Y),
            ("Масштабируется с ростом потока", N, N + " — найм линейный", Y, Y),
            ("Затраты в год", "скрытые: упущенные сделки", f"≈ {mln(model.manager_cost())} млн ₽ на одного",
             "низкие, но клиент уже пробовал", f"≈ {mln(COST3 / 3, 2)} млн ₽ в среднем за 3 года")]
    return figure("Четыре варианта, из которых выбирал клиент",
                  table(["", "Ничего не делать", "Нанять ещё менеджера", "Почта → CRM без фильтра", "<strong>ИИ-фильтр</strong>"],
                        rows, "matrix"),
                  f'Менеджер — средняя зарплата менеджера по продажам в Москве за 2025 год по вакансиям '
                  f'(<a href="{SALARY_URL}" target="_blank" rel="noopener">ГородРабот.ру</a>, '
                  f'{rub(model.MANAGER_SALARY_MONTH)} ₽ в месяц) плюс 30% <a href="{INSURANCE_URL}" target="_blank" '
                  f'rel="noopener">страховых взносов</a>, без рабочего места.')


def fig_process():
    steps = ["Письмо приходит в общий ящик", "Система забирает его не позже чем через 5 минут",
             "Отсекает внутреннюю переписку", "Модель определяет язык и оценивает, запрос ли это",
             "Выше порога — лид в CRM, ниже — в журнал для проверки", "Ответственный, задача на 24 часа, автоответ клиенту",
             "Менеджер готовит и отправляет КП", "Вечером — отчёт: сколько запросов, сколько обработано в срок"]
    html = '<ol class="steps">' + "".join(f"<li>{esc(s)}</li>" for s in steps) + "</ol>"
    return figure("Процесс после внедрения", html)


def fig_assumptions():
    rows = [("Запросов на КП в год", rub(model.REQUESTS_PER_YEAR), "~4 в день × 250 рабочих дней"),
            ("Средний чек сделки", f"{mln(model.AVG_CHECK, 0)} млн ₽", "со слов клиента: медиана 8–10 млн, диапазон 8–12 млн"),
            ("Конверсия запроса в сделку", f"{pct(model.CONVERSION * 100, 0)}%", "допущение предложения"),
            ("Доля запросов, теряемых при ручной обработке", "0,5–3%", "четыре сценария, базовый — 2%"),
            ("Рост конверсии за счёт ответа за 5 минут", f"{mln(model.EXTRA_REVENUE, 0)} млн ₽ в год", "экспертная оценка"),
            ("Экономия времени менеджеров", f"{rub(model.MANAGER_SAVING)} ₽ в год", "экспертная оценка, ~2 000 часов в год")]
    return figure("Допущения модели", table(["Показатель", "Значение", "Откуда"], rows))


def fig_decomposition():
    lr, m = model.lost_revenue(BASE), model.NET_MARGIN
    rows = [("Сохранённые сделки", f"{mln(lr)} млн ₽", f"{mln(lr * m, 2)} млн ₽", "34 млн выручки × 3,85%"),
            ("Ответ клиенту за 5 минут: рост конверсии", f"{mln(model.EXTRA_REVENUE)} млн ₽",
             f"{mln(model.EXTRA_REVENUE * m, 2)} млн ₽", "тоже выручка — та же маржа"),
            ("Время менеджеров", f"{mln(model.MANAGER_SAVING)} млн ₽", f"{mln(model.MANAGER_SAVING, 2)} млн ₽",
             "экономия затрат — без маржи"),
            ("Репутация и NPS", f"{mln(model.NPS_BENEFIT)} млн ₽", "—", "не измерить — не учитываем"),
            ("<strong>Итого в год</strong>", f"<strong>{mln(model.benefits(BASE))} млн ₽</strong>",
             f"<strong>{mln(model.benefits(BASE, m), 2)} млн ₽</strong>", "")]
    return figure("Годовой эффект в базовом сценарии: из чего он складывается",
                  table(["Поток", "По выручке, как в предложении", "По марже отрасли", "Почему так"], rows, "num txtlast"),
                  f"Затраты первого года — {mln(YEAR1, 2)} млн ₽. Отсюда окупаемость: "
                  f"{pct(model.payback(BASE)['Окупаемость, мес.'])} мес. по выручке и "
                  f"{pct(model.payback(BASE, m)['Окупаемость, мес.'])} мес. по марже.")


def fig_sensitivity():
    head = ["Конверсия запроса в сделку"] + [f"теряется {int(k * 100)}% пропущенных" for k in model.LOST_SHARES]
    rows = []
    for conv in model.CONVERSIONS:
        cells = []
        for k in model.LOST_SHARES:
            t = pct(model.threshold_margin(BASE, lost_share=k, conversion=conv) * 100)
            cells.append(f"<strong>{t}%</strong>" if (conv, k) == (model.CONVERSION, 1.0) else f"{t}%")
        rows.append([f"{int(conv * 100)}%"] + cells)
    return figure("Какую долю чека нужно терять с упущенной сделки, чтобы проект окупился за год: базовый сценарий, 2% пропусков",
                  table(head, rows, "num"),
                  "Жирным — допущения предложения: конверсия 17%, все пропущенные запросы потеряны. "
                  "Чем меньше реальные потери, тем выше порог. Расчёт — data/sensitivity.csv.")


def fig_core():
    rows = [("Логика доказательства: цена бездействия → две картины ценности → пороговая маржа", "Входные допущения: поток, чек, конверсия, доля пропусков"),
            ("Модель окупаемости и сценарии (scripts/model.py)", "Сценарии и порог под экономику конкретного клиента"),
            ("Структура предложения под четырёх читателей", "Интеграции: конкретная почта и CRM клиента"),
            ("Аргументы против «ничего не делать» и «почта → CRM без фильтра»", "Обучение модели на архиве писем клиента и подбор порога"),
            ("Асимметрия цены ошибок как принцип настройки", "Развёртывание: свой контур или облако подрядчика")]
    return figure("Что может тиражироваться, а что кастомная разработка",
                  table(["Тиражируется", "Кастомная разработка"], rows))


def fig_two_views():
    names = [n for n, _ in model.SCENARIOS]
    mx = max(model.payback(m, model.NET_MARGIN)["Окупаемость, мес."] for _, m in model.SCENARIOS)
    html = '<div class="pairs">'
    for name, miss in model.SCENARIOS:
        a = model.payback(miss)["Окупаемость, мес."]
        b = model.payback(miss, model.NET_MARGIN)["Окупаемость, мес."]
        html += (f'<div class="pair"><div class="pr-l">{esc(name)}<span>{pct(miss * 100)}% пропусков</span></div><div class="pr-bars">'
                 f'<div class="pb"><div class="bar s1" style="width:{a / mx * 100:.1f}%"></div><span>{pct(a)} мес.</span></div>'
                 f'<div class="pb"><div class="bar s2" style="width:{b / mx * 100:.1f}%"></div><span>{pct(b)} мес.</span></div></div></div>')
    html += '</div><div class="legend"><span><i class="sw s1"></i>по выручке, как в предложении</span>' \
            '<span><i class="sw s2"></i>по чистой рентабельности воздушного транспорта</span></div>'
    return figure("Срок окупаемости в двух картинах ценности, месяцы", html,
                  f'Чистая рентабельность — 4% к себестоимости, или 3,85% выручки: ФНС, <a href="{FNS_URL}" target="_blank" '
                  'rel="noopener">рентабельность по видам деятельности за 2024 год</a>, ОКВЭД 51. Расчёт — scripts/model.py.')


def fig_threshold():
    W, H, x0, x1, yt, yb = 760, 330, 50, 600, 16, 290
    mlo, mhi, plo, phi = 2, 45, 0, 36
    X = lambda m: x0 + (m - mlo) / (mhi - mlo) * (x1 - x0)
    Y = lambda p: yb - (min(p, phi) - plo) / (phi - plo) * (yb - yt)
    out = []
    for p in range(0, 37, 6):
        out.append(f'<line class="grid" x1="{x0}" x2="{x1}" y1="{Y(p):.1f}" y2="{Y(p):.1f}"/>'
                   f'<text class="tick" x="{x0 - 8}" y="{Y(p) + 4:.1f}" text-anchor="end">{p}</text>')
    for m in range(5, 46, 5):
        out.append(f'<text class="tick" x="{X(m):.1f}" y="{yb + 18}" text-anchor="middle">{m}%</text>')
    out.append(f'<line class="target" x1="{x0}" x2="{x1}" y1="{Y(12):.1f}" y2="{Y(12):.1f}"/>'
               f'<text class="band-label" x="{x0 + 6}" y="{Y(12) - 6:.1f}">окупаемость за год</text>')
    fx = X(model.NET_MARGIN * 100)
    out.append(f'<line class="median" x1="{fx:.1f}" x2="{fx:.1f}" y1="{yt}" y2="{yb}"/>'
               f'<text class="band-label" x="{fx + 5:.1f}" y="{yt + 10}">чистая рентабельность отрасли</text>')
    cls = ["s4", "s3", "s1", "s2"]
    ends = []
    for (name, miss), c in zip(model.SCENARIOS, cls):
        pts = [(m / 4, model.payback(miss, m / 400)["Окупаемость, мес."]) for m in range(mlo * 4, mhi * 4 + 1)]
        pts = [(m, p) for m, p in pts if p <= phi]
        path = " ".join(f"{X(m):.1f},{Y(p):.1f}" for m, p in pts)
        out.append(f'<polyline class="line {c}" points="{path}"/>')
        ends.append([Y(pts[-1][1]), name])
        t = model.threshold_margin(miss) * 100
        if t <= mhi:
            out.append(f'<circle class="dot {c}" cx="{X(t):.1f}" cy="{Y(12):.1f}" r="5"><title>{esc(name)}: окупаемость за год при марже {pct(t)}%</title></circle>')
    ends.sort()
    for i in range(1, len(ends)):              # раздвигаем подписи, чтобы не наезжали
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 14)
    for y, name in ends:
        out.append(f'<text class="label" x="{x1 + 8}" y="{y + 4:.1f}">{esc(name)}</text>')
    svg = f'<div class="chart-scroll"><svg viewBox="0 0 {W} {H + 10}" role="img" aria-label="Срок окупаемости в зависимости от маржи">{"".join(out)}</svg></div>'
    t = model.threshold_margin(BASE) * 100
    return figure("Сколько месяцев окупается проект в зависимости от того, какую долю чека клиент теряет с упущенной сделки",
                  svg, "Как читать: каждая линия — один сценарий доли пропущенных запросов. По горизонтали — какую долю "
                  "стоимости упущенной сделки компания теряет в деньгах, то есть её маржа с этой сделки; по вертикали — "
                  "за сколько месяцев при такой марже окупается проект. Чем выше маржа, тем дороже каждая потерянная "
                  "сделка и тем быстрее окупаемость. Пунктир — окупаемость за год: точка, где линия его пересекает, — "
                  "пороговая маржа сценария. Например, в базовом сценарии (2% пропусков) проект окупается за год, если "
                  f"с упущенной сделки компания теряет хотя бы {pct(t)}% её стоимости. Вертикальная линия — чистая "
                  "рентабельность воздушного транспорта по ФНС (3,85%): это нижняя граница, реальная потеря с рейса выше.")


def fig_price():
    tiles = [(f"{mln(YEAR1, 2)} млн ₽", "бюджет первого года с резервом, без НДС"),
             (f"{YEAR1 / model.AVG_CHECK:.0%}".replace("%", " %"), "одной средней сделки клиента"),
             (f"{sum(w for _, w, _ in model.STAGES)} недели", "от старта до сдачи"),
             ("50 / 50", "аванс и оплата после тестирования и акта")]
    kp = '<div class="kpis">' + "".join(
        f'<div class="kpi"><div class="kpi-v">{v}</div><div class="kpi-l">{esc(l)}</div></div>' for v, l in tiles) + "</div>"
    rows = [(n, f"{w} нед.", f"{rub(c)} ₽") for n, w, c in model.STAGES] + \
           [("Резерв на непредвиденные расходы, 10%", "", f"{rub(DEV * model.RISK_SHARE)} ₽"),
            ("<strong>Затраты первого года</strong>", "", f"<strong>{rub(YEAR1)} ₽</strong>"),
            ("Сопровождение во 2-й и 3-й год", "", f"{rub(model.SUPPORT_PER_YEAR)} ₽ в год")]
    return figure("Цена и структура предложения", kp + table(["Статья", "Срок", "Стоимость"], rows, "price"),
                  "Стоимостные показатели изменены по соображениям конфиденциальности; соотношения между статьями сохранены.")


def fig_stakeholders():
    rows = [("Коммерческий директор", "Сколько сделок мы теряем?", "Цена бездействия, ответ клиенту за минуты, отчёт каждый вечер"),
            ("Финансовый директор", "Сколько это стоит и когда вернётся?", "Пороговая маржа, оплата этапами, резерв в бюджете"),
            ("ИТ", "Где живут данные и что нужно от нас?", "Развёртывание в своём контуре, требования к серверу, журнал операций"),
            ("Менеджеры", "Не станет ли больше работы?", "В CRM только запросы, задачи создаются сами, сортировки нет")]
    return figure("Вопрос каждого участника решения и ответ в предложении", table(["Кто", "Его вопрос", "Ответ в предложении"], rows))


def fig_sources():
    return (f'<ol class="sources"><li>ФНС России, «Рентабельность проданных товаров, продукции, работ, услуг и рентабельность '
            f'активов организаций по видам экономической деятельности» за 2024 год — <a href="{FNS_URL}" target="_blank" '
            f'rel="noopener">КонсультантПлюс</a></li>'
            f'<li>Средняя зарплата менеджера по продажам в Москве за 2025 год по вакансиям — <a href="{SALARY_URL}" '
            f'target="_blank" rel="noopener">ГородРабот.ру</a></li>'
            f'<li>Тарифы страховых взносов — <a href="{INSURANCE_URL}" target="_blank" rel="noopener">ФНС России</a></li>'
            f'<li>Открытая бухгалтерская отчётность клиента — для проверки масштаба модели (ссылка не приводится, '
            f'чтобы не раскрывать клиента)</li>'
            f'<li>Коммерческое предложение по проекту (не публикуется): допущения о '
            f'клиенте, состав работ, сроки и условия оплаты</li></ol>'
            f'<p class="note">Расчёт окупаемости и данные для графиков — <a href="{REPO}/blob/main/scripts/model.py" '
            f'target="_blank" rel="noopener">scripts/model.py</a> и <a href="{REPO}/tree/main/data" target="_blank" '
            f'rel="noopener">data/</a>; интерактивные графики — <a href="{DL_DASH}" target="_blank" '
            f'rel="noopener">дашборд в Yandex DataLens</a>.</p>')


def author_block():
    img = base64.b64encode((ROOT / "assets/img/author.jpg").read_bytes()).decode()
    return (f'<div class="author"><img src="data:image/jpeg;base64,{img}" alt="Максим Поципух" width="64" height="64">'
            '<span>Максим Поципух</span></div>')


def dl_link(chart_id):
    return (f'<p class="dl-link"><a href="{DL}{chart_id}" target="_blank" rel="noopener">'
            f'Открыть интерактивно в DataLens ↗</a></p>')


def dl_embed(chart_id, title, height, note):
    src = f"{DL}{chart_id}?_embedded=1&_no_controls=1"
    return (f'<figure class="chart live"><figcaption class="chart-title">{title}</figcaption>'
            f'<iframe src="{src}" title="{esc(title)}" loading="lazy" style="height:{height}px"></iframe>'
            f'<p class="note">{note} Если не загрузилось — '
            f'<a href="{DL}{chart_id}" target="_blank" rel="noopener">откройте его в DataLens</a>.</p></figure>')


# Живая вставка — там, где наведение даёт то, чего нет на статичном графике: точный срок для любой маржи.
DL_EMBEDS = {"threshold": ("5a46bibknjyko", "Тот же расчёт в DataLens: маржа от 2 до 40%", 420,
                           "Живой график: наведите на линию, чтобы увидеть срок окупаемости при любой марже; "
                           "щелчок по сценарию в легенде скрывает его линию.")}

FIGS = {"summary": fig_summary, "funnel": fig_funnel, "alternatives": fig_alternatives, "process": fig_process,
        "assumptions": fig_assumptions, "decomposition": fig_decomposition, "sensitivity": fig_sensitivity,
        "two_views": fig_two_views, "threshold": fig_threshold, "price": fig_price,
        "stakeholders": fig_stakeholders, "core": fig_core, "sources": fig_sources}

CSS = """
:root{
  --bg:#f5f6f7; --surface:#ffffff; --ink:#18202a; --ink-2:#4b5662; --muted:#6c7782;
  --rule:#d9dee3; --accent:#1f5fae; --accent-soft:#e6eef8; --neutral:#aab2bb;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#a07800; --ok:#1b8a5a; --warn:#a36b00; --no:#8a929b;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){ color-scheme:dark;
    --bg:#11161c; --surface:#171d24; --ink:#e7ebef; --ink-2:#b5bec7; --muted:#8c96a0;
    --rule:#2c343d; --accent:#79a9e8; --accent-soft:#1c2632; --neutral:#5d6670;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --ok:#3fbf86; --warn:#e0a640; --no:#7d8791; }
}
:root[data-theme="dark"]{ color-scheme:dark;
  --bg:#11161c; --surface:#171d24; --ink:#e7ebef; --ink-2:#b5bec7; --muted:#8c96a0;
  --rule:#2c343d; --accent:#79a9e8; --accent-soft:#1c2632; --neutral:#5d6670;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --ok:#3fbf86; --warn:#e0a640; --no:#7d8791; }
body{margin:0; background:var(--bg); color:var(--ink); font-family:"Golos Text",system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:17px; line-height:1.62; padding-inline:16px; padding-block:40px 64px;}
.page{max-width:48rem; margin:0 auto;} a{color:var(--accent);}
.eyebrow{font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:12.5px; letter-spacing:.06em; text-transform:uppercase; color:var(--accent); margin:0 0 14px;}
h1{font-size:clamp(1.7rem,4.2vw,2.3rem); line-height:1.18; font-weight:700; letter-spacing:-.01em; text-wrap:balance; margin:0 0 16px;}
h2{font-size:1.28rem; line-height:1.3; font-weight:650; text-wrap:balance; margin:46px 0 12px; padding-top:22px; border-top:1px solid var(--rule);}
.author{display:flex; align-items:center; gap:12px; margin:4px 0 16px; font-weight:600; font-size:15px;}
.author img{width:64px; height:64px; border-radius:50%; object-fit:cover; border:1px solid var(--rule);}
.author + p em{color:var(--ink-2); font-size:15px;}
p{margin:0 0 14px;} strong{font-weight:620;} hr{display:none;}
.chart{margin:16px 0 22px; background:var(--surface); border:1px solid var(--rule); border-radius:6px; padding:14px 16px 12px;}
.chart-title{font-weight:600; font-size:14.5px; margin-bottom:10px; line-height:1.4;}
.note{font-size:12.5px; color:var(--muted); margin:10px 0 0; line-height:1.5;}
.flow{display:grid; grid-template-columns:1fr auto 1fr auto 1fr auto 1fr; gap:8px; align-items:stretch;}
.flow-col{border:1px solid var(--rule); border-radius:6px; padding:10px 12px; font-size:13px; line-height:1.45;} .flow-col p{margin:0;}
.flow-h{font-weight:650; font-size:12.5px; text-transform:uppercase; letter-spacing:.04em; color:var(--ink-2); margin-bottom:6px;}
.flow-col.core{background:var(--accent-soft); border-color:var(--accent);} .flow-col.core .flow-h{color:var(--accent);}
.arrow{align-self:center; color:var(--muted); font-size:20px;}
@media (max-width:700px){ .flow{grid-template-columns:1fr;} .arrow{transform:rotate(90deg); justify-self:center;} }
.funnel{display:grid; gap:8px;}
.fn-row{display:grid; grid-template-columns:1fr 1fr; gap:12px; align-items:center;}
.fn-bar{background:var(--s1); color:#fff; border-radius:4px; padding:7px 10px; font-weight:600; font-size:14px; min-width:9em; justify-self:end;}
.fn-row:last-child .fn-bar{background:var(--s2);}
.fn-l{font-size:13.5px; line-height:1.35;} .fn-l span{display:block; color:var(--muted); font-size:12.5px;}
.table-wrap{overflow-x:auto;}
table{border-collapse:collapse; width:100%; font-size:14px;}
th,td{text-align:left; padding:8px 10px 8px 0; border-bottom:1px solid var(--rule); vertical-align:top;}
th{font-weight:600; color:var(--ink-2); font-size:12.5px;}
.matrix td:first-child{font-weight:550; min-width:11em;} .matrix th:last-child,.matrix td:last-child{background:var(--accent-soft); padding-left:8px;}
.price td:last-child{text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap;}
.y{color:var(--ok); font-weight:600;} .p{color:var(--warn); font-weight:600;} .n{color:var(--no);}
.steps{margin:0; padding-left:1.4em; columns:2; column-gap:28px; font-size:14px;} .steps li{margin-bottom:6px; break-inside:avoid;}
@media (max-width:640px){ .steps{columns:1;} }
.pairs{display:grid; gap:12px;}
.pair{display:grid; grid-template-columns:minmax(9em,13em) 1fr; gap:12px; align-items:center; font-size:13.5px;}
.pr-l span{display:block; color:var(--muted); font-size:12px;}
.pr-bars{display:grid; gap:4px;}
.pb{display:flex; align-items:center; gap:8px; font-size:12.5px; font-variant-numeric:tabular-nums;} .pb span{white-space:nowrap;}
.bar{height:14px; border-radius:3px; min-width:3px;} .bar.s1{background:var(--s1);} .bar.s2{background:var(--s2);}
.legend{display:flex; flex-wrap:wrap; gap:6px 16px; font-size:12.5px; color:var(--ink-2); margin-top:12px;}
.legend span{display:inline-flex; align-items:center; gap:6px;} .sw{display:inline-block; width:11px; height:11px; border-radius:2px;}
.sw.s1{background:var(--s1);} .sw.s2{background:var(--s2);}
.chart-scroll{overflow-x:auto;} .chart svg{display:block; width:100%; min-width:560px; height:auto;}
.grid{stroke:var(--rule); stroke-width:1;} .tick{fill:var(--muted); font-size:11px; font-family:"IBM Plex Mono",ui-monospace,monospace;}
.target{stroke:var(--ink-2); stroke-width:1.2; stroke-dasharray:5 4;} .median{stroke:var(--muted); stroke-width:1; stroke-dasharray:2 3;}
.band-label{fill:var(--muted); font-size:11px;} .label{fill:var(--ink); font-size:12px;}
.line{fill:none; stroke-width:2.2;} .line.s1{stroke:var(--s1);} .line.s2{stroke:var(--s2);} .line.s3{stroke:var(--s3);} .line.s4{stroke:var(--s4);}
.dot{stroke:var(--surface); stroke-width:2;} .dot.s1{fill:var(--s1);} .dot.s2{fill:var(--s2);} .dot.s3{fill:var(--s3);} .dot.s4{fill:var(--s4);}
.kpis{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-bottom:12px;}
.kpi{border:1px solid var(--rule); border-radius:6px; padding:12px 14px;}
.kpi-v{font-size:1.4rem; font-weight:700; font-variant-numeric:tabular-nums;} .kpi-l{font-size:13px; color:var(--ink-2); margin-top:4px; line-height:1.4;}
.num td:not(:first-child),.num th:not(:first-child){text-align:right; font-variant-numeric:tabular-nums;}
.txtlast td:last-child,.txtlast th:last-child{text-align:left;}
.dl-link{margin:-12px 0 22px; font-size:13.5px;}
.chart.live iframe{display:block; width:100%; border:0; border-radius:4px; background:#fff;}
.sources{font-size:14.5px; line-height:1.55; padding-left:1.5em;}
@media (max-width:520px){ body{font-size:16px; padding-block:24px 48px;} .pair,.fn-row{grid-template-columns:1fr;} .fn-bar{justify-self:start;} }
"""


def main():
    html = markdown.markdown(MD.read_text(encoding="utf-8"), extensions=["tables"])
    title, rest = html.split("</h1>", 1)
    html = title + "</h1>\n" + author_block() + rest
    for name, fn in FIGS.items():
        marker = f"<!-- fig:{name} -->"
        assert marker in html, f"нет места для блока {name}"
        block = fn()
        if name in DL_EMBEDS:
            block += dl_embed(*DL_EMBEDS[name])
        elif name in DL_CHARTS:
            block += dl_link(DL_CHARTS[name])
        html = html.replace(marker, block)
    page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Окупаемость без маржи</title>
<meta name="description" content="Портфолио-кейс: как обосновать окупаемость ИИ-проекта для грузовой авиакомпании, не зная маржи клиента, — сделать видимыми потери от бездействия и превратить ROI в неравенство, которое клиент проверяет сам">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
</head>
<body>
<main class="page">
<p class="eyebrow">Портфолио-кейс: обоснование стратегического проекта · Максим Поципух · Сентябрь 2025</p>
{html}
</main>
</body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(page) // 1024} КБ, блоков: {len(FIGS)}")


if __name__ == "__main__":
    main()
