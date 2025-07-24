import csv
import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class Timer:
    """Класс для отслеживания времени выполнения"""

    def __init__(self, name=""):
        self.name = name
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = time.time()
        print(f"🕐 [{self.name}] Начато в {datetime.now().strftime('%H:%M:%S')}")

    def stop(self):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        print(f"✅ [{self.name}] Завершено за {self.format_duration(duration)}")
        return duration

    def format_duration(self, seconds):
        if seconds < 60:
            return f"{seconds:.2f} сек"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}м {secs:.1f}с"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours}ч {minutes}м {secs:.1f}с"


class PriceListParser:
    def __init__(self, headless=True, fast_mode=True):
        """
        Инициализация парсера

        Args:
            headless (bool): Запуск браузера в фоновом режиме
            fast_mode (bool): Включить режим быстрого парсинга
        """
        self.url = (
            "https://n729879.yclients.com/company/929887/personal/select-services?o="
        )
        self.driver = None
        self.data = []
        self.fast_mode = fast_mode
        self.total_timer = Timer("Общее время парсинга")
        self.setup_driver(headless)

    def setup_driver(self, headless=True):
        """Настройка веб-драйвера Chrome с оптимизациями"""
        setup_timer = Timer("Настройка драйвера")
        setup_timer.start()

        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")

        # Оптимизации для скорости
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        # Оптимизации для fast_mode (НЕ отключаем JavaScript!)
        if self.fast_mode:
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=TranslateUI")
            chrome_options.add_argument("--disable-ipc-flooding-protection")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")

            # Отключаем загрузку ресурсов, но оставляем JS
            prefs = {
                "profile.managed_default_content_settings.images": 2,  # Блокировать изображения
                "profile.managed_default_content_settings.stylesheets": 2,  # Блокировать CSS
                "profile.managed_default_content_settings.cookies": 1,  # Разрешить куки
                "profile.managed_default_content_settings.javascript": 1,  # ВАЖНО: Разрешить JS
                "profile.managed_default_content_settings.plugins": 2,
                "profile.managed_default_content_settings.popups": 2,
                "profile.managed_default_content_settings.geolocation": 2,
                "profile.managed_default_content_settings.media_stream": 2,
                "profile.managed_default_content_settings.notifications": 2,
            }
            chrome_options.add_experimental_option("prefs", prefs)

        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            # Скрипт для скрытия webdriver всегда выполняем
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            # Настраиваем время ожидания
            wait_time = 3 if self.fast_mode else 5
            self.driver.implicitly_wait(wait_time)

            setup_timer.stop()
        except Exception as e:
            print(f"Ошибка при инициализации драйвера: {e}")
            print("Убедитесь, что ChromeDriver установлен и доступен в PATH")
            raise

    def wait_for_page_load(self, timeout=30):
        """Оптимизированное ожидание загрузки страницы"""
        load_timer = Timer("Загрузка страницы")
        load_timer.start()

        # Уменьшаем timeout для быстрого режима
        if self.fast_mode:
            timeout = 20

        try:
            # Ждем основные элементы
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("Базовая структура загружена")

            # Ждем когда появятся контейнеры
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".inner-container"))
            )
            print("Контейнеры найдены")

        except TimeoutException:
            print("Не удалось дождаться загрузки контейнеров")
            return False

        # Даем время на инициализацию JS
        initial_wait = 1 if self.fast_mode else 3
        time.sleep(initial_wait)

        print("Выполняем прокрутку для загрузки всего контента...")
        self.scroll_to_load_all_content()

        load_timer.stop()
        return True

    def scroll_to_load_all_content(self):
        """Улучшенная прокрутка страницы для полной загрузки контента"""
        scroll_timer = Timer("Прокрутка страницы")
        scroll_timer.start()

        # Параметры прокрутки для быстрого режима
        if self.fast_mode:
            scroll_step = 800
            scroll_delay = 0.1
            pause_every = 5  # Пауза каждые N шагов
            pause_duration = 0.3
        else:
            scroll_step = 500
            scroll_delay = 0.5
            pause_every = 3
            pause_duration = 1.0

        last_height = self.driver.execute_script("return document.body.scrollHeight")
        current_position = 0
        scroll_count = 0

        # Более умная логика прокрутки
        while True:
            # Прокручиваем
            current_position += scroll_step
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")
            scroll_count += 1

            time.sleep(scroll_delay)

            # Периодически делаем паузу для загрузки контента
            if scroll_count % pause_every == 0:
                time.sleep(pause_duration)

            # Проверяем высоту документа
            new_height = self.driver.execute_script("return document.body.scrollHeight")

            # Если достигли конца или высота не изменилась
            if current_position >= new_height:
                if new_height > last_height:
                    print(
                        f"Обнаружен новый контент. Высота: {last_height} -> {new_height}"
                    )
                    last_height = new_height
                    # Продолжаем прокрутку с новой высотой
                    continue
                else:
                    # Достигли конца, делаем финальную прокрутку
                    self.driver.execute_script(f"window.scrollTo(0, {new_height});")
                    time.sleep(pause_duration)
                    break

            # Обновляем последнюю высоту
            if new_height > last_height:
                last_height = new_height

        # Дополнительная проверка - прокручиваем до самого конца и обратно
        final_height = self.driver.execute_script("return document.body.scrollHeight")
        self.driver.execute_script(f"window.scrollTo(0, {final_height});")
        time.sleep(0.5)

        # Возвращаемся наверх
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.5)

        print(f"Прокрутка завершена. Финальная высота: {final_height}px")
        scroll_timer.stop()

    def wait_for_dynamic_content(self):
        """Ожидание загрузки динамического контента"""
        content_timer = Timer("Ожидание динамического контента")
        content_timer.start()

        previous_count = 0
        stable_count = 0
        max_stable = 3 if self.fast_mode else 5

        for attempt in range(10):  # Максимум 10 попыток
            # Считаем количество контейнеров
            containers = self.driver.find_elements(By.CSS_SELECTOR, ".inner-container")
            current_count = len(containers)

            if current_count > previous_count:
                print(f"Загружено контейнеров: {current_count}")
                previous_count = current_count
                stable_count = 0
            else:
                stable_count += 1

            # Если количество стабильно, завершаем ожидание
            if stable_count >= max_stable:
                print(f"Контент стабилизировался на {current_count} контейнерах")
                break

            time.sleep(0.5 if self.fast_mode else 1.0)

        content_timer.stop()
        return previous_count

    def parse_services(self):
        """Оптимизированный парсинг услуг по контейнерам"""
        parse_timer = Timer("Парсинг услуг")
        parse_timer.start()

        # Дополнительное ожидание динамического контента
        container_count = self.wait_for_dynamic_content()

        # Находим все контейнеры одним запросом
        containers_timer = Timer("Поиск контейнеров")
        containers_timer.start()

        containers = self.driver.find_elements(
            By.CSS_SELECTOR, ".inner-container.ng-star-inserted"
        )
        if not containers:
            containers = self.driver.find_elements(By.CLASS_NAME, "inner-container")

        containers_timer.stop()
        print(f"Найдено контейнеров для парсинга: {len(containers)}")

        if len(containers) == 0:
            print("⚠️ Контейнеры не найдены! Проверьте селекторы.")
            return False

        total_services = 0
        processed_containers = 0

        # Batch обработка для ускорения
        batch_size = 15 if self.fast_mode else 5

        for i in range(0, len(containers), batch_size):
            batch_timer = Timer(f"Обработка пакета {i//batch_size + 1}")
            batch_timer.start()

            batch = containers[i : i + batch_size]

            for j, container in enumerate(batch):
                container_index = i + j
                try:
                    # Быстрая проверка наличия категории
                    category_name = self.extract_category_from_container(container)

                    if not category_name:
                        continue

                    # Ускоренное извлечение услуг
                    services = self.extract_services_from_container(
                        container, category_name
                    )
                    total_services += len(services)
                    processed_containers += 1

                    if (
                        not self.fast_mode or container_index % 25 == 0
                    ):  # Уменьшаем вывод в быстром режиме
                        print(
                            f"  Контейнер {container_index + 1}: {category_name} ({len(services)} услуг)"
                        )

                except Exception as e:
                    if not self.fast_mode:
                        print(f"Ошибка в контейнере {container_index + 1}: {e}")
                    continue

            batch_timer.stop()

        print(f"\nОбработано контейнеров: {processed_containers}")
        print(f"Всего извлечено услуг: {total_services}")

        parse_timer.stop()
        return len(self.data) > 0

    def extract_category_from_container(self, container):
        """Быстрое извлечение категории"""
        category_selectors = [
            ".label.category-title",
            ".category-title",
            ".service_category_title",
            ".category-label",
            "h2",
            "h3",
        ]

        for selector in category_selectors:
            try:
                category_elements = container.find_elements(By.CSS_SELECTOR, selector)
                if category_elements:
                    category_text = category_elements[0].text.strip()
                    if category_text:
                        return category_text
            except:
                continue

        return None

    def extract_services_from_container(self, container, category_name):
        """Оптимизированное извлечение услуг"""
        services = []

        # Быстрый поиск карточек с расширенными селекторами
        service_selectors = [
            ".card-content-container",
            ".service-card",
            ".service-item",
            ".list-item",
            ".service",
        ]

        service_cards = []
        for selector in service_selectors:
            service_cards = container.find_elements(By.CSS_SELECTOR, selector)
            if service_cards:
                break

        if not service_cards:
            # Пробуем найти через более общие селекторы
            service_cards = container.find_elements(
                By.CSS_SELECTOR, "div[class*='card']"
            )

        for card in service_cards:
            try:
                service_data = self.extract_service_data_from_card(card, category_name)
                if service_data:
                    services.append(service_data)
                    self.data.append(service_data)
            except:
                continue

        return services

    def extract_service_data_from_card(self, card, category_name):
        """Быстрое извлечение данных из карточки"""
        try:
            # Получаем весь текст карточки сразу для быстрого анализа
            card_text = card.text.strip()
            if not card_text:
                return None

            # Название услуги - расширенный список селекторов
            service_name = ""
            name_selectors = [
                ".title-block__title",
                ".service-title",
                ".service-name",
                ".title",
                "h3",
                "h4",
                "h5",
                ".name",
            ]

            for selector in name_selectors:
                try:
                    elements = card.find_elements(By.CSS_SELECTOR, selector)
                    if elements and elements[0].text.strip():
                        service_name = elements[0].text.strip()
                        break
                except:
                    continue

            if not service_name:
                return None

            # Быстрое извлечение остальных данных
            duration = ""
            description = ""
            price = ""

            # Длительность - расширенные селекторы
            duration_selectors = [
                ".comment__seance-length",
                ".duration",
                ".comment",
                ".time",
                ".length",
            ]

            for selector in duration_selectors:
                try:
                    elements = card.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        text = elements[0].text.strip()
                        if text and not any(
                            word in text.lower()
                            for word in ["цена", "₽", "руб", "стоимость"]
                        ):
                            duration = text
                            break
                except:
                    continue

            # Цена - расширенные селекторы
            price_selectors = [".price-range", ".price", ".cost", ".amount", ".sum"]

            for selector in price_selectors:
                try:
                    elements = card.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        text = elements[0].text.strip()
                        if text and ("₽" in text or "руб" in text or text.isdigit()):
                            price = text
                            break
                except:
                    continue

            # Если цену не нашли, быстрый поиск в тексте
            if not price:
                import re

                price_patterns = [
                    r"\d+(?:\s*\d+)*\s*[-–—]?\s*\d*(?:\s*\d+)*\s*[₽руб]",
                    r"\d+\s*[-–—]?\s*\d*\s*р\b",
                    r"от\s+\d+",
                    r"\d+\s*руб",
                ]

                for pattern in price_patterns:
                    price_match = re.search(pattern, card_text, re.IGNORECASE)
                    if price_match:
                        price = price_match.group(0).strip()
                        break

            return {
                "category": category_name,
                "service": service_name,
                "duration": duration,
                "description": description,
                "price": price,
            }

        except Exception as e:
            if not self.fast_mode:
                print(f"Ошибка извлечения данных: {e}")
            return None

    def save_to_csv(self, filename="price_list.csv"):
        """Сохранение данных в CSV файл"""
        save_timer = Timer("Сохранение в CSV")
        save_timer.start()

        if not self.data:
            print("Нет данных для сохранения")
            return False

        try:
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["category", "service", "duration", "description", "price"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for row in self.data:
                    writer.writerow(row)

            save_timer.stop()
            print(f"Данные сохранены в файл: {filename}")
            print(f"Количество записей: {len(self.data)}")
            return True

        except Exception as e:
            print(f"Ошибка при сохранении: {e}")
            return False

    def show_parsing_stats(self):
        """Показать статистику парсинга"""
        if not self.data:
            return

        print(f"\n=== СТАТИСТИКА ПАРСИНГА ===")
        print(f"Всего услуг: {len(self.data)}")

        # Группируем по категориям
        categories = {}
        for item in self.data:
            cat = item["category"] or "Без категории"
            categories[cat] = categories.get(cat, 0) + 1

        print(f"Категорий: {len(categories)}")

        # Топ-10 категорий по количеству услуг
        top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]
        print("Топ-10 категорий:")
        for cat, count in top_categories:
            print(f"  - {cat}: {count} услуг")

        # Считаем услуги с ценами
        with_prices = sum(1 for item in self.data if item["price"])
        print(f"Услуг с ценами: {with_prices}")
        print(f"Услуг без цен: {len(self.data) - with_prices}")

    def run(self, output_file="price_list.csv", debug=False):
        """Основной метод запуска парсера с измерением времени"""
        self.total_timer.start()

        try:
            print(f"🚀 Режим парсинга: {'БЫСТРЫЙ' if self.fast_mode else 'ОБЫЧНЫЙ'}")
            print(f"Загружаем страницу: {self.url}")

            page_load_timer = Timer("Загрузка страницы")
            page_load_timer.start()
            self.driver.get(self.url)
            page_load_timer.stop()

            if not self.wait_for_page_load():
                print("Не удалось дождаться загрузки страницы")
                return False

            print("\nНачинаем парсинг...")
            if not self.parse_services():
                print("Парсинг не дал результатов")
                return False

            # Показываем статистику
            self.show_parsing_stats()

            if self.save_to_csv(output_file):
                total_time = self.total_timer.stop()

                # Дополнительная статистика производительности
                print(f"\n=== СТАТИСТИКА ПРОИЗВОДИТЕЛЬНОСТИ ===")
                print(f"⚡ Общее время: {self.total_timer.format_duration(total_time)}")
                print(f"📊 Скорость: {len(self.data)/total_time:.2f} услуг/сек")
                print(f"🎯 Режим: {'БЫСТРЫЙ' if self.fast_mode else 'ОБЫЧНЫЙ'}")

                return True
            else:
                return False

        except Exception as e:
            print(f"Критическая ошибка: {e}")
            return False

        finally:
            if self.driver:
                self.driver.quit()


def main():
    """Главная функция с выбором режима"""
    print("=== ОПТИМИЗИРОВАННЫЙ ПАРСЕР ПРАЙС-ЛИСТА ===")
    print("Выберите режим работы:")
    print("1. БЫСТРЫЙ режим (оптимизации включены)")
    print("2. ОБЫЧНЫЙ режим (полная загрузка)")

    try:
        choice = input("Введите номер режима (1 или 2): ").strip()
        fast_mode = choice == "1"
    except:
        fast_mode = True  # По умолчанию быстрый режим

    print(f"\n🚀 Запуск в {'БЫСТРОМ' if fast_mode else 'ОБЫЧНОМ'} режиме...")

    # Создаем парсер
    parser = PriceListParser(headless=False, fast_mode=fast_mode)

    # Запускаем парсинг
    filename = "price_list_fast.csv" if fast_mode else "price_list_normal.csv"
    success = parser.run(output_file=filename, debug=True)

    if success:
        print(f"\n✅ Парсинг завершен успешно!")
        print(f"📁 Проверьте файл {filename}")
    else:
        print(f"\n❌ Парсинг завершился с ошибками")


if __name__ == "__main__":
    main()
