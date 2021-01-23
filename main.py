import logging
import math
import shelve
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

logging.basicConfig(level=logging.DEBUG)

storage = shelve.open("home_bills.db")
if not storage.keys():
    storage.update(
        {
            "electro": {},
            "bath": {},
            "kitchen": {},
        }
    )

rates = {
    "cold_water": 42.3,
    "hot_water": 205.15,
    "drain": 30.9,
    "el_t1": 6.72,
    "el_t2": 2.32,
    "el_t3": 5.66,
}


@app.route("/", methods=["POST"])
async def main(request: Request):
    logging.info("Request: %r", request.json)

    data = await request.json()
    response = {
        "version": data["version"],
        "session": data["session"],
        "response": {"text": handle_dialog(data)},
    }

    logging.info("Response: %r", response)

    return JSONResponse(response)


def handle_dialog(data: dict[str, Any]) -> str:
    if data["session"]["new"]:
        if not any(v for v in storage.values()):
            return "Привет! Что там по счетчикам за воду и электричество?"

        places = []
        if not storage["electro"]:
            places.append("по электричеству")

        if not storage["kitchen"]:
            places.append("воды на кухне")

        if not storage["bath"]:
            places.append("воды в ванной")

        if places:
            return f"Осталось записать показания {' и '.join(places)}."

        return f"Все показания за этот месяц уже заполнены. " \
               f"Чтобы их узнать, скажи sil <[200]> 'сколько вышло'"

    user_phrase = data["request"]["original_utterance"].lower()
    nlu = data["request"]["nlu"]
    # Обрабатываем ответ пользователя.

    if "кухня" in user_phrase or "кухне" in user_phrase:
        entities = nlu["entities"]
        if len(entities) != 1 or entities[0]["type"] != "YANDEX.NUMBER":
            return "Не поняла показания счетчика"

        amount = entities[0]["value"]
        if "горячая вода" in user_phrase:
            storage["kitchen"] = {**storage["kitchen"], **{"hot_water": amount}}
            return f"Записала горячую воду на кухне {amount}"
        if "холодная вода" in user_phrase:
            storage["kitchen"] = {**storage["kitchen"], **{"cold_water": amount}}
            return f"Записала холодную воду на кухне {amount}"
        else:
            return "Не поняла, это горячая или холодная вода?"

    if "ванная" in user_phrase or "ванной" in user_phrase:
        entities = nlu["entities"]
        if len(entities) != 1 or entities[0]["type"] != "YANDEX.NUMBER":
            return "Не поняла показания счетчика"

        amount = entities[0]["value"]
        if "горячая вода" in user_phrase:
            storage["bath"] = {**storage["bath"], **{"hot_water": amount}}
            return f"Записала горячую воду в ванной: {amount}"
        if "холодная вода" in user_phrase:
            storage["bath"] = {**storage["bath"], **{"cold_water": amount}}
            return f"Записала холодную воду в ванной {amount}"
        else:
            return "Не поняла, это горячая или холодная вода?"

    if "электричество" in user_phrase or "свет" in user_phrase:
        entities = nlu["entities"]
        if len(entities) < 2 or not all(e["type"] == "YANDEX.NUMBER" for e in entities):
            return "Не поняла о чем вы"

        rate, amount = entities[0]["value"], entities[1]["value"]
        if 0 <= rate > 3:
            return "Не поняла, это по какому тарифу? Есть тарифы: 1, 2 и 3"

        storage["electro"] = {**storage["electro"], **{rate: amount}}
        return f"Записала электричество по тарифу {rate} как {amount}"

    if "сколько вышло" in user_phrase:
        return calc_bill()

    return f"Не поняла"


def calc_bill() -> str:
    if not any(v for v in storage.values()):
        return "У меня пока нет показаний. Продиктуй их, пожалуйста"

    missing_places = []
    if not (electro := storage["electro"]):
        missing_places.append("по электричеству")
    else:
        if len(electro) < 3:
            missing_rates = (str(m) for m in {1, 2, 3}.difference(electro.keys()))
            missing_places.append(
                f"по тарифам электричества {' и '.join(missing_rates)}"
            )

    if not (kitchen := storage["kitchen"]):
        missing_places.append("воды на кухне")
    else:
        if not kitchen["hot_water"]:
            missing_places.append(f"горячей воды на кухне")
        if not kitchen["cold_water"]:
            missing_places.append(f"холодной воды на кухне")

    if not (bath := storage["bath"]):
        missing_places.append("воды в ванной")
    else:
        if not bath["hot_water"]:
            missing_places.append(f"горячей воды на кухне")
        if not bath["cold_water"]:
            missing_places.append(f"холодной воды на кухне")

    if missing_places:
        return f"Нехватает показаний {' и '.join(missing_places)}."

    cold_water = (storage["bath"]["cold_water"] + storage["kitchen"]["cold_water"]) - (
        14 + 11.6
    )
    hot_water = (storage["bath"]["hot_water"] + storage["kitchen"]["hot_water"]) - (
        7 + 5.5
    )
    el_t1 = storage["electro"][1] - 352
    el_t2 = storage["electro"][2] - 198
    el_t3 = storage["electro"][3] - 530

    cold_water_price = cold_water * rates["cold_water"]
    hot_water_price = hot_water * rates["hot_water"]
    drain_price = (cold_water + hot_water) * rates["drain"]
    el_t1_price = el_t1 * rates["el_t1"]
    el_t2_price = el_t2 * rates["el_t2"]
    el_t3_price = el_t3 * rates["el_t3"]

    total = sum(
        (
            cold_water_price,
            hot_water_price,
            drain_price,
            el_t1_price,
            el_t2_price,
            el_t3_price,
        )
    )

    rubles, kopeek = to_money(total)
    rub_text = get_num_endings(rubles, ["рубль", "рублей", "рубля"])
    kopeek_text = get_num_endings(rubles, ["копейка", "копеек", "копейка"])

    return (
        f"В этом месяце коммуналка вышла на {rubles} {rub_text} {kopeek} {kopeek_text}."
    )


def to_money(money: float) -> (int, int):
    kopeek, rubles = math.modf(money)
    rubles = int(rubles)
    kopeek = kopeek * 100
    return rubles, int(kopeek)


def get_num_endings(number: int, words: list[str]) -> str:
    if number % 10 == 0 or (11 <= number % 100 <= 19):
        return words[1]  # копейка

    if delim := number % 10:
        if delim == 1:
            return words[0]
        if delim < 5:
            return words[2]

    return words[1]


@app.on_event("shutdown")
def shutdown_handler():
    storage.close()
