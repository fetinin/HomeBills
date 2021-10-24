import logging
import math
import threading
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import sheet
import storage

app = FastAPI()
g_sheet = sheet.Sheet()
readings = storage.Storage()
readings.curr.load()
readings.prev.load()

logging.basicConfig(level=logging.DEBUG)

_rates = g_sheet.get_floats("C23", "C28")
rates = {
    "cold_water": _rates[0],
    "hot_water": _rates[1],
    "drain": _rates[2],
    "el_t1": _rates[3],
    "el_t2": _rates[4],
    "el_t3": _rates[5],
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
        if readings.curr.is_some_missing:
            return "Привет! Что там по счетчикам за воду и электричество?"

        places = []
        if not (readings.curr.el_t1 or readings.curr.el_t2 or readings.curr.el_t3):
            places.append("по электричеству")

        if not (readings.curr.kitchen_cold or readings.curr.kitchen_hot):
            places.append("воды на кухне")

        if not (readings.curr.bath_hot or readings.curr.bath_cold):
            places.append("воды в ванной")

        if places:
            return f"Осталось записать показания {' и '.join(places)}."

        return f"Все показания за этот месяц уже заполнены. " \
               f"Чтобы их узнать, скажи sil <[200]> 'сколько вышло'"

    user_phrase = data["request"]["original_utterance"].lower()
    nlu = data["request"]["nlu"]
    # Обрабатываем ответ пользователя.

    if "обнови данные" in user_phrase:
        readings.curr.load()
        readings.prev.load()
        return "Актуализировала данные из таблицы. Обращайтесь."

    if "кухня" in user_phrase or "кухне" in user_phrase:
        entities = nlu["entities"]
        if len(entities) != 1 or entities[0]["type"] != "YANDEX.NUMBER":
            return "Не поняла показания счетчика"

        amount = entities[0]["value"]
        if "горячая вода" in user_phrase:
            readings.curr.kitchen_hot = str(amount)
            return f"Записала горячую воду на кухне {amount}"
        if "холодная вода" in user_phrase:
            readings.curr.kitchen_cold = str(amount)
            return f"Записала холодную воду на кухне {amount}"
        else:
            return "Не поняла, это горячая или холодная вода?"

    if "ванная" in user_phrase or "ванной" in user_phrase:
        entities = nlu["entities"]
        if len(entities) != 1 or entities[0]["type"] != "YANDEX.NUMBER":
            return "Не поняла показания счетчика"

        amount = entities[0]["value"]
        if "горячая вода" in user_phrase:
            readings.curr.bath_hot = str(amount)
            return f"Записала горячую воду в ванной: {amount}"
        if "холодная вода" in user_phrase:
            readings.curr.bath_cold = str(amount)
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

        if rate == 1:
            readings.curr.el_t1 = str(amount)
        elif rate == 2:
            readings.curr.el_t2 = str(amount)
        else:
            readings.curr.el_t3 = str(amount)

        return f"Записала электричество по тарифу {rate} как {amount}"

    if "сколько вышло" in user_phrase:
        return calc_bill()

    return f"Не поняла"


def calc_bill() -> str:
    if readings.curr.is_some_missing:
        return "У меня пока нет показаний. Продиктуй их, пожалуйста"

    missing_places = []

    missing_rates = []
    if not readings.curr.el_t1:
        missing_places.append("1")
    if not readings.curr.el_t2:
        missing_places.append("2")
    if not readings.curr.el_t3:
        missing_places.append("3")

    if missing_rates:
        if len(missing_rates) == 3:
            missing_places.append("по электричеству")
        else:
            missing_places.append(
                f"по тарифам электричества {' и '.join(missing_rates)}")

    if not readings.curr.kitchen_hot:
        missing_places.append(f"горячей воды на кухне")
    if not readings.curr.kitchen_cold:
        missing_places.append(f"холодной воды на кухне")

    if not readings.curr.bath_hot:
        missing_places.append(f"горячей воды в ванной")
    if not readings.curr.bath_cold:
        missing_places.append(f"холодной воды в ванной")

    if missing_places:
        return f"Нехватает показаний {' и '.join(missing_places)}."

    cold_water = (readings.curr.bath_cold + readings.curr.kitchen_cold) - (
            readings.prev.bath_cold + readings.prev.kitchen_cold
    )
    hot_water = (readings.curr.bath_hot + readings.curr.kitchen_hot) - (
            readings.prev.bath_hot + readings.prev.kitchen_hot
    )
    el_t1 = readings.curr.el_t1 - readings.prev.el_t1
    el_t2 = readings.curr.el_t2 - readings.prev.el_t2
    el_t3 = readings.curr.el_t3 - readings.prev.el_t3

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

    def update_data():
        readings.curr.total_cold = cold_water_price
        readings.curr.total_hot = hot_water_price
        readings.curr.total_drain = drain_price
        readings.curr.total_t1 = el_t1_price
        readings.curr.total_t2 = el_t2_price
        readings.curr.total_t3 = el_t3_price
        readings.curr.total_all = total

    threading.Thread(target=update_data).start()  # update data in background

    total_this_month_phrase = f"В этом месяце коммуналка вышла на {money_as_text(total)}."

    if readings.prev.total_all > total:
        diff = readings.prev.total_all - total
        total_tip = f"Это на {money_as_text(diff)} меньше чем в прошлом. Так держать!"
    else:
        diff = total - readings.prev.total_all
        total_tip = f"Прошлый месяц вышел дешевле, на {money_as_text(diff)}."

    return f"{total_this_month_phrase} {total_tip}"


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

def money_as_text(total: float) -> str:
    rubles, kopeek = to_money(total)
    rub_text = get_num_endings(rubles, ["рубль", "рублей", "рубля"])
    kopeek_text = get_num_endings(kopeek, ["копейка", "копеек", "копейка"])
    return f"{rubles} {rub_text} {kopeek} {kopeek_text}"

@app.on_event("shutdown")
def shutdown_handler():
    return

