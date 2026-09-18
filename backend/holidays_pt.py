"""Feriados on which the practice does not open, 2026–2028.

Every date here blocks the whole day, for every regime and every clinic — the
same effect the Sunday rule in WORK_WINDOWS already has.

Dates are written out instead of being derived from Easter at runtime so the
table can be checked line by line against the official calendar. The movable
feasts were computed once per year (see tests/test_holidays.py, which re-derives
them from Easter and fails if this table drifts).

Grouped by who declares them, because that is what decides when a group needs
revisiting: the national and regional lists are law, OBSERVED is not.
"""
from datetime import date

# Feriados nacionais obrigatórios (Lei n.º 7/2009, art. 234.º).
NATIONAL = {
    # 2026
    date(2026, 1, 1):   "Ano Novo",
    date(2026, 4, 3):   "Sexta-feira Santa",
    date(2026, 4, 5):   "Páscoa",
    date(2026, 4, 25):  "Dia da Liberdade",
    date(2026, 5, 1):   "Dia do Trabalhador",
    date(2026, 6, 4):   "Corpo de Deus",
    date(2026, 6, 10):  "Dia de Portugal",
    date(2026, 8, 15):  "Assunção de Nossa Senhora",
    date(2026, 10, 5):  "Implantação da República",
    date(2026, 11, 1):  "Todos os Santos",
    date(2026, 12, 1):  "Restauração da Independência",
    date(2026, 12, 8):  "Imaculada Conceição",
    date(2026, 12, 25): "Natal",
    # 2027
    date(2027, 1, 1):   "Ano Novo",
    date(2027, 3, 26):  "Sexta-feira Santa",
    date(2027, 3, 28):  "Páscoa",
    date(2027, 4, 25):  "Dia da Liberdade",
    date(2027, 5, 1):   "Dia do Trabalhador",
    date(2027, 5, 27):  "Corpo de Deus",
    date(2027, 6, 10):  "Dia de Portugal",
    date(2027, 8, 15):  "Assunção de Nossa Senhora",
    date(2027, 10, 5):  "Implantação da República",
    date(2027, 11, 1):  "Todos os Santos",
    date(2027, 12, 1):  "Restauração da Independência",
    date(2027, 12, 8):  "Imaculada Conceição",
    date(2027, 12, 25): "Natal",
    # 2028
    date(2028, 1, 1):   "Ano Novo",
    date(2028, 4, 14):  "Sexta-feira Santa",
    date(2028, 4, 16):  "Páscoa",
    date(2028, 4, 25):  "Dia da Liberdade",
    date(2028, 5, 1):   "Dia do Trabalhador",
    date(2028, 6, 10):  "Dia de Portugal",
    date(2028, 6, 15):  "Corpo de Deus",
    date(2028, 8, 15):  "Assunção de Nossa Senhora",
    date(2028, 10, 5):  "Implantação da República",
    date(2028, 11, 1):  "Todos os Santos",
    date(2028, 12, 1):  "Restauração da Independência",
    date(2028, 12, 8):  "Imaculada Conceição",
    date(2028, 12, 25): "Natal",
}

# Feriado da Região Autónoma dos Açores: Segunda-feira do Espírito Santo,
# the Monday after Pentecost, so it moves with Easter.
REGIONAL_ACORES = {
    date(2026, 5, 25): "Dia da Região Autónoma dos Açores",
    date(2027, 5, 17): "Dia da Região Autónoma dos Açores",
    date(2028, 6, 5):  "Dia da Região Autónoma dos Açores",
}

# Feriados municipais da Ilha Terceira. Angra do Heroísmo and Praia da Vitória
# have different dates, so this stays empty until the concelho and its dates are
# confirmed — a wrong guess here silently closes a working day.
MUNICIPAL_TERCEIRA = {}

# Terça-feira de Carnaval is NOT a statutory holiday: it is granted each year as
# tolerância de ponto. Listed because the island effectively shuts down, but kept
# separate so it is obvious this group rests on custom rather than law.
OBSERVED = {
    date(2026, 2, 17): "Terça-feira de Carnaval",
    date(2027, 2, 9):  "Terça-feira de Carnaval",
    date(2028, 2, 29): "Terça-feira de Carnaval",
}

HOLIDAYS = {**NATIONAL, **REGIONAL_ACORES, **MUNICIPAL_TERCEIRA, **OBSERVED}

# Years the table actually covers. A date outside this range is not a holiday
# merely because the table says nothing about it, and callers that care about
# the difference can check.
COVERED_YEARS = (2026, 2027, 2028)


def is_holiday(query_date):
    """True when the practice is closed all day for a feriado."""
    return query_date in HOLIDAYS


def holiday_name(query_date):
    """The feriado's name, or None when the date is a normal working day."""
    return HOLIDAYS.get(query_date)
