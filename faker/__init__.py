import random
import string
import uuid
from decimal import Decimal


class Faker:
    def first_name(self):
        return random.choice(
            ["Alex", "Sam", "Jamie", "Taylor", "Jordan", "Morgan", "Casey"]
        )

    def last_name(self):
        return random.choice(
            ["Smith", "Johnson", "Lee", "Brown", "Garcia", "Davis", "Martinez"]
        )

    def email(self):
        return f"user{random.randint(1000, 9999)}@example.com"

    def state(self):
        return random.choice(
            ["Tehran", "Fars", "Isfahan", "Mazandaran", "Khorasan", "Khuzestan"]
        )

    def city(self):
        return random.choice(["Tehran", "Shiraz", "Isfahan", "Tabriz", "Mashhad"])

    def zipcode(self):
        return f"{random.randint(10000, 99999)}"

    def address(self):
        return f"{random.randint(1, 999)} Main St"

    def sentence(self, nb_words=3):
        words = [self.word() for _ in range(nb_words)]
        return " ".join(words).capitalize() + "."

    def paragraph(self, nb_sentences=2):
        return " ".join(self.sentence() for _ in range(nb_sentences))

    def word(self):
        return random.choice(
            ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
        )

    def random_int(self, min=0, max=9999):
        return random.randint(min, max)

    def pydecimal(self, left_digits=3, right_digits=2, positive=True):
        left = random.randint(1, 10**left_digits - 1)
        right = random.randint(0, 10**right_digits - 1)
        sign = 1 if positive else random.choice([-1, 1])
        return Decimal(sign * left) + (Decimal(right) / (10**right_digits))

    def ean(self):
        return "".join(str(random.randint(0, 9)) for _ in range(13))

    def slug(self):
        return f"slug-{uuid.uuid4().hex[:8]}"

    def text(self, max_nb_chars=200):
        base = "Lorem ipsum dolor sit amet"
        return (base * ((max_nb_chars // len(base)) + 1))[:max_nb_chars]

    def pystr(self, max_chars=20):
        return "".join(random.choice(string.ascii_letters) for _ in range(max_chars))

    def pyint(self, min_value=0, max_value=999999):
        return random.randint(min_value, max_value)

    def numerify(self, text="########"):
        return "".join(
            str(random.randint(0, 9)) if char == "#" else char for char in text
        )

