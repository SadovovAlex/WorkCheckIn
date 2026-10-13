# virtual_keyboard.py
import tkinter as tk
from tkinter import font as tkfont

class VirtualKeyboard:
    """Виртуальная клавиатура для терминала"""
    
    def __init__(self, root, entry_widget=None, title="Клавиатура"):
        self.root = root
        self.entry_widget = entry_widget
        self.title = title
        self.keyboard_window = None
        self.is_visible = False
        self.current_layout = 'ru'  # 'ru' или 'en'
        
        # Раскладки клавиатуры
        self.layouts = {
            'ru': [
                ['й', 'ц', 'у', 'к', 'е', 'н', 'г', 'ш', 'щ', 'з', 'х', 'ъ'],
                ['ф', 'ы', 'в', 'а', 'п', 'р', 'о', 'л', 'д', 'ж', 'э'],
                ['я', 'ч', 'с', 'м', 'и', 'т', 'ь', 'б', 'ю', 'ё']
            ],
            'en': [
                ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']'],
                ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'"],
                ['z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/']
            ]
        }
        
        self.shift_pressed = False
        self.keys_frame = None
        self.title_label = None
    
    def show(self, entry_widget=None):
        """Показать виртуальную клавиатуру"""
        # Проверяем, существует ли еще окно и не было ли оно уничтожено
        if self.keyboard_window:
            try:
                if self.keyboard_window.winfo_exists():
                    # Если уже открыта и существует, поднимаем наверх
                    self.keyboard_window.lift()
                    self.keyboard_window.focus_force()
                    return
                else:
                    # Окно было уничтожено
                    self.keyboard_window = None
                    self.is_visible = False
            except:
                # Окно было уничтожено
                self.keyboard_window = None
                self.is_visible = False
        
        if entry_widget:
            self.entry_widget = entry_widget
        
        if not self.entry_widget:
            print("❌ Не привязано поле ввода")
            return
        
        # Проверяем, существует ли еще поле ввода
        try:
            if not self.entry_widget.winfo_exists():
                print("❌ Поле ввода было уничтожено")
                return
        except:
            print("❌ Поле ввода было уничтожено")
            return
        
        # Проверяем корневое окно
        try:
            if not self.root.winfo_exists():
                print("❌ Корневое окно было уничтожено")
                return
        except:
            print("❌ Корневое окно было уничтожено")
            return
        
        # Создаем окно клавиатуры
        try:
            self.keyboard_window = tk.Toplevel(self.root)
            self.keyboard_window.overrideredirect(True)
            self.keyboard_window.attributes('-topmost', True)
            self.keyboard_window.attributes('-alpha', 0.95)
            self.keyboard_window.configure(bg='#1a1a3e')
        except Exception as e:
            print(f"❌ Ошибка создания окна клавиатуры: {e}")
            return
        
        # Получаем размеры экрана
        try:
            screen_width = self.keyboard_window.winfo_screenwidth()
            screen_height = self.keyboard_window.winfo_screenheight()
        except:
            screen_width = 1920
            screen_height = 1080
        
        # Размеры клавиатуры
        kb_width = min(int(screen_width * 0.6), 600)
        kb_height = 350
        x = screen_width - kb_width - 20
        y = screen_height - kb_height - 20
        
        try:
            self.keyboard_window.geometry(f"{kb_width}x{kb_height}+{x}+{y}")
        except:
            return
        
        # Заголовок с кнопкой закрытия
        title_frame = tk.Frame(self.keyboard_window, bg='#1a1a3e', height=35)
        title_frame.pack(fill='x', padx=10, pady=(5, 5))
        title_frame.pack_propagate(False)
        
        # Заголовок с раскладкой
        layout_name = 'РУС' if self.current_layout == 'ru' else 'ENG'
        self.title_label = tk.Label(
            title_frame,
            text=f"⌨️ {self.title} [{layout_name}]",
            font=("Arial", 13, "bold"),
            bg='#1a1a3e',
            fg='#e94560'
        )
        self.title_label.pack(side='left')
        
        # Кнопка закрытия
        close_btn = tk.Button(
            title_frame,
            text="✕",
            font=("Arial", 14, "bold"),
            bg='#ff4444',
            fg='white',
            relief='flat',
            cursor='hand2',
            width=3,
            command=self.hide
        )
        close_btn.pack(side='right')
        
        def on_close_enter(e):
            close_btn.config(bg='#ff6666')
        
        def on_close_leave(e):
            close_btn.config(bg='#ff4444')
        
        close_btn.bind('<Enter>', on_close_enter)
        close_btn.bind('<Leave>', on_close_leave)
        
        # Основная рамка
        main_frame = tk.Frame(self.keyboard_window, bg='#1a1a3e')
        main_frame.pack(expand=True, fill='both', padx=10, pady=5)
        
        # Создаем контейнер для клавиш
        self.keys_frame = tk.Frame(main_frame, bg='#1a1a3e')
        self.keys_frame.pack(expand=True, fill='both')
        
        # Создаем клавиши
        self.create_keys()
        
        # Привязываем события
        self.keyboard_window.bind('<Escape>', lambda e: self.hide())
        self.keyboard_window.protocol("WM_DELETE_WINDOW", self.hide)
        
        self.is_visible = True
        
        # Поднимаем окно
        try:
            self.keyboard_window.lift()
            self.keyboard_window.focus_force()
        except:
            pass
    
    def create_keys(self):
        """Создание клавиш на клавиатуре"""
        if not self.keys_frame:
            return
        
        try:
            # Очищаем предыдущие клавиши
            for widget in self.keys_frame.winfo_children():
                widget.destroy()
        except:
            return
        
        layout = self.layouts[self.current_layout]
        row_index = 0
        
        # Строка с цифрами
        try:
            self.create_row(self.keys_frame, 0, [
                '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '='
            ], key_width=4)
        except:
            pass
        row_index = 1
        
        # Основные строки
        for row in layout:
            try:
                self.create_row(self.keys_frame, row_index, row, key_width=4)
            except:
                pass
            row_index += 1
        
        # Нижняя строка со специальными клавишами
        try:
            self.create_row(self.keys_frame, row_index, [
                ('🔠 РУС', 'layout_ru'), ('🔡 ENG', 'layout_en'),
                ('⇧', 'shift'), ('␣', 'space'), 
                ('⌫', 'backspace'), ('↵', 'enter'), ('✕', 'close')
            ], is_special=True, special_height=3)
        except:
            pass
    
    def create_row(self, parent, row, keys, is_special=False, key_width=5, special_height=2):
        """Создание одной строки клавиш"""
        try:
            frame = tk.Frame(parent, bg='#1a1a3e')
            frame.pack(pady=2)
            
            for key in keys:
                if is_special:
                    if isinstance(key, tuple):
                        text, action = key
                        btn = self.create_special_key(frame, text, action, special_height)
                    else:
                        btn = self.create_special_key(frame, key, key, special_height)
                else:
                    btn = self.create_key(frame, key, key_width)
                
                btn.pack(side='left', padx=2)
        except:
            pass
    
    def create_key(self, parent, char, width=5):
        """Создание обычной клавиши"""
        try:
            display_char = char.upper() if (self.current_layout == 'en' and self.shift_pressed) else char
            
            btn = tk.Button(
                parent,
                text=display_char,
                font=("Arial", 12),
                width=width,
                height=2,
                bg='#2a2a5e',
                fg='white',
                relief='flat',
                cursor='hand2',
                activebackground='#3a3a7e',
                activeforeground='white'
            )
            
            btn.bind('<Button-1>', lambda e, c=char: self.key_press(c))
            btn.bind('<Enter>', lambda e, b=btn: b.config(bg='#3a3a7e'))
            btn.bind('<Leave>', lambda e, b=btn: b.config(bg='#2a2a5e'))
            
            return btn
        except:
            return tk.Button(parent, text="")
    
    def create_special_key(self, parent, text, action, height=2):
        """Создание специальной клавиши"""
        try:
            width = 5
            bg_color = '#333366'
            font_size = 12
            
            if action == 'space':
                width = 10
                bg_color = '#2a2a5e'
            elif action == 'enter':
                width = 6
                bg_color = '#4CAF50'
            elif action == 'backspace':
                width = 6
                bg_color = '#f44336'
            elif action == 'close':
                width = 4
                bg_color = '#8B0000'
            elif action == 'layout_ru':
                width = 7
                height = 3
                bg_color = '#2196F3'
                font_size = 13
                if self.current_layout == 'ru':
                    bg_color = '#42a5f5'
            elif action == 'layout_en':
                width = 7
                height = 3
                bg_color = '#2196F3'
                font_size = 13
                if self.current_layout == 'en':
                    bg_color = '#42a5f5'
            elif action == 'shift':
                width = 5
                bg_color = '#FF9800'
                if self.shift_pressed:
                    bg_color = '#FFA726'
            
            btn = tk.Button(
                parent,
                text=text,
                font=("Arial", font_size, "bold"),
                width=width,
                height=height,
                bg=bg_color,
                fg='white',
                relief='flat',
                cursor='hand2',
                activebackground='#555588',
                activeforeground='white'
            )
            
            btn.bind('<Button-1>', lambda e, a=action: self.special_key_press(a))
            btn.bind('<Enter>', lambda e, b=btn: b.config(bg='#555588'))
            btn.bind('<Leave>', lambda e, b=btn, c=bg_color: b.config(bg=c))
            
            return btn
        except:
            return tk.Button(parent, text="")
    
    def key_press(self, char):
        """Обработка нажатия обычной клавиши"""
        if not self.entry_widget:
            return
        
        try:
            if not self.entry_widget.winfo_exists():
                return
        except:
            return
        
        # Определяем символ для вставки
        if self.current_layout == 'en' and self.shift_pressed:
            char = char.upper()
        elif self.current_layout == 'ru' and self.shift_pressed:
            char = char.upper()
        
        try:
            current_pos = self.entry_widget.index(tk.INSERT)
            self.entry_widget.insert(current_pos, char)
            self.entry_widget.icursor(current_pos + len(char))
            self.entry_widget.focus_set()
        except:
            return
        
        if self.shift_pressed and char.isalpha():
            self.shift_pressed = False
            self.update_keys()
    
    def special_key_press(self, action):
        """Обработка нажатия специальной клавиши"""
        if not self.entry_widget:
            return
        
        try:
            if not self.entry_widget.winfo_exists():
                return
        except:
            return
        
        if action == 'backspace':
            try:
                current_pos = self.entry_widget.index(tk.INSERT)
                if current_pos > 0:
                    self.entry_widget.delete(current_pos - 1, current_pos)
                    self.entry_widget.icursor(current_pos - 1)
            except:
                pass
        
        elif action == 'space':
            try:
                current_pos = self.entry_widget.index(tk.INSERT)
                self.entry_widget.insert(current_pos, ' ')
                self.entry_widget.icursor(current_pos + 1)
            except:
                pass
        
        elif action == 'enter':
            try:
                current_pos = self.entry_widget.index(tk.INSERT)
                self.entry_widget.insert(current_pos, '\n')
                self.entry_widget.icursor(current_pos + 1)
            except:
                pass
        
        elif action == 'shift':
            self.shift_pressed = not self.shift_pressed
            self.update_keys()
        
        elif action == 'layout_ru':
            self.current_layout = 'ru'
            self.shift_pressed = False
            self.update_keys()
            self.update_title()
        
        elif action == 'layout_en':
            self.current_layout = 'en'
            self.shift_pressed = False
            self.update_keys()
            self.update_title()
        
        elif action == 'close':
            self.hide()
        
        try:
            self.entry_widget.focus_set()
        except:
            pass
    
    def update_title(self):
        """Обновление заголовка с текущей раскладкой"""
        if self.title_label:
            try:
                layout_name = 'РУС' if self.current_layout == 'ru' else 'ENG'
                self.title_label.config(text=f"⌨️ {self.title} [{layout_name}]")
            except:
                pass
    
    def update_keys(self):
        """Обновление отображения клавиш"""
        self.create_keys()
        self.update_title()
    
    def hide(self):
        """Скрыть клавиатуру"""
        self.is_visible = False
        if self.keyboard_window:
            try:
                if self.keyboard_window.winfo_exists():
                    self.keyboard_window.destroy()
            except:
                pass
            self.keyboard_window = None

# Глобальный экземпляр клавиатуры
_keyboard_instance = None

def get_keyboard(root, title="Клавиатура"):
    """Получить экземпляр клавиатуры"""
    global _keyboard_instance
    
    # Проверяем, существует ли корневое окно
    try:
        if not root.winfo_exists():
            _keyboard_instance = None
            return None
    except:
        _keyboard_instance = None
        return None
    
    if _keyboard_instance is None:
        _keyboard_instance = VirtualKeyboard(root, title=title)
    else:
        # Обновляем корневое окно если изменилось
        try:
            if not _keyboard_instance.root.winfo_exists():
                _keyboard_instance = VirtualKeyboard(root, title=title)
        except:
            _keyboard_instance = VirtualKeyboard(root, title=title)
    
    return _keyboard_instance

def show_keyboard(entry_widget, root=None, title="Клавиатура"):
    """Показать клавиатуру для поля ввода"""
    try:
        if root is None:
            root = entry_widget.winfo_toplevel()
        
        if not root.winfo_exists():
            print("❌ Корневое окно не существует")
            return None
    except:
        print("❌ Не удалось получить корневое окно")
        return None
    
    kb = get_keyboard(root, title)
    if kb:
        kb.show(entry_widget)
    return kb