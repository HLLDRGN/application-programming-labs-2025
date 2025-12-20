"""Итератор по аудиофайлам."""
import os
from typing import Iterator, List, Union


class FileIterator:
    """Итератор для перебора MP3 файлов в директории."""
    
    def __init__(self, dir_path: Union[str, os.PathLike]) -> None:
        """
        Инициализация итератора.
        
        Args:
            dir_path: Путь к директории с файлами
        """
        self.dir_path = os.path.abspath(dir_path)
        
        # Создаем директорию, если не существует
        if not os.path.exists(self.dir_path):
            os.makedirs(self.dir_path, exist_ok=True)
        
        # Собираем список MP3 файлов
        self.file_list: List[str] = self._get_mp3_files()
        self.index = 0
    
    def _get_mp3_files(self) -> List[str]:
        """
        Получает список всех MP3 файлов в директории.
        
        Returns:
            Список путей к MP3 файлам
        """
        file_list: List[str] = []
        
        if os.path.exists(self.dir_path):
            for file_name in os.listdir(self.dir_path):
                if file_name.lower().endswith('.mp3'):
                    file_list.append(os.path.join(self.dir_path, file_name))
        
        return file_list
    
    def refresh(self) -> None:
        """Обновляет список файлов."""
        self.file_list = self._get_mp3_files()
        self.index = 0
    
    def __iter__(self) -> Iterator[str]:
        """
        Возвращает итератор.
        
        Returns:
            Сам объект как итератор
        """
        return self
    
    def __next__(self) -> str:
        """
        Возвращает следующий MP3 файл.
        
        Returns:
            Путь к следующему MP3 файлу
        
        Raises:
            StopIteration: Когда файлы закончились
        """
        if self.index < len(self.file_list):
            file_path = self.file_list[self.index]
            self.index += 1
            return file_path
        raise StopIteration
    
    def __len__(self) -> int:
        """
        Возвращает количество MP3 файлов.
        
        Returns:
            Количество файлов
        """
        return len(self.file_list)
    
    def reset(self) -> None:
        """Сбрасывает итератор в начальное состояние."""
        self.index = 0
    
    def get_files(self) -> List[str]:
        """
        Возвращает список всех MP3 файлов.
        
        Returns:
            Список путей к файлам
        """
        return self.file_list.copy()
    
    def get_file_names(self) -> List[str]:
        """
        Возвращает список имен файлов.
        
        Returns:
            Список имен файлов
        """
        return [os.path.basename(path) for path in self.file_list]