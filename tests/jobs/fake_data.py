"""Golden job: fake data with Faker.

Usage: fake_data.py <data dir> <out dir> (both unused). Faker, seeded with `Faker.seed`, makes
names, addresses, e-mail addresses, dictionaries of strings and numbers and dates between two
fixed dates, for four locales and a two-locale `Faker`, and unique integers. No value is drawn
relative to today: ru_RU's user names, and so its e-mail addresses, may end in a year drawn
between 1970 and the clock's now, which the guest fixes and the native run does not, so the job
draws neither in ru_RU. It counts the locales it finds in its package and lists a generator's
providers, so a listing the zip served short shows.
"""

from datetime import date
from importlib.metadata import version

import faker
from faker import Faker

print("versions", f"faker={version('faker')}")
START, END = date(2020, 1, 1), date(2025, 12, 31)


def sample(fake, accounts):
    values = [fake.name(), fake.address().replace("\n", " | ")]
    if accounts:
        values += [fake.email(), fake.user_name()]
    return [
        *values,
        fake.pydict(nb_elements=4, value_types=[str, int, float]),
        fake.date_between_dates(date_start=START, date_end=END).isoformat(),
        fake.city(),
        fake.phone_number(),
    ]


Faker.seed(4321)
for locale in ("en_US", "de_DE", "ja_JP", "ru_RU"):
    fake = Faker(locale)
    for _ in range(2):
        print(locale, sample(fake, accounts=locale != "ru_RU"))
both = Faker(["en_US", "fr_FR"])
for _ in range(3):
    print("two locales", both.name(), both.email())
plain = Faker()
print("unique", sorted(plain.unique.random_int(min=1, max=20) for _ in range(10)))
print("locales", len(faker.config.AVAILABLE_LOCALES), faker.config.AVAILABLE_LOCALES[:5])
print("providers", sorted(type(p).__module__ for p in plain.get_providers()))
