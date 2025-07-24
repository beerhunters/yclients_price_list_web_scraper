import csv
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class PriceListParser:
    def __init__(self, headless=True):
        """
        Инициализация парсера

        Args:
            headless (bool): Запуск браузера в фоновом режиме
        """
        self.url = (
            "https://n729879.yclients.com/company/929887/personal/select-services?o="
        )
        self.driver = None
        self.data = []
        self.setup_driver(headless)

    def setup_driver(self, headless=True):
        """Настройка веб-драйвера Chrome"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            self.driver.implicitly_wait(5)
        except Exception as e:
            print(f"Ошибка при инициализации драйвера: {e}")
            print("Убедитесь, что ChromeDriver установлен и доступен в PATH")
            raise

    def wait_for_page_load(self, timeout=45):
        """Ожидание загрузки динамического контента"""
        print("Ожидаем загрузки страницы...")

        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("Базовая структура загружена")
        except TimeoutException:
            print("Не удалось загрузить базовую структуру")
            return False

        time.sleep(5)
        print("Выполняем полную прокрутку страницы...")
        self.scroll_to_load_all_content()
        return True

    def scroll_to_load_all_content(self):
        """Прокрутка страницы для загрузки всего lazy-loading контента"""
        print("Начинаем полную прокрутку для загрузки всего контента...")

        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_step = 500

        current_position = 0
        while current_position < last_height:
            current_position += scroll_step
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(0.5)

            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height > last_height:
                print(f"Обнаружен новый контент. Высота: {last_height} -> {new_height}")
                last_height = new_height

        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
        print(f"Прокрутка завершена. Итоговая высота страницы: {last_height}px")

    def parse_services(self):
        """Парсинг услуг по контейнерам"""
        print("Начинаем парсинг услуг по контейнерам...")

        # Находим все контейнеры
        containers = self.driver.find_elements(
            By.CSS_SELECTOR, ".inner-container.ng-star-inserted"
        )
        print(f"Найдено контейнеров: {len(containers)}")

        if not containers:
            print("Контейнеры не найдены, пробуем альтернативный селектор...")
            containers = self.driver.find_elements(By.CLASS_NAME, "inner-container")
            print(f"Найдено контейнеров (альтернативный поиск): {len(containers)}")

        total_services = 0

        for i, container in enumerate(containers):
            try:
                # Ищем категорию в текущем контейнере
                category_name = self.extract_category_from_container(container)

                if not category_name:
                    continue  # Пропускаем контейнеры без категории

                print(f"\nОбрабатываем контейнер {i+1}: {category_name}")

                # Ищем все услуги в этом контейнере
                services = self.extract_services_from_container(
                    container, category_name
                )
                total_services += len(services)

                print(f"  Найдено услуг в категории '{category_name}': {len(services)}")

            except Exception as e:
                print(f"Ошибка при обработке контейнера {i+1}: {e}")
                continue

        print(f"\nВсего извлечено услуг: {total_services}")
        return len(self.data) > 0

    def extract_category_from_container(self, container):
        """Извлечение названия категории из контейнера"""
        category_selectors = [
            ".label.category-title",
            ".category-title",
            ".service_category_title",
            ".service_caterogy_title",
            "[class*='category-title']",
            "[class*='category_title']",
        ]

        for selector in category_selectors:
            try:
                category_elements = container.find_elements(By.CSS_SELECTOR, selector)
                if category_elements:
                    category_text = category_elements[0].text.strip()
                    if category_text:
                        return category_text
            except Exception:
                continue

        return None

    def extract_services_from_container(self, container, category_name):
        """Извлечение всех услуг из контейнера"""
        services = []

        # Ищем все карточки услуг в контейнере
        service_cards = container.find_elements(
            By.CSS_SELECTOR, ".card-content-container"
        )

        if not service_cards:
            # Альтернативные селекторы для карточек услуг
            alternative_selectors = [
                ".service-card",
                ".service_card",
                "[class*='service-card']",
                "[class*='card-content']",
                ".card-container",
            ]

            for selector in alternative_selectors:
                service_cards = container.find_elements(By.CSS_SELECTOR, selector)
                if service_cards:
                    break

        print(f"    Найдено карточек услуг: {len(service_cards)}")

        for j, card in enumerate(service_cards):
            try:
                service_data = self.extract_service_data_from_card(card, category_name)
                if service_data:
                    services.append(service_data)
                    self.data.append(service_data)

            except Exception as e:
                print(f"    Ошибка при обработке карточки {j+1}: {e}")
                continue

        return services

    def extract_service_data_from_card(self, card, category_name):
        """Извлечение данных об услуге из карточки"""
        try:
            # Название услуги
            service_name = ""
            title_selectors = [
                ".title-block__title",
                ".service-title",
                ".service_title",
                "[class*='title-block']",
                "[class*='service-title']",
                "h3",
                "h4",
                ".title",
            ]

            for selector in title_selectors:
                try:
                    title_elements = card.find_elements(By.CSS_SELECTOR, selector)
                    if title_elements:
                        service_name = title_elements[0].text.strip()
                        if service_name:
                            break
                except:
                    continue

            if not service_name:
                return None

            # Длительность/комментарий
            duration = ""
            duration_selectors = [
                ".comment__seance-length",
                ".seance-length",
                ".duration",
                ".comment",
                "[class*='seance-length']",
                "[class*='duration']",
                "[class*='comment']",
            ]

            for selector in duration_selectors:
                try:
                    duration_elements = card.find_elements(By.CSS_SELECTOR, selector)
                    if duration_elements:
                        duration_text = duration_elements[0].text.strip()
                        if duration_text and not any(
                            word in duration_text.lower()
                            for word in ["цена", "стоимость", "₽", "руб"]
                        ):
                            duration = duration_text
                            break
                except:
                    continue

            # Описание
            description = ""
            desc_selectors = [
                ".description",
                ".service-description",
                "[class*='description']",
                ".detail",
                ".details",
            ]

            for selector in desc_selectors:
                try:
                    desc_elements = card.find_elements(By.CSS_SELECTOR, selector)
                    if desc_elements:
                        desc_text = desc_elements[0].text.strip()
                        if (
                            desc_text
                            and desc_text != service_name
                            and desc_text != duration
                        ):
                            description = desc_text
                            break
                except:
                    continue

            # Цена (как один столбец)
            price = ""
            price_selectors = [
                ".price-range",
                ".price",
                ".cost",
                ".service-price",
                "[class*='price-range']",
                "[class*='price']",
                "[class*='cost']",
            ]

            for selector in price_selectors:
                try:
                    price_elements = card.find_elements(By.CSS_SELECTOR, selector)
                    if price_elements:
                        price_text = price_elements[0].text.strip()
                        if price_text and (
                            "₽" in price_text
                            or "руб" in price_text
                            or price_text.isdigit()
                        ):
                            price = price_text
                            break
                except:
                    continue

            # Если цену не нашли в специальных элементах, ищем в тексте карточки
            if not price:
                try:
                    card_text = card.text
                    import re

                    # Ищем цены в формате "1000 ₽", "от 800 до 1200 ₽", "800-1200 руб" и т.д.
                    price_patterns = [
                        r"от\s+\d+(?:\s*\d+)*\s+до\s+\d+(?:\s*\d+)*\s*[₽руб]",
                        r"\d+(?:\s*\d+)*\s*[-–—]\s*\d+(?:\s*\d+)*\s*[₽руб]",
                        r"\d+(?:\s*\d+)*\s*[₽руб]",
                        r"от\s+\d+(?:\s*\d+)*\s*[₽руб]",
                        r"до\s+\d+(?:\s*\d+)*\s*[₽руб]",
                    ]

                    for pattern in price_patterns:
                        match = re.search(pattern, card_text, re.IGNORECASE)
                        if match:
                            price = match.group(0).strip()
                            break
                except:
                    pass

            # Создаем запись об услуге
            service_data = {
                "category": category_name,
                "service": service_name,
                "duration": duration,
                "description": description,
                "price": price,
            }

            return service_data

        except Exception as e:
            print(f"      Ошибка извлечения данных из карточки: {e}")
            return None

    def save_to_csv(self, filename="price_list.csv"):
        """Сохранение данных в CSV файл"""
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
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        print(f"Категорий: {len(categories)}")
        for cat, count in sorted(categories.items()):
            print(f"  - {cat}: {count} услуг")

        # Считаем услуги с ценами
        with_prices = sum(1 for item in self.data if item["price"])
        print(f"Услуг с ценами: {with_prices}")
        print(f"Услуг без цен: {len(self.data) - with_prices}")

        # Считаем услуги с описанием и длительностью
        with_duration = sum(1 for item in self.data if item["duration"])
        with_description = sum(1 for item in self.data if item["description"])
        print(f"Услуг с длительностью: {with_duration}")
        print(f"Услуг с описанием: {with_description}")

        # Показываем примеры найденных услуг
        print(f"\n=== ПРИМЕРЫ УСЛУГ ===")
        for i, item in enumerate(self.data[:10]):
            print(f"{i+1}. Категория: {item['category']}")
            print(f"   Услуга: {item['service']}")
            if item["price"]:
                print(f"   Цена: {item['price']}")
            if item["duration"]:
                print(f"   Длительность: {item['duration']}")
            print()

    def run(self, output_file="price_list.csv", debug=False):
        """Основной метод запуска парсера"""
        try:
            print(f"Загружаем страницу: {self.url}")
            self.driver.get(self.url)

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
                print("Парсинг успешно завершен!")
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
    """Главная функция"""
    print("=== ПАРСЕР ПРАЙС-ЛИСТА С ПРАВИЛЬНОЙ СТРУКТУРОЙ ===")
    print("Версия с парсингом по контейнерам")

    # Создаем парсер
    parser = PriceListParser(headless=False)

    # Запускаем парсинг
    success = parser.run(output_file="price_list_fixed.csv", debug=True)

    if success:
        print("\n✅ Парсинг завершен успешно!")
        print("Проверьте файл price_list_fixed.csv")
    else:
        print("\n❌ Парсинг завершился с ошибками")


if __name__ == "__main__":
    main()
