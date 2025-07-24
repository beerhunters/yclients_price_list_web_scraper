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

        # Сначала ждем базовой загрузки страницы
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            print("Базовая структура загружена")
        except TimeoutException:
            print("Не удалось загрузить базовую структуру")
            return False

        # Ждем загрузки JavaScript
        time.sleep(5)

        # ПОЛНАЯ прокрутка страницы для загрузки всего контента
        print("Выполняем полную прокрутку страницы...")
        self.scroll_to_load_all_content()

        # Пробуем найти любые элементы с текстом, похожим на услуги/цены
        selectors_to_try = [
            "service_title",
            "service-title",
            "[class*='service']",
            "[class*='title']",
            "[class*='price']",
            "[class*='category']",
        ]

        for selector in selectors_to_try:
            try:
                if selector.startswith("["):
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                else:
                    elements = self.driver.find_elements(By.CLASS_NAME, selector)

                if elements:
                    print(
                        f"Найдены элементы с селектором: {selector} ({len(elements)} шт.)"
                    )
                    return True
            except:
                continue

        # Если специфичные элементы не найдены, проверяем общую загрузку
        try:
            all_text = self.driver.find_element(By.TAG_NAME, "body").text
            if len(all_text) > 100:  # Если на странице есть достаточно текста
                print("Страница загружена (найден контент)")
                return True
        except:
            pass

        print("Не удалось найти ожидаемые элементы, но продолжаем...")
        return True  # Продолжаем парсинг даже если не нашли специфичные элементы

    def scroll_to_load_all_content(self):
        """Полная прокрутка страницы для загрузки всего lazy-loading контента"""
        print("Начинаем полную прокрутку для загрузки всего контента...")

        # Получаем начальную высоту страницы
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_pause_time = 2
        scroll_step = 500  # Прокручиваем по 500px за раз

        # Сначала прокручиваем постепенно вниз
        current_position = 0
        while current_position < last_height:
            # Прокручиваем на следующий шаг
            current_position += scroll_step
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(0.5)  # Короткая пауза между прокрутками

            # Проверяем, изменилась ли высота страницы (подгрузился новый контент)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height > last_height:
                print(f"Обнаружен новый контент. Высота: {last_height} -> {new_height}")
                last_height = new_height

        print("Первичная прокрутка завершена")

        # Теперь делаем несколько полных прокруток для надежности
        for scroll_round in range(3):
            print(f"Раунд прокрутки {scroll_round + 1}/3")

            # Прокрутка до самого низа
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(scroll_pause_time)

            # Проверяем, подгрузился ли новый контент
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height > last_height:
                print(
                    f"Подгружен дополнительный контент: {last_height} -> {new_height}"
                )
                last_height = new_height

                # Если контент еще подгружается, делаем дополнительную паузу
                time.sleep(3)
            else:
                print("Новый контент не обнаружен")

            # Прокрутка вверх и снова вниз для активации всех lazy-load элементов
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(scroll_pause_time)

        # Финальная прокрутка по всей странице для активации всех элементов
        print("Финальная прокрутка по всей странице...")
        final_height = self.driver.execute_script("return document.body.scrollHeight")

        # Прокручиваем от верха до низа с остановками
        positions = [
            i * (final_height // 10) for i in range(11)
        ]  # 11 позиций (0%, 10%, 20%, ..., 100%)

        for position in positions:
            self.driver.execute_script(f"window.scrollTo(0, {position});")
            time.sleep(0.8)

        # Возвращаемся в начало страницы
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)

        final_height = self.driver.execute_script("return document.body.scrollHeight")
        print(f"Прокрутка завершена. Итоговая высота страницы: {final_height}px")

        # Дополнительная пауза для стабилизации DOM
        time.sleep(3)

    def parse_services(self):
        """Парсинг услуг со страницы"""
        print("Начинаем парсинг услуг...")

        # Сначала анализируем страницу
        self.analyze_page_structure()

        # Пробуем разные стратегии парсинга
        strategies = [
            self.parse_by_exact_structure,  # Новый точный метод
            self.parse_by_original_classes,
            self.parse_by_alternative_selectors,
            self.parse_by_text_patterns,
            self.parse_by_dom_structure,
        ]

        for i, strategy in enumerate(strategies, 1):
            print(f"\n--- Стратегия {i} ---")
            try:
                if strategy():
                    print(f"Стратегия {i} успешна! Найдено услуг: {len(self.data)}")
                    return True
            except Exception as e:
                print(f"Стратегия {i} не сработала: {e}")
                continue

        print("Все стратегии парсинга не дали результата")
        return False

    def analyze_page_structure(self):
        """Анализ структуры страницы"""
        print("\n=== АНАЛИЗ СТРУКТУРЫ СТРАНИЦЫ ===")

        try:
            # Получаем заголовок страницы
            title = self.driver.title
            print(f"Заголовок: {title}")

            # Получаем URL
            current_url = self.driver.current_url
            print(f"URL: {current_url}")

            # Ищем все элементы с классами
            all_elements = self.driver.find_elements(By.CSS_SELECTOR, "*[class]")
            classes = set()

            for elem in all_elements:
                class_attr = elem.get_attribute("class")
                if class_attr:
                    classes.update(class_attr.split())

            # Фильтруем интересные классы
            interesting_classes = []
            keywords = [
                "service",
                "price",
                "category",
                "title",
                "name",
                "cost",
                "item",
                "list",
            ]

            for cls in classes:
                if any(keyword in cls.lower() for keyword in keywords):
                    interesting_classes.append(cls)

            print(f"Интересные классы ({len(interesting_classes)}):")
            for cls in sorted(interesting_classes)[:20]:  # Показываем первые 20
                elements_count = len(self.driver.find_elements(By.CLASS_NAME, cls))
                print(f"  .{cls} ({elements_count} элементов)")

            # Ищем текст с ценами
            price_pattern_elements = self.driver.find_elements(
                By.XPATH,
                "//*[contains(text(), '₽') or contains(text(), 'руб') or contains(text(), 'р.') or text()[matches(., '[0-9]+')]]",
            )
            print(f"Элементы с возможными ценами: {len(price_pattern_elements)}")

        except Exception as e:
            print(f"Ошибка анализа: {e}")

    def parse_by_original_classes(self):
        """Парсинг по исходным классам"""
        print("Пробуем исходные классы...")

        categories = self.driver.find_elements(By.CLASS_NAME, "service_category_title")
        services = self.driver.find_elements(By.CLASS_NAME, "service_title")
        comments = self.driver.find_elements(By.CLASS_NAME, "comment")
        prices = self.driver.find_elements(By.CLASS_NAME, "service_price")

        print(
            f"Найдено: категорий={len(categories)}, услуг={len(services)}, комментариев={len(comments)}, цен={len(prices)}"
        )

        if len(services) > 0:
            return self.extract_data_from_elements(
                categories, services, comments, prices
            )

        return False

    def parse_by_exact_structure(self):
        """Парсинг по точной структуре сайта"""
        print("Парсинг по точной структуре сайта...")

        try:
            # Ищем все контейнеры с категориями и услугами
            containers = self.driver.find_elements(By.CLASS_NAME, "inner-container")
            print(f"Найдено контейнеров: {len(containers)}")

            current_category = ""

            for container in containers:
                try:
                    # Проверяем есть ли в контейнере категория
                    category_elements = container.find_elements(
                        By.CLASS_NAME, "service_caterogy_title"
                    )
                    if category_elements:
                        current_category = category_elements[0].text.strip()
                        print(f"Найдена категория: {current_category}")
                        continue

                    # Ищем карточки услуг в текущем контейнере
                    service_cards = container.find_elements(
                        By.CLASS_NAME, "service-card"
                    )
                    print(f"В контейнере найдено карточек услуг: {len(service_cards)}")

                    for card in service_cards:
                        try:
                            # Название услуги
                            service_name = ""
                            title_elements = card.find_elements(
                                By.CLASS_NAME, "title-block__title"
                            )
                            if title_elements:
                                service_name = title_elements[0].text.strip()

                            # Длительность
                            duration = ""
                            duration_elements = card.find_elements(
                                By.CLASS_NAME, "comment__seance-length"
                            )
                            if duration_elements:
                                duration = duration_elements[0].text.strip()

                            # Описание
                            description = ""
                            desc_elements = card.find_elements(
                                By.CLASS_NAME, "description"
                            )
                            if desc_elements:
                                description = desc_elements[0].text.strip()

                            # Цена
                            price = ""
                            price_elements = card.find_elements(
                                By.CLASS_NAME, "price-range"
                            )
                            if price_elements:
                                price = price_elements[0].text.strip()

                            # Объединяем комментарий (длительность + описание)
                            comment_parts = []
                            if duration:
                                comment_parts.append(f"Длительность: {duration}")
                            if description:
                                comment_parts.append(f"Описание: {description}")
                            comment = " | ".join(comment_parts)

                            # Добавляем данные если есть название услуги
                            if service_name:
                                self.data.append(
                                    {
                                        "category": current_category,
                                        "service": service_name,
                                        "comment": comment,
                                        "price": price,
                                    }
                                )

                        except Exception as e:
                            print(f"Ошибка при парсинге карточки услуги: {e}")
                            continue

                except Exception as e:
                    print(f"Ошибка при обработке контейнера: {e}")
                    continue

            print(f"Всего собрано услуг: {len(self.data)}")
            return len(self.data) > 0

        except Exception as e:
            print(f"Ошибка точного парсинга: {e}")
            return False

    def parse_by_alternative_selectors(self):
        """Парсинг альтернативными селекторами (без ограничения в 20 записей)"""
        print("Пробуем альтернативные селекторы...")

        alternative_selectors = {
            "categories": ['[class*="category"]', '[class*="group"]', "h1, h2, h3, h4"],
            "services": [
                '[class*="service"]',
                '[class*="title"]',
                '[class*="name"]',
                '[class*="item"]',
            ],
            "prices": [
                '[class*="price"]',
                '[class*="cost"]',
                '[class*="sum"]',
                '*[text()*="₽"]',
            ],
        }

        for cat_sel in alternative_selectors["categories"]:
            for serv_sel in alternative_selectors["services"]:
                for price_sel in alternative_selectors["prices"]:
                    try:
                        categories = self.driver.find_elements(By.CSS_SELECTOR, cat_sel)
                        services = self.driver.find_elements(By.CSS_SELECTOR, serv_sel)
                        prices = self.driver.find_elements(By.CSS_SELECTOR, price_sel)

                        if len(services) > 3:  # Минимальный порог
                            print(
                                f"Найдено услуг: {len(services)} с селекторами: {serv_sel}"
                            )
                            # Извлекаем ВСЕ данные без ограничений
                            for i, service in enumerate(services):  # Убрали [:20]
                                try:
                                    service_text = service.text.strip()
                                    if service_text and len(service_text) > 2:
                                        price_text = ""
                                        if i < len(prices):
                                            price_text = prices[i].text.strip()

                                        self.data.append(
                                            {
                                                "category": "Общая категория",
                                                "service": service_text,
                                                "comment": "",
                                                "price": price_text,
                                            }
                                        )
                                except:
                                    continue

                            if len(self.data) > 0:
                                return True
                    except:
                        continue

        return False

    def parse_by_text_patterns(self):
        """Парсинг по текстовым паттернам (без ограничений)"""
        print("Пробуем парсинг по текстовым паттернам...")

        try:
            # Получаем весь текст страницы
            body = self.driver.find_element(By.TAG_NAME, "body")
            all_text = body.text

            # Ищем строки с ценами
            import re

            price_lines = re.findall(
                r".*?[0-9]+.*?₽.*?|.*?[0-9]+.*?руб.*?", all_text, re.MULTILINE
            )

            print(f"Найдено строк с ценами: {len(price_lines)}")

            if len(price_lines) > 0:
                for line in price_lines:  # Убрали [:20]
                    line = line.strip()
                    if len(line) > 5:
                        # Пытаемся разделить название и цену
                        price_match = re.search(
                            r"([0-9\s]+).*?₽|([0-9\s]+).*?руб", line
                        )
                        if price_match:
                            price = price_match.group(0).strip()
                            service_name = line.replace(price, "").strip()

                            self.data.append(
                                {
                                    "category": "Автоопределение",
                                    "service": service_name,
                                    "comment": "",
                                    "price": price,
                                }
                            )

                return len(self.data) > 0

        except Exception as e:
            print(f"Ошибка текстового парсинга: {e}")

        return False

    def parse_by_dom_structure(self):
        """Парсинг по структуре DOM"""
        print("Пробуем структурный парсинг...")

        try:
            # Ищем все div, li, tr которые могут содержать услуги
            containers = self.driver.find_elements(
                By.CSS_SELECTOR, "div, li, tr, article, section"
            )

            for container in containers:
                try:
                    text = container.text.strip()
                    if text and len(text) > 10 and len(text) < 200:
                        # Проверяем, есть ли в тексте цена
                        if "₽" in text or "руб" in text:
                            # Пытаемся извлечь цену
                            import re

                            price_match = re.search(
                                r"([0-9\s]+.*?₽|[0-9\s]+.*?руб)", text
                            )
                            if price_match:
                                price = price_match.group(0).strip()
                                service_name = text.replace(price, "").strip()

                                if len(service_name) > 3:
                                    self.data.append(
                                        {
                                            "category": "DOM структура",
                                            "service": service_name,
                                            "comment": "",
                                            "price": price,
                                        }
                                    )
                except:
                    continue

            return len(self.data) > 0

        except Exception as e:
            print(f"Ошибка структурного парсинга: {e}")

        return False

    def extract_data_from_elements(self, categories, services, comments, prices):
        """Извлечение данных из найденных элементов"""
        current_category = ""

        # Простое сопоставление по индексам
        for i, service in enumerate(services):
            try:
                service_text = service.text.strip()
                if not service_text:
                    continue

                # Пытаемся найти категорию
                if i < len(categories):
                    category_text = categories[i].text.strip()
                    if category_text:
                        current_category = category_text

                # Комментарий
                comment_text = ""
                if i < len(comments):
                    comment_text = comments[i].text.strip()

                # Цена
                price_text = ""
                if i < len(prices):
                    price_text = prices[i].text.strip()

                self.data.append(
                    {
                        "category": current_category,
                        "service": service_text,
                        "comment": comment_text,
                        "price": price_text,
                    }
                )

            except Exception as e:
                continue

        return len(self.data) > 0

    def save_to_csv(self, filename="price_list.csv"):
        """Сохранение данных в CSV файл"""
        if not self.data:
            print("Нет данных для сохранения")
            return False

        try:
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["category", "service", "comment", "price"]
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

    def debug_page_structure(self):
        """Отладочный метод для анализа структуры страницы"""
        print("=== ОТЛАДКА СТРУКТУРЫ СТРАНИЦЫ ===")

        # Поиск всех возможных классов
        all_elements = self.driver.find_elements(By.CSS_SELECTOR, "*[class]")
        classes = set()

        for elem in all_elements:
            class_attr = elem.get_attribute("class")
            if class_attr:
                classes.update(class_attr.split())

        service_related = [
            cls
            for cls in classes
            if "service" in cls.lower()
            or "price" in cls.lower()
            or "category" in cls.lower()
        ]
        print("Классы, связанные с услугами:")
        for cls in sorted(service_related):
            print(f"  .{cls}")

        # Поиск текста, похожего на цены
        price_elements = self.driver.find_elements(
            By.XPATH, "//*[contains(text(), '₽') or contains(text(), 'руб')]"
        )
        print(f"\nНайдено элементов с ценами: {len(price_elements)}")

        # Вывод части HTML для анализа
        print("\n=== ФРАГМЕНТ HTML ===")
        body = self.driver.find_element(By.TAG_NAME, "body")
        html_snippet = body.get_attribute("innerHTML")[:2000]
        print(html_snippet)

    def run(self, output_file="price_list.csv", debug=False):
        """Основной метод запуска парсера"""
        try:
            print(f"Загружаем страницу: {self.url}")
            self.driver.get(self.url)

            if not self.wait_for_page_load():
                print("Не удалось дождаться загрузки страницы")
                return False

            # Дополнительная проверка и прокрутка после основной загрузки
            print("\nВыполняем дополнительную прокрутку для полной загрузки...")
            self.scroll_to_load_all_content()

            if debug:
                self.debug_page_structure()

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
        for cat, count in categories.items():
            print(f"  - {cat}: {count} услуг")

        # Считаем услуги с ценами
        with_prices = sum(1 for item in self.data if item["price"])
        print(f"Услуг с ценами: {with_prices}")
        print(f"Услуг без цен: {len(self.data) - with_prices}")


def main():
    """Главная функция"""
    print("=== ПАРСЕР ПРАЙС-ЛИСТА ===")
    print("Версия с улучшенной обработкой динамического контента")

    # Создаем парсер (headless=False для отладки)
    parser = PriceListParser(headless=False)

    # Запускаем парсинг с отладкой
    success = parser.run(output_file="price_list.csv", debug=True)

    if success:
        print("\n✅ Парсинг завершен успешно!")
        print("Проверьте файл price_list.csv")
    else:
        print("\n❌ Парсинг завершился с ошибками")
        print("Попробуйте:")
        print("1. Проверить интернет-соединение")
        print("2. Убедиться что сайт доступен")
        print("3. Обновить ChromeDriver")
        print("4. Запустить с headless=False для визуальной отладки")


if __name__ == "__main__":
    main()
