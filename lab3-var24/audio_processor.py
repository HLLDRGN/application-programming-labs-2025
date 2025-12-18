import numpy as np
import soundfile as sf
from typing import Tuple


def load_audio(filepath: str) -> Tuple[np.ndarray, int]:
    """Загружает аудиофайл и возвращает данные и частоту дискретизации"""
    try:
        data, samplerate = sf.read(filepath)
        # Нормализация, если нужно
        if np.max(np.abs(data)) > 1.0:
            data = data / np.max(np.abs(data))
        return data, samplerate
    except FileNotFoundError:
        raise FileNotFoundError(f"Аудиофайл не найден: {filepath}")
    except Exception as e:
        raise RuntimeError(f"Ошибка загрузки аудио: {e}")


def create_echo(audio_data: np.ndarray, delay_samples: int, decay: float) -> np.ndarray:
    """Создаёт эхо-эффект путём наложения задержанного сигнала"""
    # Проверка параметров
    if decay < 0 or decay > 1:
        raise ValueError("Коэффициент затухания должен быть между 0.0 и 1.0")
    if delay_samples < 0:
        raise ValueError("Задержка не может быть отрицательной")
    
    output_size = len(audio_data) + delay_samples

    if len(audio_data.shape) == 1:
        result = np.zeros(output_size, dtype=audio_data.dtype)
    else:
        result = np.zeros((output_size, audio_data.shape[1]), dtype=audio_data.dtype)

    result[:len(audio_data)] = audio_data
    result[delay_samples:delay_samples + len(audio_data)] += (audio_data * decay)

    return result


def save_audio(audio_data: np.ndarray, filepath: str, samplerate: int) -> None:
    """Сохраняет аудиофайл с указанным именем"""
    try:
        sf.write(filepath, audio_data, samplerate)
    except Exception as e:
        raise RuntimeError(f"Ошибка сохранения аудио: {e}")