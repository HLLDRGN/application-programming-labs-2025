import re
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Any, Dict


def is_valid_date(date_str: str) -> bool:
    """Проверка валидности даты в различных форматах"""
    date_patterns = [
        r'^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$',
    ]
    
    for pattern in date_patterns:
        match = re.match(pattern, date_str)
        if match:
            day, month, year = match.groups()
            
            try:
                day_int = int(day)
                month_int = int(month)
                year_int = int(year)
                
                current_year = datetime.now().year
                if year_int < 1900 or year_int > current_year:
                    return False
                
                datetime(year_int, month_int, day_int)
                
                if year_int == current_year:
                    today = datetime.now()
                    if datetime(year_int, month_int, day_int) > today:
                        return False
                
                return True
            except ValueError:
                return False
    
    return False


def extract_data_from_line(line: str) -> Tuple[Optional[str], Optional[str]]:
    """Извлечение данных из строк вида 'Фамилия: Иванов' или '1) Фамилия: Иванов'"""
    # Убираем нумерацию в начале строки (например, "1) ")
    line = re.sub(r'^\d+\)\s*', '', line.strip())
    
    # Ищем паттерн "Поле: Значение"
    match = re.match(r'^([^:]+):\s*(.+)$', line)
    if match:
        field, value = match.groups()
        return field.strip(), value.strip()
    return None, None


def parse_person_data(profile_lines: List[str]) -> Optional[Tuple[str, str]]:
    """Извлечение фамилии и даты рождения из анкеты человека"""
    surname = None
    birth_date = None
    
    for line in profile_lines:
        field, value = extract_data_from_line(line)
        
        if field and value:
            if field.lower() == 'фамилия':
                surname = value
            elif field.lower() == 'дата рождения':
                birth_date = value
    
    # Проверяем, что получили оба значения
    if surname and birth_date:
        # Проверяем, что фамилия начинается с заглавной буквы
        if not surname[0].isupper():
            return None
        
        # Проверяем валидность даты
        if is_valid_date(birth_date):
            return (surname, birth_date)
    
    return None


def calculate_age(birth_date_str: str) -> int:
    """Вычисление возраста из строки даты рождения"""
    date_pattern = r'^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$'
    match = re.match(date_pattern, birth_date_str)
    
    if match:
        day, month, year = map(int, match.groups())
        birth_date = datetime(year, month, day)
        today = datetime.now()
        
        age = today.year - birth_date.year
        
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            age -= 1
        
        return age
    
    return 0


def parse_profiles_from_content(content: str) -> List[List[str]]:
    """Разбор содержимого файла на анкеты"""
    profiles = []
    current_profile = []
    
    lines = content.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Если строка начинается с цифры и скобки (например, "1)"), это начало новой анкеты
        if re.match(r'^\d+\)', line):
            if current_profile:
                profiles.append(current_profile)
            current_profile = [line]
        else:
            current_profile.append(line)
    
    # Добавляем последнюю анкету
    if current_profile:
        profiles.append(current_profile)
    
    return profiles


def extract_person_data_from_profiles(profiles: List[List[str]]) -> List[Tuple[str, str]]:
    """Извлечение данных о людях из всех анкет"""
    person_data = []
    
    for profile_lines in profiles:
        data = parse_person_data(profile_lines)
        if data:
            person_data.append(data)
    
    return person_data


def save_sorted_data_to_file(person_data: List[Tuple[str, str]], output_path: str) -> None:
    """Сохранение отсортированных данных в файл"""
    # Сортируем по возрасту (от старшего к младшему)
    person_data.sort(key=lambda x: calculate_age(x[1]), reverse=True)
    
    # Формируем список в формате "Фамилия: дата рождения"
    result_list = [f"{surname}: {birth_date}" for surname, birth_date in person_data]
    
    with open(output_path, 'w', encoding='utf-8') as output_file:
        for item in result_list:
            output_file.write(item + '\n')
    
    return result_list


def print_results(result_list: List[str], total_profiles: int, output_filename: str) -> None:
    """Вывод результатов обработки"""
    print(f"✓ Данные успешно обработаны")
    print(f"✓ Найдено {len(result_list)} валидных записей из {total_profiles} анкет")
    print(f"✓ Результат сохранен в файл: '{output_filename}'")
    
    print("\n" + "="*60)
    print("Отсортированный список (от старшего к младшему):")
    print("="*60)
    
    # Показываем первые 20 записей или все, если их меньше
    show_count = min(20, len(result_list))
    for i, item in enumerate(result_list[:show_count], 1):
        surname, date = item.split(": ")
        age = calculate_age(date)
        print(f"{i:3}. {surname:20} {date:15} (возраст: {age} лет)")
    
    if len(result_list) > 20:
        print(f"\n... и еще {len(result_list) - 20} записей")


def main():
    parser = argparse.ArgumentParser(
        description='Обработка анкет с фамилиями и датами рождения',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python script.py data.txt
  python script.py data.txt -o result.txt
  python script.py data.txt --output sorted_results.txt
        """
    )
    
    parser.add_argument(
        'input_file',
        type=str,
        help='Путь к входному файлу с анкетами'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='sorted_by_age.txt',
        help='Путь к выходному файлу (по умолчанию: sorted_by_age.txt)'
    )
    
    args = parser.parse_args()
    
    # Проверяем существование входного файла
    if not Path(args.input_file).exists():
        print(f"✗ Ошибка: Файл '{args.input_file}' не найден.")
        print(f"  Убедитесь, что файл существует и путь указан верно.")
        sys.exit(1)
    
    try:
        # Чтение файла
        with open(args.input_file, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Разбор анкет
        profiles = parse_profiles_from_content(content)
        
        # Извлечение данных о людях
        person_data = extract_person_data_from_profiles(profiles)
        
        if not person_data:
            print("В файле не найдено валидных данных.")
            return
        
        # Сохранение отсортированных данных
        result_list = save_sorted_data_to_file(person_data, args.output)
        
        # Вывод результатов
        print_results(result_list, len(profiles), args.output)
            
    except FileNotFoundError:
        print(f"✗ Ошибка: Файл '{args.input_file}' не найден.")
        print(f"  Убедитесь, что файл находится в той же папке, что и скрипт.")
    except UnicodeDecodeError:
        print(f"✗ Ошибка: Невозможно прочитать файл '{args.input_file}' в кодировке UTF-8.")
        print(f"  Попробуйте изменить кодировку файла или указать другую кодировку.")
    except Exception as e:
        print(f"✗ Произошла ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
