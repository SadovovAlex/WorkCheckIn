# ui_parts.py
import tkinter as tk
from tkinter import font as tkfont
from src.config import PARTS

class PartsList:
    """Список деталей с прокруткой"""
    
    def __init__(self, parent, width, height):
        self.parent = parent
        self.width = width
        self.height = height
        self.parts = PARTS
        
    def create(self):
        """Создание виджета со списком деталей"""
        # Основной контейнер
        container = tk.Frame(self.parent, bg='#0a0a1a', width=self.width)
        container.pack(side='right', fill='y', padx=(0, 10), pady=10)
        container.pack_propagate(False)
        
        # Заголовок
        title = tk.Label(
            container,
            text="📦 ПРОИЗВОДСТВО",
            font=("Arial", 20, "bold"),
            bg='#0a0a1a',
            fg='#e94560'
        )
        title.pack(pady=(0, 10))
        
        # Canvas для прокрутки
        canvas_frame = tk.Frame(container, bg='#0a0a1a')
        canvas_frame.pack(expand=True, fill='both')
        
        canvas = tk.Canvas(
            canvas_frame,
            bg='#0a0a1a',
            highlightthickness=0,
            width=self.width - 20
        )
        canvas.pack(side='left', fill='both', expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(
            canvas_frame,
            orient='vertical',
            command=canvas.yview,
            bg='#1a1a3e',
            troughcolor='#0a0a1a'
        )
        scrollbar.pack(side='right', fill='y')
        canvas.config(yscrollcommand=scrollbar.set)
        
        # Внутренний фрейм
        scroll_frame = tk.Frame(canvas, bg='#0a0a1a')
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        
        # Добавляем детали
        for part in self.parts:
            self.create_part_item(scroll_frame, part)
            
        # Обновляем область прокрутки
        scroll_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox('all'))
        
        # Привязываем прокрутку колесиком мыши
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        canvas.bind('<MouseWheel>', on_mousewheel)
        
        return container
        
    def create_part_item(self, parent, part):
        """Создание элемента списка деталей"""
        item = tk.Frame(
            parent,
            bg='#1a1a3e',
            relief='flat',
            bd=1
        )
        item.pack(fill='x', padx=5, pady=3)
        
        # Статус (цветной индикатор)
        status_indicator = tk.Frame(
            item,
            bg=part["color"],
            width=5
        )
        status_indicator.pack(side='left', fill='y', padx=(0, 10))
        
        # Информация
        info_frame = tk.Frame(item, bg='#1a1a3e')
        info_frame.pack(side='left', fill='x', expand=True, padx=5, pady=5)
        
        # Название
        name_label = tk.Label(
            info_frame,
            text=part["name"],
            font=("Arial", 13, "bold"),
            bg='#1a1a3e',
            fg='white',
            anchor='w'
        )
        name_label.pack(fill='x')
        
        # Количество и статус
        bottom_frame = tk.Frame(info_frame, bg='#1a1a3e')
        bottom_frame.pack(fill='x')
        
        stock_label = tk.Label(
            bottom_frame,
            text=f"{part['stock']} шт.",
            font=("Arial", 12),
            bg='#1a1a3e',
            fg=part["color"]
        )
        stock_label.pack(side='left')
        
        status_label = tk.Label(
            bottom_frame,
            text=part["status"],
            font=("Arial", 11),
            bg='#1a1a3e',
            fg=part["color"]
        )
        status_label.pack(side='right')