# logo_animation.py
import tkinter as tk
import math
import random

class Logo3DAnimation:
    """3D анимация вращающегося логотипа РУСМАШ"""
    
    def __init__(self, parent, width=300, height=100):
        self.parent = parent
        self.width = width
        self.height = height
        self.canvas = None
        self.angle = 0
        self.running = True
        self.particles = []
        self.glow_particles = []
        self.after_id = None
        
        # Цвета для логотипа
        self.colors = [
            '#e94560', '#ff6b6b', '#ff4757', 
            '#ff6348', '#ff7f50', '#ff4757'
        ]
        
        self.create_canvas()
        self.init_particles()
        
    def create_canvas(self):
        """Создание canvas для анимации"""
        self.canvas = tk.Canvas(
            self.parent,
            width=self.width,
            height=self.height,
            bg='#0a0a1a',
            highlightthickness=0
        )
        self.canvas.pack()
        
    def init_particles(self):
        """Инициализация частиц для свечения"""
        for _ in range(30):
            self.particles.append({
                'x': random.randint(0, self.width),
                'y': random.randint(0, self.height),
                'size': random.randint(1, 3),
                'speed_x': random.uniform(-0.5, 0.5),
                'speed_y': random.uniform(-0.5, 0.5),
                'life': random.uniform(0.5, 1.0),
                'max_life': random.uniform(50, 100)
            })
        
        for _ in range(15):
            self.glow_particles.append({
                'x': random.randint(0, self.width),
                'y': random.randint(0, self.height),
                'size': random.randint(3, 6),
                'angle': random.uniform(0, 2 * math.pi),
                'radius': random.randint(50, 120),
                'speed': random.uniform(0.01, 0.03),
                'alpha': random.uniform(0.3, 0.7)
            })
    
    def draw_3d_text(self, text, x, y, angle, scale=1.0):
        """Рисование 3D текста с эффектом вращения"""
        # Очищаем canvas
        self.canvas.delete('all')
        
        # Рисуем частицы
        for p in self.particles:
            # Движение частиц
            p['x'] += p['speed_x']
            p['y'] += p['speed_y']
            p['life'] -= 0.01
            
            if p['life'] <= 0 or p['x'] < 0 or p['x'] > self.width or p['y'] < 0 or p['y'] > self.height:
                p['x'] = random.randint(0, self.width)
                p['y'] = random.randint(0, self.height)
                p['life'] = random.uniform(0.5, 1.0)
                p['speed_x'] = random.uniform(-0.5, 0.5)
                p['speed_y'] = random.uniform(-0.5, 0.5)
            
            # Рисуем частицы с разной прозрачностью через цвет
            alpha = int(255 * p['life'])
            # Используем оттенки серого для частиц
            gray = int(200 * p['life'])
            color = f'#{gray:02x}{gray:02x}{gray:02x}'
            self.canvas.create_oval(
                p['x'] - p['size'], p['y'] - p['size'],
                p['x'] + p['size'], p['y'] + p['size'],
                fill=color,
                outline=''
            )
        
        # Рисуем свечение (используем круги с разной яркостью)
        for gp in self.glow_particles:
            gp['angle'] += gp['speed']
            x_glow = self.width // 2 + gp['radius'] * math.cos(gp['angle'])
            y_glow = self.height // 2 + gp['radius'] * math.sin(gp['angle'])
            
            # Используем оттенки синего для свечения
            intensity = int(100 * gp['alpha'])
            color = f'#{intensity:02x}{intensity:02x}{int(intensity*1.5):02x}'
            self.canvas.create_oval(
                x_glow - gp['size'], y_glow - gp['size'],
                x_glow + gp['size'], y_glow + gp['size'],
                fill=color,
                outline=''
            )
        
        # Создаем 3D эффект для текста
        letters = list(text)
        total_width = len(letters) * 45
        start_x = (self.width - total_width) // 2
        
        # Основной текст
        for i, letter in enumerate(letters):
            # Вращение вокруг оси Y
            rot_angle = angle + i * 0.3
            cos_a = math.cos(rot_angle)
            
            # Перспектива
            perspective = 0.8 + 0.2 * cos_a
            
            # Позиция буквы
            pos_x = start_x + i * 45 + 22
            pos_y = self.height // 2 + 10
            
            # Размер буквы с учетом перспективы
            size = int(28 * perspective)
            font_size = max(14, min(32, size))
            
            # Выбор цвета
            color_index = i % len(self.colors)
            base_color = self.colors[color_index]
            
            # Тень (3D эффект)
            shadow_offset = int(3 * (1 - perspective))
            shadow_color = '#0a0a1a'
            
            # Рисуем тень
            self.canvas.create_text(
                pos_x + shadow_offset + 2,
                pos_y + shadow_offset + 2,
                text=letter,
                font=("Arial", font_size, "bold"),
                fill=shadow_color
            )
            
            # Рисуем основную букву
            self.canvas.create_text(
                pos_x,
                pos_y,
                text=letter,
                font=("Arial", font_size, "bold"),
                fill=base_color
            )
            
            # Добавляем блик (светлый оттенок сверху)
            if perspective > 0.9:
                # Создаем эффект блика с помощью дополнительного текста
                highlight_color = f'#{255:02x}{255:02x}{255:02x}'
                self.canvas.create_text(
                    pos_x - 2,
                    pos_y - 3,
                    text=letter,
                    font=("Arial", font_size//2, "bold"),
                    fill=highlight_color,
                    stipple='gray50'
                )
        
        # Рисуем подпись
        self.canvas.create_text(
            self.width // 2,
            self.height - 10,
            text="⚙️ ТЕРМИНАЛ УЧЕТА",
            font=("Arial", 10),
            fill='#555577'
        )
    
    def animate(self):
        """Основной цикл анимации"""
        if not self.running:
            return
        
        try:
            # Обновляем угол вращения, скорость анимации
            self.angle += 0.08
            
            # Рисуем 3D текст
            self.draw_3d_text("РУСМАШ", self.width//2, self.height//2, self.angle)
            
            # Планируем следующий кадр
            if self.running:
                self.after_id = self.parent.after(50, self.animate)
        except Exception as e:
            print(f"Ошибка анимации: {e}")
            self.running = False
    
    def start(self):
        """Запуск анимации"""
        self.running = True
        self.animate()
    
    def stop(self):
        """Остановка анимации"""
        self.running = False
        if self.after_id:
            try:
                self.parent.after_cancel(self.after_id)
            except:
                pass
            self.after_id = None
    
    def destroy(self):
        """Уничтожение анимации"""
        self.stop()
        if self.canvas:
            try:
                self.canvas.destroy()
            except:
                pass
            self.canvas = None