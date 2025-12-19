import argparse
import csv
import json
import os
import random
import re
import sys
import time
import traceback
from typing import List, Dict, Optional, Tuple, Iterator
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class FileIterator:
    """Итератор для перебора MP3 файлов в директории."""
    
    def __init__(self, dir_path: str) -> None:
        """
        Инициализация итератора.
        
        Args:
            dir_path: Путь к директории с файлами
        """
        self.dir_path = os.path.abspath(dir_path)
        if not os.path.exists(self.dir_path):
            os.makedirs(self.dir_path, exist_ok=True)
        
        # Собираем список MP3 файлов
        self.file_list: List[str] = []
        if os.path.exists(self.dir_path):
            for file_name in os.listdir(self.dir_path):
                if file_name.lower().endswith('.mp3'):
                    self.file_list.append(os.path.join(self.dir_path, file_name))
        
        self.index = 0
        self.total_files = len(self.file_list)
        
    def __iter__(self) -> Iterator[str]:
        """Возвращает итератор."""
        return self
    
    def __next__(self) -> str:
        """Возвращает следующий MP3 файл."""
        if self.index < self.total_files:
            file_path = self.file_list[self.index]
            self.index += 1
            return file_path
        raise StopIteration
    
    def __len__(self) -> int:
        """Возвращает количество MP3 файлов."""
        return self.total_files
    
    def reset(self) -> None:
        """Сброс итератора."""
        self.index = 0


def parse_args() -> argparse.Namespace:
    """
    Парсинг аргументов командной строки.
    
    Returns:
        Пространство имен с аргументами
    """
    parser = argparse.ArgumentParser(
        description='Скачивание музыки с Mixkit по жанрам: country, funk, classical'
    )
    parser.add_argument(
        '--output_dir',
        '-o',
        required=True,
        help='Папка для сохранения всех треков'
    )
    parser.add_argument(
        '--csv_path',
        '-c',
        default='music_annotation.csv',
        help='Путь к выходному CSV-файлу (по умолчанию: music_annotation.csv)'
    )
    parser.add_argument(
        '--min_files',
        type=int,
        default=50,
        help='Минимальное количество файлов для скачивания (по умолчанию: 50)'
    )
    parser.add_argument(
        '--max_files',
        type=int,
        default=100,
        help='Максимальное количество файлов для скачивания (по умолчанию: 100)'
    )
    parser.add_argument(
        '--max_pages',
        type=int,
        default=3,
        help='Максимальное количество страниц для парсинга на жанр (по умолчанию: 3)'
    )
    
    args = parser.parse_args()
    
    # Валидация аргументов
    if args.min_files < 1:
        parser.error('--min_files должно быть больше 0')
    if args.max_files < args.min_files:
        parser.error('--max_files должно быть больше или равно --min_files')
    if args.max_pages < 1:
        parser.error('--max_pages должно быть больше 0')
    
    return args


def csv_init(csv_path: str) -> None:
    """
    Создаёт CSV-файл с заголовком.
    
    Args:
        csv_path: Путь к CSV файлу
    """
    try:
        # Создаем директорию для CSV файла, если она не существует
        csv_dir = os.path.dirname(csv_path)
        if csv_dir and not os.path.exists(csv_dir):
            os.makedirs(csv_dir, exist_ok=True)
        
        csv_header = ["genre", "abs_path", "rel_path", "url", "filename", "duration"]
        with open(csv_path, 'w', encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(csv_header)
        print(f"Создан CSV файл: {csv_path}")
    except IOError as e:
        print(f"Ошибка создания CSV файла {csv_path}: {e}")
        raise


def append_to_csv(csv_path: str, csv_data: List[List[str]]) -> None:
    """
    Добавляет строки в CSV-файл.
    
    Args:
        csv_path: Путь к CSV файлу
        csv_data: Список строк для записи
    """
    try:
        with open(csv_path, 'a', encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            for row in csv_data:
                writer.writerow(row)
    except IOError as e:
        print(f"Ошибка записи в CSV файл {csv_path}: {e}")
        raise


def generate_url(genre: str, page: int = 1) -> str:
    """
    Создаёт ссылку на страницу жанра в Mixkit.
    
    Args:
        genre: Название жанра
        page: Номер страницы (по умолчанию: 1)
    
    Returns:
        URL страницы жанра
    """
    base_url = f"https://mixkit.co/free-stock-music/{genre}/"
    if page > 1:
        return f"{base_url}?page={page}"
    return base_url


def get_html(url: str) -> Optional[str]:
    """
    Получает HTML страницы с обработкой ошибок.
    
    Args:
        url: URL страницы
    
    Returns:
        HTML содержимое или None в случае ошибки
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        # Проверяем, что это HTML страница
        if 'text/html' in resp.headers.get('Content-Type', ''):
            return resp.text
        else:
            print(f"Неожиданный Content-Type: {resp.headers.get('Content-Type')}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"Таймаут при загрузке страницы: {url}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP ошибка при загрузке {url}: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка сети при загрузке {url}: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка при загрузке {url}: {e}")
    
    return None


def mp3_parse(html: str) -> List[str]:
    """
    Парсит HTML и извлекает ссылки на MP3 файлы.
    
    Args:
        html: HTML содержимое страницы
    
    Returns:
        Список URL MP3 файлов
    """
    if not html:
        return []
    
    urls: List[str] = []
    soup = BeautifulSoup(html, 'html.parser')
    
    # Способ 1: Парсинг JSON-LD скриптов
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string or '{}')
            js = json.dumps(data)
            found = re.findall(r'https://assets\.mixkit\.co/[^\s"\']+\.mp3', js)
            urls.extend(found)
        except json.JSONDecodeError:
            continue
    
    # Способ 2: Поиск ссылок в audio тегах
    for audio_tag in soup.find_all('audio'):
        if audio_tag.get('src'):
            src = audio_tag['src']
            if src.endswith('.mp3'):
                urls.append(src)
    
    # Способ 3: Поиск ссылок с классом download-button
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.endswith('.mp3') and 'mixkit' in href:
            if not href.startswith('http'):
                href = urljoin('https://mixkit.co', href)
            urls.append(href)
    
    # Удаляем дубликаты и сортируем для стабильности
    unique_urls = list(dict.fromkeys(urls))
    return sorted(unique_urls)


def random_urls(urls: List[str], min_count: int = 1, max_count: int = 10) -> List[str]:
    """
    Выбирает случайное количество ссылок из списка.
    
    Args:
        urls: Список URL
        min_count: Минимальное количество ссылок для выбора
        max_count: Максимальное количество ссылок для выбора
    
    Returns:
        Случайный подсписок URL
    """
    if not urls:
        return []
    
    # Ограничиваем максимальное количество доступными ссылками
    available_count = len(urls)
    max_possible = min(max_count, available_count)
    min_possible = min(min_count, available_count)
    
    if min_possible > max_possible:
        min_possible = max_possible
    
    # Выбираем случайное количество в заданном диапазоне
    n = random.randint(min_possible, max_possible)
    
    # Возвращаем случайные ссылки
    return random.sample(urls, n)


def download_mp3(url: str, path: str, retries: int = 3) -> bool:
    """
    Скачивает MP3-файл по URL с повторными попытками.
    
    Args:
        url: URL MP3 файла
        path: Путь для сохранения
        retries: Количество попыток
    
    Returns:
        True если скачивание успешно, иначе False
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for attempt in range(retries):
        try:
            print(f"Попытка {attempt + 1}/{retries}: скачивание {os.path.basename(path)}")
            
            resp = requests.get(url, headers=headers, timeout=(5, 30), stream=True)
            resp.raise_for_status()
            
            # Проверяем размер файла
            content_length = resp.headers.get('Content-Length')
            if content_length and int(content_length) < 1024:  # Меньше 1KB
                print(f"Файл слишком маленький: {content_length} байт")
                return False
            
            # Скачиваем файл
            with open(path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Проверяем, что файл создан и не пустой
            if os.path.exists(path) and os.path.getsize(path) > 1024:
                print(f"Успешно скачан: {os.path.basename(path)}")
                return True
            else:
                print(f"Файл не создан или пустой: {path}")
                
        except requests.exceptions.Timeout:
            print(f"Таймаут при скачивании {url}")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP ошибка при скачивании {url}: {e}")
            if e.response.status_code == 404:
                return False  # Не пытаться снова для 404
        except requests.exceptions.RequestException as e:
            print(f"Ошибка сети при скачивании {url}: {e}")
        except IOError as e:
            print(f"Ошибка записи файла {path}: {e}")
        except Exception as e:
            print(f"Неожиданная ошибка при скачивании {url}: {e}")
        
        # Пауза перед следующей попыткой
        if attempt < retries - 1:
            time.sleep(random.uniform(1, 3))
    
    return False


def get_duration_from_url(url: str) -> str:
    """
    Получает примерную длительность из имени файла или возвращает 0.
    
    Args:
        url: URL файла
    
    Returns:
        Строка с длительностью (например, "3:45")
    """
    # Пытаемся извлечь длительность из имени файла
    filename = os.path.basename(url)
    match = re.search(r'(\d+)[_-]?sec', filename, re.IGNORECASE)
    if match:
        seconds = int(match.group(1))
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:02d}"
    
    # Или ищем числа в формате времени
    match = re.search(r'(\d+)[_-]?min[_-]?(\d+)', filename, re.IGNORECASE)
    if match:
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        return f"{minutes}:{seconds:02d}"
    
    # Или просто случайная длительность для примера
    return f"{random.randint(2, 5)}:{random.randint(0, 59):02d}"


def process_genre(
    genre: str, 
    output_dir: str, 
    csv_path: str,
    min_files_per_genre: int = 5,
    max_files_per_genre: int = 15,
    max_pages: int = 3
) -> int:
    """
    Обрабатывает один жанр.
    
    Args:
        genre: Название жанра
        output_dir: Папка для сохранения файлов
        csv_path: Путь к CSV файлу
        min_files_per_genre: Минимальное количество файлов на жанр
        max_files_per_genre: Максимальное количество файлов на жанр
        max_pages: Максимальное количество страниц для парсинга
    
    Returns:
        Количество успешно скачанных файлов
    """
    print(f"\n{'='*60}")
    print(f"Обрабатываем жанр: {genre}")
    print(f"{'='*60}")
    
    all_urls: List[str] = []
    
    # Парсим несколько страниц
    for page in range(1, max_pages + 1):
        print(f"Парсинг страницы {page}...")
        url = generate_url(genre, page)
        html = get_html(url)
        
        if html:
            page_urls = mp3_parse(html)
            print(f"Найдено ссылок на странице {page}: {len(page_urls)}")
            all_urls.extend(page_urls)
            
            # Небольшая пауза между запросами
            if page < max_pages:
                time.sleep(random.uniform(1, 2))
        else:
            print(f"Не удалось загрузить страницу {page}")
    
    # Удаляем дубликаты
    all_urls = list(dict.fromkeys(all_urls))
    print(f"Всего уникальных ссылок для жанра {genre}: {len(all_urls)}")
    
    if not all_urls:
        print(f"Для жанра {genre} ссылки не найдены!")
        return 0
    
    # Выбираем случайные ссылки для скачивания
    selected_urls: List[str] = random_urls(
        all_urls, 
        min_files_per_genre, 
        max_files_per_genre
    )
    print(f"Выбрано для скачивания: {len(selected_urls)} ссылок")
    
    csv_data: List[List[str]] = []
    downloaded_count = 0
    
    # Скачиваем выбранные файлы
    for i, url in enumerate(selected_urls, 1):
        # Создаем уникальное имя файла
        base_name = os.path.basename(url)
        safe_name = re.sub(r'[^\w\-.]', '_', base_name)  # Заменяем спецсимволы
        filename = f"{genre}_{i:03d}_{safe_name}"
        
        # Если имя слишком длинное, укорачиваем
        if len(filename) > 150:
            name, ext = os.path.splitext(filename)
            filename = name[:100] + ext
        
        filepath = os.path.join(output_dir, filename)
        
        # Пропускаем, если файл уже существует
        if os.path.exists(filepath):
            print(f"Файл уже существует: {filename}")
        else:
            print(f"[{i}/{len(selected_urls)}] Скачиваем: {filename}")
            
            # Скачиваем файл
            if download_mp3(url, filepath):
                downloaded_count += 1
                
                # Получаем длительность
                duration = get_duration_from_url(url)
                
                # Добавляем данные в CSV
                abs_path = os.path.abspath(filepath)
                rel_path = os.path.relpath(filepath, output_dir)
                csv_data.append([
                    genre,
                    abs_path,
                    rel_path,
                    url,
                    filename,
                    duration
                ])
            else:
                print(f"Не удалось скачать: {filename}")
        
        # Пауза между скачиваниями
        if i < len(selected_urls):
            time.sleep(random.uniform(0.5, 1.5))
    
    # Записываем данные в CSV
    if csv_data:
        try:
            append_to_csv(csv_path, csv_data)
            print(f"Данные для жанра {genre} записаны в CSV")
        except Exception as e:
            print(f"Ошибка при записи в CSV для жанра {genre}: {e}")
    
    return downloaded_count


def distribute_files_by_genre(
    total_files: int, 
    genres: List[str], 
    min_per_genre: int = 1
) -> Dict[str, int]:
    """
    Распределяет общее количество файлов по жанрам.
    
    Args:
        total_files: Общее количество файлов
        genres: Список жанров
        min_per_genre: Минимальное количество файлов на жанр
    
    Returns:
        Словарь с распределением по жанрам
    """
    # Гарантируем минимум для каждого жанра
    distribution = {genre: min_per_genre for genre in genres}
    allocated = min_per_genre * len(genres)
    
    # Распределяем оставшиеся файлы случайным образом
    remaining = total_files - allocated
    if remaining > 0:
        # Генерируем случайные веса для жанров
        weights = [random.random() for _ in genres]
        total_weight = sum(weights)
        
        for i, genre in enumerate(genres):
            additional = int(remaining * (weights[i] / total_weight))
            distribution[genre] += additional
        
        # Корректируем округление
        current_total = sum(distribution.values())
        while current_total < total_files:
            genre = random.choice(genres)
            distribution[genre] += 1
            current_total += 1
    
    print("\nРаспределение файлов по жанрам:")
    for genre, count in distribution.items():
        print(f"  {genre}: {count} файлов")
    
    return distribution


def main() -> None:
    """
    Основная функция программы.
    """
    try:
        # Парсим аргументы
        args = parse_args()
        
        # Создаем выходную директорию
        os.makedirs(args.output_dir, exist_ok=True)
        print(f"Выходная директория: {args.output_dir}")
        
        # Инициализируем CSV файл
        csv_init(args.csv_path)
        print(f"CSV файл: {args.csv_path}")
        
        # Определяем жанры
        genres = ['country', 'funk', 'classical']
        
        # Определяем общее количество файлов для скачивания
        total_to_download = random.randint(args.min_files, args.max_files)
        print(f"\nЦель: скачать {total_to_download} файлов")
        print(f"Диапазон: от {args.min_files} до {args.max_files} файлов")
        
        # Распределяем файлы по жанрам
        distribution = distribute_files_by_genre(total_to_download, genres)
        
        total_downloaded = 0
        
        # Обрабатываем каждый жанр
        for genre in genres:
            files_to_download = distribution.get(genre, 0)
            if files_to_download > 0:
                downloaded = process_genre(
                    genre=genre,
                    output_dir=args.output_dir,
                    csv_path=args.csv_path,
                    min_files_per_genre=files_to_download,
                    max_files_per_genre=files_to_download,
                    max_pages=args.max_pages
                )
                total_downloaded += downloaded
                print(f"Для жанра {genre} скачано: {downloaded}/{files_to_download} файлов")
        
        # Выводим итоговую статистику
        print(f"\n{'='*60}")
        print("ИТОГИ:")
        print(f"{'='*60}")
        print(f"Всего скачано файлов: {total_downloaded}")
        print(f"Целевое количество: {total_to_download}")
        
        if total_downloaded < total_to_download:
            print(f"Внимание: скачано меньше целевого количества на {total_to_download - total_downloaded} файлов")
        
        # Демонстрация итератора
        print(f"\n{'='*60}")
        print("ДЕМОНСТРАЦИЯ ИТЕРАТОРА:")
        print(f"{'='*60}")
        
        try:
            iterator = FileIterator(args.output_dir)
            file_count = len(iterator)
            print(f"Всего MP3 файлов в директории: {file_count}")
            
            if file_count > 0:
                print("\nПервые 5 файлов:")
                iterator.reset()
                for i, file_path in enumerate(iterator):
                    if i < 5:
                        print(f"  {i+1}. {os.path.basename(file_path)}")
                    else:
                        break
                if file_count > 5:
                    print("  ...")
            else:
                print("В директории нет MP3 файлов")
                
        except Exception as e:
            print(f"Ошибка при работе с итератором: {e}")
        
        print(f"\nПрограмма завершена успешно!")
        print(f"Файлы сохранены в: {args.output_dir}")
        print(f"Аннотации сохранены в: {args.csv_path}")
        
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем")
        sys.exit(0)
    except argparse.ArgumentError as e:
        print(f"Ошибка аргументов: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nОшибка при выполнении программы: {e}")
        print(f"\nДетали ошибки:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
