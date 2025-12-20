"""Основной класс для загрузки музыки."""
import csv
import json
import os
import random
import re
import time
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import GENRES, DEFAULT_CONFIG, REGEX_PATTERNS, CSV_HEADERS
from utils import (
    get_duration_from_url,
    create_safe_filename,
    random_urls,
    generate_url,
    make_request,
    distribute_files_by_genre
)


class MusicDownloader:
    """Класс для скачивания музыки с сайта Mixkit."""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Инициализация загрузчика.
        
        Args:
            config: Конфигурация загрузчика
        """
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.config['user_agent']})
    
    def get_html(self, url: str) -> Optional[str]:
        """
        Получает HTML страницы.
        
        Args:
            url: URL страницы
        
        Returns:
            HTML содержимое или None
        """
        response = make_request(url, self.session.headers, self.config['request_timeout'])
        if response and 'text/html' in response.headers.get('Content-Type', ''):
            return response.text
        return None
    
    def parse_mp3_urls(self, html: str) -> List[str]:
        """
        Парсит HTML и извлекает ссылки на MP3 файлы.
        
        Args:
            html: HTML содержимое
        
        Returns:
            Список URL MP3 файлов
        """
        if not html:
            return []
        
        urls: List[str] = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Способ 1: JSON-LD скрипты
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '{}')
                js = json.dumps(data)
                found = re.findall(REGEX_PATTERNS['mp3_url'], js)
                urls.extend(found)
            except json.JSONDecodeError:
                continue
        
        # Способ 2: audio теги
        for audio_tag in soup.find_all('audio'):
            if audio_tag.get('src'):
                src = audio_tag['src']
                if src.endswith('.mp3'):
                    urls.append(src)
        
        # Способ 3: ссылки с классом download
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.endswith('.mp3') and 'mixkit' in href:
                if not href.startswith('http'):
                    href = urljoin('https://mixkit.co', href)
                urls.append(href)
        
        # Удаляем дубликаты
        return list(dict.fromkeys(urls))
    
    def download_mp3(self, url: str, path: str) -> bool:
        """
        Скачивает MP3 файл.
        
        Args:
            url: URL файла
            path: Путь для сохранения
        
        Returns:
            True при успехе, False при ошибке
        """
        for attempt in range(self.config['retry_attempts']):
            try:
                print(f"Попытка {attempt + 1}/{self.config['retry_attempts']}: "
                      f"скачивание {os.path.basename(path)}")
                
                response = self.session.get(
                    url,
                    timeout=self.config['download_timeout'],
                    stream=True
                )
                response.raise_for_status()
                
                # Проверяем размер файла
                content_length = response.headers.get('Content-Length')
                if content_length and int(content_length) < 1024:
                    print(f"Файл слишком маленький: {content_length} байт")
                    return False
                
                # Скачиваем файл
                with open(path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Проверяем результат
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
                    return False
            except requests.exceptions.RequestException as e:
                print(f"Ошибка сети при скачивании {url}: {e}")
            except IOError as e:
                print(f"Ошибка записи файла {path}: {e}")
            except Exception as e:
                print(f"Неожиданная ошибка при скачивании {url}: {e}")
            
            # Пауза перед следующей попыткой
            if attempt < self.config['retry_attempts'] - 1:
                time.sleep(random.uniform(1, 3))
        
        return False
    
    def process_genre(
        self,
        genre: str,
        output_dir: str,
        csv_path: str,
        min_files: int,
        max_files: int
    ) -> int:
        """
        Обрабатывает один жанр.
        
        Args:
            genre: Название жанра
            output_dir: Папка для сохранения
            csv_path: Путь к CSV файлу
            min_files: Минимальное количество файлов
            max_files: Максимальное количество файлов
        
        Returns:
            Количество скачанных файлов
        """
        print(f"\n{'='*60}")
        print(f"Обрабатываем жанр: {genre}")
        print(f"{'='*60}")
        
        all_urls: List[str] = []
        
        # Парсим несколько страниц
        for page in range(1, self.config['max_pages'] + 1):
            print(f"Парсинг страницы {page}...")
            url = generate_url(genre, page)
            html = self.get_html(url)
            
            if html:
                page_urls = self.parse_mp3_urls(html)
                print(f"Найдено ссылок на странице {page}: {len(page_urls)}")
                all_urls.extend(page_urls)
                
                # Пауза между запросами
                if page < self.config['max_pages']:
                    time.sleep(random.uniform(
                        self.config['min_delay'],
                        self.config['max_delay']
                    ))
            else:
                print(f"Не удалось загрузить страницу {page}")
        
        # Удаляем дубликаты
        all_urls = list(dict.fromkeys(all_urls))
        print(f"Всего уникальных ссылок для жанра {genre}: {len(all_urls)}")
        
        if not all_urls:
            print(f"Для жанра {genre} ссылки не найдены!")
            return 0
        
        # Выбираем случайные ссылки
        selected_urls = random_urls(all_urls, min_files, max_files)
        print(f"Выбрано для скачивания: {len(selected_urls)} ссылок")
        
        csv_data: List[List[str]] = []
        downloaded_count = 0
        
        # Скачиваем файлы
        for i, url in enumerate(selected_urls, 1):
            base_name = os.path.basename(url)
            filename = create_safe_filename(base_name, genre, i)
            filepath = os.path.join(output_dir, filename)
            
            if os.path.exists(filepath):
                print(f"Файл уже существует: {filename}")
            else:
                print(f"[{i}/{len(selected_urls)}] Скачиваем: {filename}")
                
                if self.download_mp3(url, filepath):
                    downloaded_count += 1
                    
                    # Получаем данные для CSV
                    duration = get_duration_from_url(url)
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
                self.append_to_csv(csv_path, csv_data)
                print(f"Данные для жанра {genre} записаны в CSV")
            except Exception as e:
                print(f"Ошибка при записи в CSV для жанра {genre}: {e}")
        
        return downloaded_count
    
    def download_music(
        self,
        output_dir: str,
        csv_path: str,
        min_files: int,
        max_files: int
    ) -> Dict[str, int]:
        """
        Основной метод скачивания музыки.
        
        Args:
            output_dir: Папка для сохранения
            csv_path: Путь к CSV файлу
            min_files: Минимальное количество файлов
            max_files: Максимальное количество файлов
        
        Returns:
            Статистика скачивания
        """
        # Создаем директорию
        os.makedirs(output_dir, exist_ok=True)
        print(f"Выходная директория: {output_dir}")
        
        # Инициализируем CSV
        self.csv_init(csv_path)
        print(f"CSV файл: {csv_path}")
        
        # Определяем общее количество файлов
        total_to_download = random.randint(min_files, max_files)
        print(f"\nЦель: скачать {total_to_download} файлов")
        print(f"Диапазон: от {min_files} до {max_files} файлов")
        
        # Распределяем по жанрам
        distribution = distribute_files_by_genre(total_to_download, GENRES)
        print("\nРаспределение файлов по жанрам:")
        for genre, count in distribution.items():
            print(f"  {genre}: {count} файлов")
        
        total_downloaded = 0
        stats: Dict[str, int] = {}
        
        # Обрабатываем каждый жанр
        for genre in GENRES:
            files_to_download = distribution.get(genre, 0)
            if files_to_download > 0:
                downloaded = self.process_genre(
                    genre=genre,
                    output_dir=output_dir,
                    csv_path=csv_path,
                    min_files=files_to_download,
                    max_files=files_to_download
                )
                stats[genre] = downloaded
                total_downloaded += downloaded
                print(f"Для жанра {genre} скачано: {downloaded}/{files_to_download} файлов")
        
        return {
            'total_downloaded': total_downloaded,
            'total_target': total_to_download,
            'by_genre': stats
        }
    
    def csv_init(self, csv_path: str) -> None:
        """
        Инициализирует CSV файл.
        
        Args:
            csv_path: Путь к CSV файлу
        """
        try:
            csv_dir = os.path.dirname(csv_path)
            if csv_dir and not os.path.exists(csv_dir):
                os.makedirs(csv_dir, exist_ok=True)
            
            with open(csv_path, 'w', encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(CSV_HEADERS)
            print(f"Создан CSV файл: {csv_path}")
        except IOError as e:
            print(f"Ошибка создания CSV файла {csv_path}: {e}")
            raise
    
    def append_to_csv(self, csv_path: str, csv_data: List[List[str]]) -> None:
        """
        Добавляет данные в CSV файл.
        
        Args:
            csv_path: Путь к CSV файлу
            csv_data: Данные для записи
        """
        try:
            with open(csv_path, 'a', encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                for row in csv_data:
                    writer.writerow(row)
        except IOError as e:
            print(f"Ошибка записи в CSV файл {csv_path}: {e}")
            raise