import matplotlib.pyplot as plt
import numpy as np


def visualize(
    original: np.ndarray,
    echo: np.ndarray,
    delay_samples: int,
    samplerate: int
) -> None:
    """Визуализация исходного и обработанного сигналов"""
    
    # Подготовка данных
    duration_seconds = 2  # Показываем первые 2 секунды
    samples_to_show = min(samplerate * duration_seconds, len(original))
    time_axis = np.arange(samples_to_show) / samplerate
    
    # Создание фигуры с подзаголовком
    plt.figure(figsize=(14, 10))
    plt.suptitle("Визуализация аудиосигналов: исходный vs с эхо-эффектом", 
                 fontsize=14, fontweight="bold", y=0.98)
    
    # Исходный сигнал
    ax1 = plt.subplot(3, 1, 1)
    plt.plot(
        time_axis,
        original[:samples_to_show],
        color="royalblue",
        linewidth=0.8,
        alpha=0.9
    )
    plt.title("Исходный сигнал", fontsize=12, fontweight="bold", pad=10)
    plt.xlabel("Время (секунды)")
    plt.ylabel("Амплитуда")
    plt.grid(True, alpha=0.3, linestyle="--")
    plt.ylim(-1.1, 1.1)
    ax1.set_facecolor("#f8f9fa")
    
    # Сигнал с эхо-эффектом
    ax2 = plt.subplot(3, 1, 2)
    echo_to_show = min(samples_to_show, len(echo))
    plt.plot(
        time_axis[:echo_to_show],
        echo[:echo_to_show],
        color="forestgreen",
        linewidth=0.8,
        alpha=0.9
    )
    plt.title("Сигнал с эхо-эффектом", fontsize=12, fontweight="bold", pad=10)
    plt.xlabel("Время (секунды)")
    plt.ylabel("Амплитуда")
    plt.grid(True, alpha=0.3, linestyle="--")
    plt.ylim(-1.1, 1.1)
    ax2.set_facecolor("#f8f9fa")
    
    # Дополнительная информация
    plt.subplot(3, 1, 3)
    plt.axis('off')  # Отключаем оси для текстового блока
    
    delay_seconds = delay_samples / samplerate
    info_text = (
        f"Параметры обработки:\n"
        f"• Задержка эхо: {delay_seconds:.3f} сек ({delay_samples} сэмплов)\n"
        f"• Частота дискретизации: {samplerate} Гц\n"
        f"• Длина исходного сигнала: {len(original):,} сэмплов\n"
        f"• Длина с эхо: {len(echo):,} сэмплов\n"
        f"• Показано: {duration_seconds} секунд ({samples_to_show} сэмплов)"
    )
    
    plt.text(0.1, 0.5, info_text, 
             fontsize=11, 
             verticalalignment='center',
             bbox=dict(boxstyle="round", facecolor="#e8f4f8", alpha=0.8))
    
    # Настройка общего вида
    plt.tight_layout(rect=[0, 0, 1, 0.96])  # Оставляем место для суперзаголовка
    plt.show()