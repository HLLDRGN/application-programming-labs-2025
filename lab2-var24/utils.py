"""Вспомогательные функции и утилиты."""
import os
import re
import random
from typing import List, Dict, Tuple, Optional
from urllib.parse import urljoin

import requests

from config import REGEX_PATTERNS, DEFAULT_CONFIG


def parse_duration(duration_str: str) -> str:
    """
    Преобразует строку длительности в секунды.
    
    Args:
        duration_str: Строка с длительностью
    
    Returns:
        Строка в формате "минуты:секунды"
    """
    if not duration_str:
        return f"{random.randint(2, 5)}:{random.randint(0, 59):02d}"

    duration_str = duration_str.strip()
    
    # Формат "0:01" или "1:23" или "1:23:45"
    if ":" in duration_str:
        parts = duration_str.split(":")
        try:
            if len(parts) == 2:
                minutes, seconds = map(int, parts)
                return f"{minutes}:{seconds:02d}"
            elif len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                total_minutes = hours * 60 + minutes
                return f"{total_minutes}:{seconds:02d}"
        except ValueError:
            pass

    # Ищем числа в строке
    numbers = re.findall(r'\d+', duration_str)
    if numbers:
        if len(numbers) == 1:
            seconds = int(numbers[0])
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes}:{remaining_seconds:02d}"
        elif len(numbers) == 2:
            minutes, seconds = map(int, numbers[:2])
            return f"{minutes}:{seconds:02d}"
        elif len(numbers) >= 3:
            hours, minutes, seconds = map(int, numbers[:3])
            total_minutes = hours * 60 + minutes
            return f"{total_minutes}:{seconds:02d}"

    return f"{random.randint(2, 5)}:{random.randint(0, 59):02d}"


def get_duration_from_url(url: str) -> str:
    """
    Получает примерную длительность из имени файла.
    
    Args:
        url: URL файла
    
    Returns:
        Строка с длительностью
    """
    filename = os.path.basename(url)
    
    # Ищем секунды в имени файла
    match = re.search(REGEX_PATTERNS['duration_sec'], filename, re.IGNORECASE)
    if match:
        seconds = int(match.group(1))
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}:{remaining_seconds:02d}"
    
    # Ищем минуты и секунды
    match = re.search(REGEX_PATTERNS['duration_min_sec'], filename, re.IGNORECASE)
    if match:
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        return f"{minutes}:{seconds:02d}"
    
    # Случайная длительность
    return f"{random.randint(2, 5)}:{random.randint(0, 59):02d}"


def create_safe_filename(base_name: str, genre: str, index: int) -> str:
    """
    Создает безопасное имя файла.
    
    Args:
        base_name: Исходное имя файла
        genre: Жанр музыки
        index: Порядковый номер
    
    Returns:
        Безопасное имя файла
    """
    # Заменяем спецсимволы на подчеркивания
    safe_name = re.sub(REGEX_PATTERNS['safe_filename'], '_', base_name)
    
    # Формируем имя файла
    filename = f"{genre}_{index:03d}_{safe_name}"
    
    # Укорачиваем слишком длинные имена
    if len(filename) > 150:
        name, ext = os.path.splitext(filename)
        filename = name[:100] + ext
    
    return filename


def random_urls(urls: List[str], min_count: int = 1, max_count: int = 10) -> List[str]:
    """
    Выбирает случайное количество ссылок из списка.
    
    Args:
        urls: Список URL
        min_count: Минимальное количество
        max_count: Максимальное количество
    
    Returns:
        Случайный подсписок
    """
    if not urls:
        return []
    
    available_count = len(urls)
    max_possible = min(max_count, available_count)
    min_possible = min(min_count, available_count)
    
    if min_possible > max_possible:
        min_possible = max_possible
    
    n = random.randint(min_possible, max_possible)
    return random.sample(urls, n)


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
        min_per_genre: Минимальное количество на жанр
    
    Returns:
        Распределение по жанрам
    """
    distribution = {genre: min_per_genre for genre in genres}
    allocated = min_per_genre * len(genres)
    
    remaining = total_files - allocated
    if remaining > 0:
        weights = [random.random() for _ in genres]
        total_weight = sum(weights)
        
        for i, genre in enumerate(genres):
            additional = int(remaining * (weights[i] / total_weight))
            distribution[genre] += additional
        
        current_total = sum(distribution.values())
        while current_total < total_files:
            genre = random.choice(genres)
            distribution[genre] += 1
            current_total += 1
    
    return distribution


def generate_url(genre: str, page: int = 1) -> str:
    """
    Генерирует URL для страницы жанра.
    
    Args:
        genre: Название жанра
        page: Номер страницы
    
    Returns:
        URL страницы
    """
    base_url = f"https://mixkit.co/free-stock-music/{genre}/"
    if page > 1:
        return f"{base_url}?page={page}"
    return base_url


def make_request(url: str, headers: Dict[str, str], timeout: int = 10) -> Optional[requests.Response]:
    """
    Выполняет HTTP-запрос с обработкой ошибок.
    
    Args:
        url: URL для запроса
        headers: Заголовки запроса
        timeout: Таймаут в секундах
    
    Returns:
        Ответ сервера или None при ошибке
    """
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout:
        print(f"Таймаут при запросе: {url}")
    except requests.exceptions.HTTPError as e:
        print(f"HTTP ошибка при запросе {url}: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка сети при запросе {url}: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка при запросе {url}: {e}")
    
    return None