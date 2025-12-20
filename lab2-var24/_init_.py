"""Пакет для скачивания музыки с сайта Mixkit."""

from .downloader import MusicDownloader
from .iterator import FileIterator
from .config import GENRES, DEFAULT_CONFIG
from .utils import (
    parse_duration,
    get_duration_from_url,
    create_safe_filename,
    random_urls,
    distribute_files_by_genre
)

__all__ = [
    'MusicDownloader',
    'FileIterator',
    'GENRES',
    'DEFAULT_CONFIG',
    'parse_duration',
    'get_duration_from_url',
    'create_safe_filename',
    'random_urls',
    'distribute_files_by_genre'
]
