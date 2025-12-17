import argparse
import csv
import requests
import os
import time
import random
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup


def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Скачивание музыки с mixkit.co по жанрам (country, funk, classical)"
    )
    parser.add_argument(
        "--download-folder",
        "-d",
        required=True,
        help="Папка для сохранения аудиофайлов",
    )
    parser.add_argument(
        "--annotation-file",
        "-a",
        default="annotation.csv",
        help="Путь к файлу аннотации CSV (по умолчанию: annotation.csv)",
    )
    parser.add_argument(
        "--min-files", type=int, default=50, help="Минимальное количество файлов"
    )
    parser.add_argument(
        "--max-files", type=int, default=100, help="Максимальное количество файлов"
    )

    args = parser.parse_args()

    # Валидация аргументов
    if not (50 <= args.max_files <= 1000):
        parser.error("--max-files должно быть от 50 до 1000")
    if args.min_files > args.max_files:
        parser.error("--min-files не может быть больше --max-files")

    return args


class MusicDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            }
        )
        self.base_url = "https://mixkit.co"

        # Жанры для варианта 24
        self.genres = ["country", "funk", "classical"]
        
        # Страницы с музыкой по жанрам (на основе структуры сайта)
        self.genre_urls = {
            "country": "/free-stock-music/country/",
            "funk": "/free-stock-music/funk/",
            "classical": "/free-stock-music/classical/"
        }

    def get_music_pages_from_genre(self, genre, url, max_pages=3):
        """Получить страницы с музыкой из определенного жанра"""
        music_pages = []
        
        print(f"Поиск музыки в жанре: {genre}")
        
        for page in range(1, max_pages + 1):
            page_url = url
            if page > 1:
                page_url = f"{url.rstrip('/')}/?page={page}"
            
            print(f"  Страница {page}: {page_url}")
            
            try:
                response = self.session.get(self.base_url + page_url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Поиск ссылок на отдельные треки
                # На Mixkit ссылки на музыку обычно содержат "/free-stock-music/жанр/название-трека-123/"
                track_links = soup.find_all("a", href=re.compile(r"/free-stock-music/[^/]+/[^/]+/$"))
                
                for link in track_links:
                    href = link["href"]
                    if href.startswith("/free-stock-music/"):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in music_pages:
                            music_pages.append(full_url)
                            print(f"    Найдена страница трека: {os.path.basename(href)}")
                
                # Проверяем наличие следующей страницы
                next_button = soup.find("a", class_="pagination__item--next")
                if not next_button and page >= 2:
                    break
                    
                time.sleep(random.uniform(1, 2))
                
            except requests.RequestException as e:
                print(f"    Ошибка при загрузке страницы {page_url}: {e}")
                break
            except Exception as e:
                print(f"    Ошибка при парсинге страницы {page_url}: {e}")
                break
        
        print(f"  Найдено треков в жанре {genre}: {len(music_pages)}")
        return music_pages

    def get_music_pages(self):
        """Получить страницы с музыкой из трех жанров (country, funk, classical)"""
        all_music_pages = []
        
        for genre in self.genres:
            if genre in self.genre_urls:
                genre_pages = self.get_music_pages_from_genre(genre, self.genre_urls[genre])
                all_music_pages.extend(genre_pages)
        
        # Перемешиваем, чтобы получить случайное распределение
        random.shuffle(all_music_pages)
        return all_music_pages

    def distribute_files_by_genre(self, total_files, min_per_genre=1):
        """Распределить общее количество файлов по жанрам случайным образом"""
        # Гарантируем минимум по 1 файлу на каждый жанр
        base_distribution = {genre: min_per_genre for genre in self.genres}
        remaining_files = total_files - (min_per_genre * len(self.genres))
        
        if remaining_files > 0:
            # Распределяем оставшиеся файлы случайным образом
            weights = [random.random() for _ in self.genres]
            total_weight = sum(weights)
            
            for i, genre in enumerate(self.genres):
                additional = int(remaining_files * (weights[i] / total_weight))
                base_distribution[genre] += additional
            
            # Корректировка на случай округления
            total_allocated = sum(base_distribution.values())
            if total_allocated < total_files:
                genre_idx = random.randint(0, len(self.genres) - 1)
                base_distribution[self.genres[genre_idx]] += total_files - total_allocated
        
        print(f"\nРаспределение файлов по жанрам:")
        for genre, count in base_distribution.items():
            print(f"  {genre}: {count} файлов")
        
        return base_distribution

    def parse_duration(self, duration_str):
        """Преобразует строку длительности в секунды"""
        if not duration_str:
            return 0

        duration_str = duration_str.strip()
        duration_str = re.sub(r"\s+", "", duration_str)

        # Формат "0:01" или "1:23"
        if ":" in duration_str:
            parts = duration_str.split(":")
            if len(parts) == 2:
                try:
                    minutes = int(parts[0])
                    seconds = int(parts[1])
                    return minutes * 60 + seconds
                except ValueError:
                    return 0
            elif len(parts) == 3:
                try:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    seconds = int(parts[2])
                    return hours * 3600 + minutes * 60 + seconds
                except ValueError:
                    return 0

        # Пытаемся найти числа в строке
        numbers = re.findall(r"\d+", duration_str)
        if numbers:
            if len(numbers) == 1:
                return int(numbers[0])
            elif len(numbers) == 2:
                return int(numbers[0]) * 60 + int(numbers[1])
            elif len(numbers) == 3:
                return int(numbers[0]) * 3600 + int(numbers[1]) * 60 + int(numbers[2])

        return 0

    def get_duration_and_audio_url(self, page_url):
        """Извлекает длительность и аудио URL со страницы музыки"""
        try:
            response = self.session.get(page_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Ищем длительность
            duration_elem = soup.find("div", class_="item-grid-card-audio__duration")
            if not duration_elem:
                duration_elem = soup.find("span", class_="audio-player__time-total")
            if not duration_elem:
                duration_elem = soup.find("div", {"data-test-id": "duration"})

            duration_sec = 0
            if duration_elem:
                duration_text = duration_elem.get_text(strip=True)
                duration_sec = self.parse_duration(duration_text)
                print(f"    Длительность: {duration_text} -> {duration_sec} сек")

            # Ищем аудио URL
            audio_url = None
            
            # Способ 1: из data-атрибута
            audio_div = soup.find("div", {"data-audio-player-preview-url-value": True})
            if audio_div:
                audio_url = audio_div.get("data-audio-player-preview-url-value")
            
            # Способ 2: из audio тега
            if not audio_url:
                audio_tag = soup.find("audio")
                if audio_tag and audio_tag.get("src"):
                    audio_url = audio_tag["src"]
            
            # Способ 3: из ссылки с классом
            if not audio_url:
                audio_link = soup.find("a", class_="audio-player__download-button")
                if audio_link and audio_link.get("href"):
                    audio_url = audio_link["href"]
            
            if audio_url and not audio_url.startswith("http"):
                audio_url = urljoin(self.base_url, audio_url)

            return duration_sec, audio_url

        except Exception as e:
            print(f"Ошибка извлечения данных со страницы {page_url}: {e}")
            return 0, None

    def download_music_from_page(self, page_url, download_folder, genre):
        """Скачивает музыку со страницы"""
        duration_sec, audio_url = self.get_duration_and_audio_url(page_url)

        if not audio_url:
            print(f"Не найден аудио URL: {page_url}")
            return None, None, 0

        # Формируем имя файла с указанием жанра
        filename = os.path.basename(audio_url)
        if not filename.endswith(".mp3"):
            filename += ".mp3"
        
        # Добавляем жанр к имени файла для удобства
        genre_prefix = genre[:3].lower()
        filename = f"{genre_prefix}_{filename}"
        filepath = os.path.join(download_folder, filename)

        # Скачиваем файл
        print(f"Скачивание ({genre}, {duration_sec} сек): {filename}")
        try:
            audio_response = self.session.get(audio_url, timeout=30)
            if audio_response.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(audio_response.content)

                if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    return filepath, filename, duration_sec
                else:
                    print(f"Файл не скачался или пустой: {filename}")
                    return None, None, 0
            else:
                print(f"Ошибка HTTP {audio_response.status_code}: {audio_url}")
        except Exception as e:
            print(f"Ошибка скачивания {filename}: {e}")

        return None, None, 0

    def download_music_by_genre(
        self, download_folder, annotation_file, min_files=50, max_files=100
    ):
        """Основной метод скачивания музыки по жанрам"""
        os.makedirs(download_folder, exist_ok=True)
        
        # Определяем количество файлов для скачивания
        total_to_download = random.randint(min_files, max_files)
        print(f"\nЦель: скачать {total_to_download} файлов (от {min_files} до {max_files})")
        
        # Получаем все доступные страницы с музыкой
        print("\nПоиск доступной музыки на сайте...")
        all_music_pages = self.get_music_pages()
        
        if not all_music_pages:
            print("Не найдено страниц с музыкой!")
            return annotation_file
        
        print(f"\nВсего найдено треков: {len(all_music_pages)}")
        
        # Создаем CSV файл для аннотации
        with open(annotation_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                ["absolute_path", "relative_path", "filename", "genre", "duration_seconds"]
            )

            downloaded = 0
            skipped = 0
            
            # Определяем жанр для каждой страницы
            genre_for_page = {}
            for page_url in all_music_pages:
                for genre in self.genres:
                    if f"/{genre}/" in page_url:
                        genre_for_page[page_url] = genre
                        break
                if page_url not in genre_for_page:
                    genre_for_page[page_url] = "unknown"
            
            # Скачиваем файлы
            for i, page_url in enumerate(all_music_pages):
                if downloaded >= total_to_download:
                    break
                
                genre = genre_for_page.get(page_url, "unknown")
                print(f"\n--- Обработка {i + 1}/{len(all_music_pages)} ({genre}) ---")
                
                filepath, filename, duration = self.download_music_from_page(
                    page_url, download_folder, genre
                )

                if filepath and os.path.exists(filepath):
                    absolute_path = os.path.abspath(filepath)
                    relative_path = os.path.relpath(filepath, download_folder)
                    
                    writer.writerow(
                        [absolute_path, relative_path, filename, genre, duration]
                    )
                    downloaded += 1
                    print(f"Сохранён: {filename} ({duration} сек) [{downloaded}/{total_to_download}]")
                else:
                    skipped += 1
                    print("Пропущен или ошибка загрузки")

                # Случайная задержка между запросами
                time.sleep(random.uniform(1, 3))

        print(f"\nЗавершено!")
        print(f"Скачано файлов: {downloaded}")
        print(f"Пропущено файлов: {skipped}")
        
        if downloaded < min_files:
            print(f"Внимание: скачано меньше минимального количества ({min_files})")
        
        # Подсчитываем статистику по жанрам
        if os.path.exists(annotation_file):
            self.calculate_genre_statistics(annotation_file)
        
        return annotation_file

    def calculate_genre_statistics(self, annotation_file):
        """Подсчитывает статистику по жанрам"""
        genre_count = {genre: 0 for genre in self.genres}
        genre_count["unknown"] = 0
        
        try:
            with open(annotation_file, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)  # пропуск заголовка
                for row in reader:
                    if row and len(row) >= 4:
                        genre = row[3]
                        if genre in genre_count:
                            genre_count[genre] += 1
                        else:
                            genre_count["unknown"] += 1
            
            print("\nСтатистика по жанрам:")
            for genre, count in genre_count.items():
                if count > 0:
                    print(f"  {genre}: {count} файлов")
                    
        except Exception as e:
            print(f"Ошибка при подсчете статистики: {e}")


class MusicIterator:
    def __init__(self, annotation_source):
        """Итератор по аудиофайлам. Принимает путь к CSV или папке."""
        self.file_paths = []

        if os.path.isfile(annotation_source):
            # Загрузка из CSV
            with open(annotation_source, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)  # пропуск заголовка
                for row in reader:
                    if row and len(row) > 0:
                        abs_path = row[0]
                        if os.path.exists(abs_path):
                            self.file_paths.append(abs_path)
            print(f"Загружено {len(self.file_paths)} путей из аннотации")
        elif os.path.isdir(annotation_source):
            # Загрузка из папки
            for root, _, files in os.walk(annotation_source):
                for file in files:
                    if file.lower().endswith((".mp3", ".wav", ".ogg", ".m4a")):
                        self.file_paths.append(os.path.join(root, file))
            print(f"Загружено {len(self.file_paths)} файлов из папки")
        else:
            raise ValueError(
                f"Укажите существующий CSV-файл или папку: {annotation_source}"
            )

    def __iter__(self):
        self._index = 0
        return self

    def __next__(self):
        if self._index < len(self.file_paths):
            path = self.file_paths[self._index]
            self._index += 1
            return path
        else:
            raise StopIteration

    def __len__(self):
        return len(self.file_paths)


def main():
    """Основная функция программы"""
    # Парсим аргументы командной строки
    args = parse_arguments()

    # Скачивание музыки
    downloader = MusicDownloader()
    annotation_path = downloader.download_music_by_genre(
        download_folder=args.download_folder,
        annotation_file=args.annotation_file,
        min_files=args.min_files,
        max_files=args.max_files,
    )

    # Демонстрация итератора
    if annotation_path and os.path.exists(annotation_path):
        print("\n" + "=" * 50)
        print("Демонстрация работы итератора:")
        print("=" * 50)

        iterator = MusicIterator(annotation_path)
        print(f"Всего файлов для итерации: {len(iterator)}")

        print("\nПервые 5 файлов:")
        for i, path in enumerate(iterator):
            if i < 5:
                print(f"{i + 1}: {os.path.basename(path)}")

        print("...")


if __name__ == "__main__":
    main()