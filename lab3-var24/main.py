import argparse
import sys
from audio_processor import load_audio, create_echo, save_audio
from visualization import visualize


def parse_arguments() -> argparse.Namespace:
    """Парсит аргументы командной строки для настройки эхо-эффекта"""
    
    parser = argparse.ArgumentParser(
        description="Программа для обработки аудиофайлов: добавление эхо-эффекта с визуализацией"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Путь к исходному аудиофайлу (обязательный параметр)"
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Путь для сохранения обработанного файла (обязательный параметр)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Задержка эхо в секундах (по умолчанию: 0.3)"
    )
    parser.add_argument(
        "--decay",
        type=float,
        default=0.6,
        help="Коэффициент затухания эхо (0.0-1.0, по умолчанию: 0.6)"
    )
    parser.add_argument(
        "--show-plot",
        action="store_true",
        help="Показать графики визуализации"
    )
    return parser.parse_args()


def main() -> int:
    """Основной конвейер обработки аудио"""
    
    print("=== Аудио обработчик: Эхо-эффект ===")
    args = parse_arguments()
    
    print(f"Входной файл: {args.input}")
    print(f"Выходной файл: {args.output}")
    print(f"Параметры: задержка={args.delay}с, затухание={args.decay}")
    
    try:
        # 1. Загрузка аудио
        print("\n[1/4] Загрузка аудиофайла...")
        audio_data, samplerate = load_audio(args.input)
        print(f"   ✓ Загружено: {len(audio_data)} сэмплов, частота {samplerate} Гц")
        
        # 2. Создание эхо-эффекта
        print(f"[2/4] Создание эхо-эффекта...")
        delay_samples = int(args.delay * samplerate)
        echo_data = create_echo(audio_data, delay_samples, args.decay)
        print(f"   ✓ Эхо создано: {delay_samples} сэмплов задержки")
        
        # 3. Визуализация (если нужно)
        if args.show_plot:
            print("[3/4] Визуализация сигналов...")
            visualize(audio_data, echo_data, delay_samples, samplerate)
        else:
            print("[3/4] Визуализация пропущена (используйте --show-plot)")
        
        # 4. Сохранение результата
        print("[4/4] Сохранение результата...")
        save_audio(echo_data, args.output, samplerate)
        print(f"   ✓ Файл сохранен: {args.output}")
        
        print("\n✅ Обработка завершена успешно!")
        return 0
        
    except FileNotFoundError:
        print(f"\n❌ Ошибка: Файл '{args.input}' не найден", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())