import asyncio
from telegram import Bot
import aiohttp
from datetime import datetime
import time

BOT_TOKEN = "8787982429:AAGpfzIibK7e58YtvAl6g5m1EG2sZtEdFYA"
CHAT_ID = 6318865778

BASE_URL = "https://agropraktika.eu/vacancies"
CHECK_INTERVAL = 75
PAGES = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

bot = Bot("8787982429:AAGpfzIibK7e58YtvAl6g5m1EG2sZtEdFYA")

previous_status = {}
previous_vacancy_count = 0

last_open_time = 0
last_error_time = 0


def log(text):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {text}", flush=True)


async def get_data(session):
    status = {}
    vacancy_count = 0

    for page in range(1, PAGES + 1):
        url = f"{BASE_URL}?page={page}"
        log(f"Проверка страницы {page}")

        try:
            async with session.get(url, headers=HEADERS) as response:

                if response.status == 403:
                    log("Ошибка 403")
                    return None, None

                html = await response.text()
                html_lower = html.lower()

                if len(html) < 1000:
                    log("Слишком маленький HTML")
                    return None, None

                # если страницы не существует (кроме первой)
                if page != 1 and f"?page={page}" not in html:
                    log(f"Страница {page} не существует")
                    continue

                # считаем вакансии (по кнопке Apply)
                count_on_page = html_lower.count("apply")
                vacancy_count += count_on_page

                log(f"Вакансий на странице {page}: {count_on_page}")

                # статус регистрации
                if "регистрация временно приостановлена" in html_lower:
                    status[page] = 1
                    log(f"Страница {page}: закрыто")
                else:
                    status[page] = 0
                    log(f"Страница {page}: ВОЗМОЖНО ОТКРЫТО")

        except Exception as e:
            log(f"Ошибка: {e}")
            return None, None

    return status, vacancy_count


async def check():
    global previous_status, previous_vacancy_count
    global last_open_time, last_error_time

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                log("Новая проверка сайта")
                current_status, vacancy_count = await get_data(session)

                if current_status is None:
                    if time.time() - last_error_time > 600:
                        last_error_time = time.time()
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text="⚠️ Сайт не отвечает или блокирует (403)"
                        )

                    await asyncio.sleep(CHECK_INTERVAL)
                    continue

                log(f"Всего вакансий: {vacancy_count}")

                # первый запуск
                if not previous_status:
                    previous_status = current_status
                    previous_vacancy_count = vacancy_count
                    log("Первичная проверка выполнена")

                else:
                    # 🚨 открылась регистрация
                    for page in current_status:
                        if (
                            page in previous_status
                            and previous_status[page] == 1
                            and current_status[page] == 0
                        ):
                            if time.time() - last_open_time > 300:
                                last_open_time = time.time()

                                log(f"🔥 ОТКРЫЛОСЬ на странице {page}")

                                for _ in range(3):
                                    await bot.send_message(
                                        chat_id=CHAT_ID,
                                        text=f"🚨 РЕГИСТРАЦИЯ ОТКРЫЛАСЬ!\nСтраница: {page}\n{BASE_URL}?page={page}"
                                    )
                                    await asyncio.sleep(1)

                    # ➕ добавили вакансию
                    if vacancy_count > previous_vacancy_count:
                        log("Добавлена вакансия")
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text="➕ Добавлена новая вакансия"
                        )

                    # ➖ удалили вакансию
                    if vacancy_count < previous_vacancy_count:
                        log("Удалили вакансию")
                        await bot.send_message(
                            chat_id=CHAT_ID,
                            text="➖ Вакансия удалена"
                        )

                    previous_status = current_status
                    previous_vacancy_count = vacancy_count

            except Exception as e:
                log(f"Критическая ошибка: {e}")
                await bot.send_message(chat_id=CHAT_ID, text=f"Ошибка: {e}")

            log(f"Жду {CHECK_INTERVAL} секунд")
            await asyncio.sleep(CHECK_INTERVAL)


async def main():
    log("Бот запущен")
    await bot.send_message(chat_id=CHAT_ID, text="🤖 Бот запущен и следит за Agropraktika 24/7")
    await check()


if __name__ == "__main__":
    asyncio.run(main())
