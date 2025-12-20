"""Основной модуль программы."""
import argparse
import os
import sys
import traceback
from typing import NoReturn

from downloader import MusicDownloader
from iterator import FileIterator
from config import GENRES


def parse_arguments() -> argparse.Namespace:
    """
    Парсит аргументы командной строки.
    
    Returns:
        Пространство имен с аргументами
    """
    parser = argparse.ArgumentParser(
        description='Скачивание музыки с Mixkit по жанрам'
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


def print_summary(stats: dict, output_dir: str, csv_path: str) -> None:
    """
    Выводит итоговую статистику.
    
    Args:
        stats: Статистика скачивания
        output_dir: Папка с файлами
        csv_path: Путь к CSV файлу
    """
    print(f"\n{'='*60}")
    print("ИТОГИ:")
    print(f"{'='*60}")
    print(f"Всего скачано файлов: {stats['total_downloaded']}")
    print(f"Целевое количество: {stats['total_target']}")
    
    if stats['total_downloaded'] < stats['total_target']:
        print(f"Внимание: скачано меньше целевого количества "
              f"на {stats['total_target'] - stats['total_downloaded']} файлов")
    
    print(f"\nПо жанрам:")
    for genre, count in stats['by_genre'].items():
        print(f"  {genre}: {count} файлов")


def demonstrate_iterator(output_dir: str) -> None:
    """
    Демонстрирует работу итератора.
    
    Args:
        output_dir: Папка с файлами
    """
    print(f"\n{'='*60}")
    print("ДЕМОНСТРАЦИЯ ИТЕРАТОРА:")
    print(f"{'='*60}")
    
    try:
        iterator = FileIterator(output_dir)
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


def main() -> None:
    """Основная функция программы."""
    try:
        # Парсим аргументы
        args = parse_arguments()
        
        # Создаем конфигурацию
        config = {
            'max_pages': args.max_pages,
            'csv_path': args.csv_path
        }
        
        # Создаем загрузчик
        downloader = MusicDownloader(config)
        
        # Скачиваем музыку
        stats = downloader.download_music(
            output_dir=args.output_dir,
            csv_path=args.csv_path,
            min_files=args.min_files,
            max_files=args.max_files
        )
        
        # Выводим статистику
        print_summary(stats, args.output_dir, args.csv_path)
        
        # Демонстрируем итератор
        demonstrate_iterator(args.output_dir)
        
        # Финальное сообщение
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