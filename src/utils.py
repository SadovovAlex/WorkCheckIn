# utils.py
import random
import threading
import time
import tkinter as tk 
from datetime import datetime

class AnimationManager:
    """Управление анимациями"""
    
    @staticmethod
    def create_stars(widget, width, height, callback=None):
        """Создание мерцающих звезд на фоне"""
        def animate():
            if widget.winfo_exists():
                if random.random() < 0.08:
                    star = tk.Frame(
                        widget,
                        bg='white',
                        width=2,
                        height=2
                    )
                    x = random.randint(0, width)
                    y = random.randint(0, height)
                    star.place(x=x, y=y)
                    widget.after(500, star.destroy)
                    
            if callback and not callback():
                return
            widget.after(100, animate)
            
        return animate

class IdleMonitor:
    """Мониторинг бездействия"""
    
    def __init__(self, timeout_callback, reset_callback, timeout=10):
        self.timeout = timeout
        self.timeout_callback = timeout_callback
        self.reset_callback = reset_callback
        self.idle_count = 0
        self.is_idle = False
        self.running = True
        
    def start(self):
        """Запуск мониторинга"""
        def monitor():
            while self.running:
                time.sleep(1)
                if not self.is_idle:
                    self.idle_count += 1
                    if self.idle_count >= self.timeout:
                        self.is_idle = True
                        if self.timeout_callback:
                            self.timeout_callback()
                            
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        
    def reset(self):
        """Сброс таймера"""
        self.idle_count = 0
        if self.is_idle:
            self.is_idle = False
            if self.reset_callback:
                self.reset_callback()
                
    def stop(self):
        """Остановка мониторинга"""
        self.running = False

class TimeManager:
    """Управление временем"""
    
    @staticmethod
    def get_current_time():
        return datetime.now().strftime("%H:%M:%S")
        
    @staticmethod
    def get_current_date():
        return datetime.now().strftime("%d.%m.%Y")