"""Конфигурация и константы для загрузчика музыки."""

# Жанры для скачивания
GENRES = ['country', 'funk', 'classical']

# Настройки по умолчанию
DEFAULT_CONFIG = {
    'min_files': 50,
    'max_files': 100,
    'max_pages': 3,
    'csv_path': 'music_annotation.csv',
    'retry_attempts': 3,
    'request_timeout': 10,
    'download_timeout': 30,
    'min_delay': 0.5,
    'max_delay': 2.0,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Шаблоны регулярных выражений
REGEX_PATTERNS = {
    'mp3_url': r'https://assets\.mixkit\.co/[^\s"\']+\.mp3',
    'duration_sec': r'(\d+)[_-]?sec',
    'duration_min_sec': r'(\d+)[_-]?min[_-]?(\d+)',
    'safe_filename': r'[^\w\-.]'
}

# Заголовки CSV файла
CSV_HEADERS = ["genre", "abs_path", "rel_path", "url", "filename", "duration"]