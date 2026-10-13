# src/report_generator.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime
from src.config import EMPLOYEES, get_employee_status, get_work_time, APP_SETTINGS
import json
import glob

# Корень проекта — на уровень выше src (check-in/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
PHOTOS_DIR = os.path.join(BASE_DIR, "photos")


class ReportGenerator:
    """Генератор отчетов с фотографиями"""

    def __init__(self):
        self.settings = APP_SETTINGS.copy()
        self.load_settings()

    def load_settings(self):
        """Загрузка настроек из settings.json в корне проекта (секция app_settings)"""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # ✅ Читаем именно app_settings
                self.settings.update(data.get("app_settings", {}))
            except Exception as e:
                print(f"⚠️ ReportGenerator: не удалось загрузить settings.json: {e}")

    def get_employee_photos_for_date(self, date_str=None):
        """Получить фотографии сотрудников за указанную дату"""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        photos_path = os.path.join(PHOTOS_DIR, date_str)
        photos = {}

        if os.path.exists(photos_path):
            for ext in ['jpg', 'jpeg', 'png']:
                pattern = os.path.join(photos_path, f"*.{ext}")
                for filepath in glob.glob(pattern):
                    filename = os.path.basename(filepath)
                    name_parts = filename.split('_')
                    if len(name_parts) >= 2:
                        employee_name = name_parts[0]
                        if employee_name not in photos:
                            photos[employee_name] = []
                        photos[employee_name].append({
                            'path': filepath,
                            'filename': filename,
                            'time': name_parts[1].replace('.jpg', '').replace('.jpeg', '').replace('.png', '')
                        })

        return photos

    def generate_report(self):
        """Генерация отчета для мастера цеха"""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        arrived_employees = []
        left_employees = []
        current_employees = []
        forgot_employees = []                          # ← «забыли нажать УШЁЛ»

        for emp in EMPLOYEES:
            emp_id = emp["id"]
            status_info = get_employee_status(emp_id)
            status = status_info.get("status", "off")

            # В config.py: приход = "time", уход = "checkout_time"
            checkin_time  = status_info.get("time")
            checkout_time = status_info.get("checkout_time")
            checkin_date  = status_info.get("date")               # ← дата прихода
            forgot        = status_info.get("forgot_checkout", False)

            # ⚠️ Показываем в отчёте ТОЛЬКО тех, кто пришёл СЕГОДНЯ
            if checkin_date != date_str:
                # Сотрудник приходил в другой день.
                # Если он сейчас "on" — всё равно показываем как текущего,
                # но в «Пришли сегодня» НЕ добавляем.
                if status == "on":
                    current_employees.append({
                        'emp': emp,
                        'checkin_time': checkin_time,
                        'checkout_time': checkout_time,
                    })
                continue

            employee_record = {
                'emp': emp,
                'checkin_time': checkin_time,
                'checkout_time': checkout_time,
            }

            # Все, у кого есть время прихода и дата == сегодня
            if checkin_time:
                arrived_employees.append(employee_record)

            # Все, у кого есть время ухода и дата == сегодня
            if checkout_time:
                if forgot:
                    forgot_employees.append(employee_record)   # ← отдельный список
                else:
                    left_employees.append(employee_record)

            # Кто сейчас на работе
            if status == "on":
                current_employees.append(employee_record)

        photos = self.get_employee_photos_for_date(date_str)

        html_content = self.generate_html_report(
            arrived_employees,
            left_employees,
            current_employees,
            forgot_employees,
            photos,
            date_str,
            time_str
        )

        return {
            'html': html_content,
            'date': date_str,
            'time': time_str,
            'photos': photos,
            'arrived_count': len(arrived_employees),
            'left_count': len(left_employees),
            'current_count': len(current_employees),
            'forgot_count': len(forgot_employees),
            'total_photos': sum(len(photos[emp_name]) for emp_name in photos)
        }

    def generate_html_report(self, arrived, left, current, forgot, photos, date_str, time_str):
        """Создание красивого HTML отчета"""

        # Форматируем время для отображения
        def format_time(time_str):
            try:
                if ':' in time_str:
                    parts = time_str.split(':')
                    if len(parts) >= 2:
                        return f"{parts[0]}:{parts[1]}"
                return time_str
            except:
                return time_str

        # Строим HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background-color: #f5f5f5;
                    margin: 0;
                    padding: 20px;
                    color: #333;
                }}
                .container {{
                    max-width: 900px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #1a1a3e 0%, #2a1a5e 100%);
                    color: white;
                    padding: 30px 40px;
                    border-bottom: 4px solid #e94560;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .header .subtitle {{
                    margin-top: 8px;
                    font-size: 16px;
                    color: #aaaadd;
                }}
                .content {{
                    padding: 30px 40px;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                    gap: 15px;
                    margin-bottom: 30px;
                }}
                .stat-card {{
                    background: #f8f9fa;
                    border-radius: 8px;
                    padding: 15px 20px;
                    border-left: 4px solid #e94560;
                }}
                .stat-card .number {{
                    font-size: 32px;
                    font-weight: bold;
                    color: #1a1a3e;
                }}
                .stat-card .label {{
                    font-size: 14px;
                    color: #666;
                    margin-top: 4px;
                }}
                .stat-card.green {{ border-left-color: #4CAF50; }}
                .stat-card.orange {{ border-left-color: #FF9800; }}
                .stat-card.blue {{ border-left-color: #2196F3; }}
                .stat-card.warn {{ border-left-color: #FF5722; }}

                .section {{
                    margin-top: 30px;
                    border-top: 2px solid #eee;
                    padding-top: 25px;
                }}
                .section-title {{
                    font-size: 20px;
                    font-weight: 600;
                    color: #1a1a3e;
                    margin-bottom: 15px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                .employee-list {{
                    list-style: none;
                    padding: 0;
                    margin: 0;
                }}
                .employee-item {{
                    padding: 12px 16px;
                    background: #f8f9fa;
                    border-radius: 6px;
                    margin-bottom: 8px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    transition: all 0.3s;
                }}
                .employee-item:hover {{
                    background: #f0f1f3;
                    transform: translateX(5px);
                }}
                .employee-name {{
                    font-weight: 500;
                    font-size: 16px;
                }}
                .employee-time {{
                    color: #666;
                    font-size: 14px;
                    background: #e9ecef;
                    padding: 4px 12px;
                    border-radius: 12px;
                }}
                .employee-avatar {{
                    font-size: 24px;
                    margin-right: 10px;
                }}
                .photos-section {{
                    margin-top: 30px;
                    border-top: 2px solid #eee;
                    padding-top: 25px;
                }}
                .photos-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
                    gap: 15px;
                    margin-top: 15px;
                }}
                .photo-item {{
                    background: #f8f9fa;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    text-align: center;
                    padding: 10px;
                }}
                .photo-item img {{
                    width: 100%;
                    height: auto;
                    border-radius: 4px;
                    max-height: 150px;
                    object-fit: cover;
                }}
                .photo-item .photo-name {{
                    font-size: 12px;
                    color: #666;
                    margin-top: 6px;
                    font-weight: 500;
                }}
                .photo-item .photo-time {{
                    font-size: 11px;
                    color: #999;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px 40px;
                    text-align: center;
                    color: #888;
                    font-size: 13px;
                    border-top: 1px solid #eee;
                }}
                .badge {{
                    display: inline-block;
                    padding: 3px 10px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                .badge-green {{ background: #d4edda; color: #155724; }}
                .badge-red {{ background: #f8d7da; color: #721c24; }}
                .badge-orange {{ background: #fff3cd; color: #856404; }}

                @media (max-width: 600px) {{
                    .header {{ padding: 20px; }}
                    .content {{ padding: 20px; }}
                    .stats-grid {{ grid-template-columns: 1fr 1fr; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏭 Отчет по сотрудникам цеха</h1>
                    <div class="subtitle">
                        📅 {date_str} | 🕐 {time_str}
                    </div>
                </div>

                <div class="content">
                    <!-- Статистика -->
                    <div class="stats-grid">
                        <div class="stat-card green">
                            <div class="number">{len(arrived)}</div>
                            <div class="label">✅ Пришли сегодня</div>
                        </div>
                        <div class="stat-card orange">
                            <div class="number">{len(left)}</div>
                            <div class="label">❌ Ушли сегодня</div>
                        </div>
                        <div class="stat-card blue">
                            <div class="number">{len(current)}</div>
                            <div class="label">👤 Сейчас на работе</div>
                        </div>
                        <div class="stat-card warn">
                            <div class="number">{len(forgot)}</div>
                            <div class="label">⚠️ Забыли нажать «УШЁЛ»</div>
                        </div>
                        <div class="stat-card">
                            <div class="number">{sum(len(photos[emp_name]) for emp_name in photos)}</div>
                            <div class="label">📸 Фотографий за день</div>
                        </div>
                    </div>

                    <!-- Пришедшие сотрудники -->
                    <div class="section">
                        <div class="section-title">
                            <span>✅ Пришедшие сотрудники</span>
                            <span class="badge badge-green">{len(arrived)}</span>
                        </div>
                        <ul class="employee-list">
        """

        if arrived:
            for item in arrived:
                emp = item['emp']
                time = item.get('checkin_time') or "—"
                has_photo = emp["name"] in photos
                html += f"""
                            <li class="employee-item">
                                <span>
                                    <span class="employee-avatar">{emp['avatar']}</span>
                                    <span class="employee-name">{emp['name']}</span>
                                    <span style="color:#888;font-size:14px;margin-left:10px;">{emp['position']}</span>
                                </span>
                                <span>
                                    <span class="employee-time">🕐 {time}</span>
                                    {f'<span style="margin-left:10px;color:#4CAF50;">📸</span>' if has_photo else ''}
                                </span>
                            </li>
                """
        else:
            html += """
                            <li class="employee-item" style="color:#999;justify-content:center;">
                                Нет пришедших сотрудников
                            </li>
            """

        html += f"""
                        </ul>
                    </div>

                    <!-- Ушедшие сотрудники -->
                    <div class="section">
                        <div class="section-title">
                            <span>❌ Ушедшие сотрудники</span>
                            <span class="badge badge-red">{len(left)}</span>
                        </div>
                        <ul class="employee-list">
        """

        if left:
            for item in left:
                emp = item['emp']
                time = item.get('checkout_time') or "—"
                html += f"""
                            <li class="employee-item">
                                <span>
                                    <span class="employee-avatar">{emp['avatar']}</span>
                                    <span class="employee-name">{emp['name']}</span>
                                    <span style="color:#888;font-size:14px;margin-left:10px;">{emp['position']}</span>
                                </span>
                                <span class="employee-time">🕐 {time}</span>
                            </li>
                """
        else:
            html += """
                            <li class="employee-item" style="color:#999;justify-content:center;">
                                Нет ушедших сотрудников
                            </li>
            """

        html += f"""
                        </ul>
                    </div>

                    <!-- Забыли нажать УШЁЛ -->
                    <div class="section">
                        <div class="section-title">
                            <span>⚠️ Забыли нажать «УШЁЛ»</span>
                            <span class="badge badge-orange">{len(forgot)}</span>
                        </div>
                        <ul class="employee-list">
        """

        if forgot:
            for item in forgot:
                emp = item['emp']
                checkin = item.get('checkin_time') or "—"
                checkout = item.get('checkout_time') or "—"
                html += f"""
                            <li class="employee-item" style="border-left:4px solid #FF9800;">
                                <span>
                                    <span class="employee-avatar">{emp['avatar']}</span>
                                    <span class="employee-name">{emp['name']}</span>
                                    <span style="color:#888;font-size:14px;margin-left:10px;">{emp['position']}</span>
                                </span>
                                <span>
                                    <span class="employee-time">🕐 {checkin} → {checkout}</span>
                                    <span class="badge badge-orange" style="margin-left:8px;">Авто-закрыто</span>
                                </span>
                            </li>
                """
        else:
            html += """
                            <li class="employee-item" style="color:#999;justify-content:center;">
                                Нет сотрудников, забывших нажать «УШЁЛ»
                            </li>
            """

        html += f"""
                        </ul>
                    </div>

                    <!-- Текущие на работе -->
                    <div class="section">
                        <div class="section-title">
                            <span>👤 Сейчас на работе</span>
                            <span class="badge badge-orange">{len(current)}</span>
                        </div>
                        <ul class="employee-list">
        """

        if current:
            for item in current:
                emp = item['emp']
                work_time = get_work_time(emp["id"])
                html += f"""
                            <li class="employee-item">
                                <span>
                                    <span class="employee-avatar">{emp['avatar']}</span>
                                    <span class="employee-name">{emp['name']}</span>
                                    <span style="color:#888;font-size:14px;margin-left:10px;">{emp['position']}</span>
                                </span>
                                <span class="employee-time">⏱️ {work_time}</span>
                            </li>
                """
        else:
            html += """
                            <li class="employee-item" style="color:#999;justify-content:center;">
                                Нет сотрудников на работе
                            </li>
            """

        html += """
                        </ul>
                    </div>
        """

        # Фотографии
        if photos:
            html += """
                    <div class="photos-section">
                        <div class="section-title">📸 Фотографии сотрудников за день</div>
                        <div class="photos-grid">
            """

            for employee_name, photo_list in photos.items():
                for photo in photo_list[:3]:  # Показываем до 3 фото на сотрудника
                    html += f"""
                            <div class="photo-item">
                                <img src="cid:{photo['filename']}" alt="{employee_name}">
                                <div class="photo-name">{employee_name}</div>
                                <div class="photo-time">🕐 {photo['time'][:4]}:{photo['time'][4:6]}</div>
                            </div>
                    """

            html += """
                        </div>
                    </div>
            """

        html += f"""
                </div>

                <div class="footer">
                    <p>📧 Это автоматическое сообщение сгенерировано системой учета сотрудников</p>
                    <p style="font-size:11px;color:#aaa;">Не отвечайте на это письмо</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def send_report(self):
        """Отправка отчета по email (с подробным логированием)"""
        import traceback
        from datetime import datetime as _dt

        def log(msg):
            ts = _dt.now().strftime("%H:%M:%S")
            print(f"[{ts}] [REPORT] {msg}")

        log("=" * 60)
        log("🚀 Начало отправки отчета")

        # ---------- 1. Загрузка настроек ----------
        try:
            self.load_settings()
            log("📂 Настройки загружены из settings.json")
        except Exception as e:
            log(f"❌ Не удалось загрузить настройки: {e}")
            return False

        smtp_server = self.settings.get("email_smtp_server", "")
        smtp_port   = self.settings.get("email_smtp_port", 587)
        sender      = self.settings.get("email_sender", "")
        password    = self.settings.get("email_password", "")
        receiver    = self.settings.get("email_receiver", "")

        log(f"   SMTP сервер : {smtp_server}")
        log(f"   SMTP порт   : {smtp_port}")
        log(f"   Отправитель : {sender}")
        log(f"   Получатель  : {receiver}")
        log(f"   Пароль      : {'*' * len(password) if password else '(пусто)'}")

        # ---------- 2. Проверка настроек ----------
        missing = []
        if not smtp_server: missing.append("email_smtp_server")
        if not smtp_port:   missing.append("email_smtp_port")
        if not sender:      missing.append("email_sender")
        if not password:    missing.append("email_password")
        if not receiver:    missing.append("email_receiver")

        if missing:
            log(f"❌ Не заполнены поля: {', '.join(missing)}")
            return False

        try:
            smtp_port = int(smtp_port)
        except (TypeError, ValueError):
            log(f"❌ Некорректный порт: {smtp_port}")
            return False

        # ---------- 3. Генерация отчета ----------
        try:
            log("📝 Генерация HTML-отчета...")
            report_data = self.generate_report()
            log(f"   ✅ Отчет сгенерирован: "
                f"{report_data['arrived_count']} пришли, "
                f"{report_data['left_count']} ушли, "
                f"{report_data['current_count']} на работе, "
                f"{report_data['forgot_count']} забыли УШЁЛ, "
                f"{report_data['total_photos']} фото")
        except Exception as e:
            log(f"❌ Ошибка генерации отчета: {e}")
            traceback.print_exc()
            return False

        # ---------- 4. Сборка письма ----------
        try:
            log("✉️ Сборка MIME-сообщения...")
            msg = MIMEMultipart('related')
            msg['From'] = sender
            msg['To'] = receiver
            msg['Subject'] = (
                f"🏭 Отчет по сотрудникам цеха от "
                f"{report_data['date']} {report_data['time']}"
            )

            msg_html = MIMEText(report_data['html'], 'html', 'utf-8')
            msg.attach(msg_html)
            log("   ✅ HTML-часть прикреплена")

            # Прикрепляем фотографии
            attached_photos = 0
            failed_photos = 0
            for employee_name, photo_list in report_data['photos'].items():
                for photo in photo_list:
                    try:
                        with open(photo['path'], 'rb') as f:
                            img_data = f.read()
                        img = MIMEImage(img_data)
                        # Определяем подтип по расширению
                        ext = os.path.splitext(photo['filename'])[1].lower()
                        if ext in ('.jpg', '.jpeg'):
                            img.add_header('Content-Type', 'image/jpeg')
                        elif ext == '.png':
                            img.add_header('Content-Type', 'image/png')
                        img.add_header('Content-ID', f'<{photo["filename"]}>')
                        img.add_header('Content-Disposition', 'inline',
                                       filename=photo['filename'])
                        msg.attach(img)
                        attached_photos += 1
                    except Exception as e:
                        failed_photos += 1
                        log(f"   ⚠️ Не удалось прикрепить {photo['filename']}: {e}")

            log(f"   ✅ Прикреплено фото: {attached_photos} "
                f"(ошибок: {failed_photos})")

            total_size = len(msg.as_string())
            log(f"   📦 Размер письма: ~{total_size / 1024:.1f} КБ")
        except Exception as e:
            log(f"❌ Ошибка сборки письма: {e}")
            traceback.print_exc()
            return False

        # ---------- 5. Подключение к SMTP ----------
        log(f"🔌 Подключение к {smtp_server}:{smtp_port} ...")
        try:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
            log("   ✅ TCP-соединение установлено")
        except Exception as e:
            log(f"❌ Не удалось подключиться к SMTP: {e}")
            return False

        try:
            # EHLO
            try:
                code, msg_ehlo = server.ehlo()
                log(f"   EHLO → {code}")
            except Exception as e:
                log(f"   ⚠️ EHLO не удался: {e}")

            # STARTTLS
            try:
                log("   🔒 STARTTLS ...")
                server.starttls()
                server.ehlo()
                log("   ✅ TLS-шифрование включено")
            except Exception as e:
                log(f"   ⚠️ STARTTLS не удался: {e} "
                    f"(продолжаем без шифрования)")

            # LOGIN
            log("   🔑 Авторизация ...")
            try:
                server.login(sender, password)
                log("   ✅ Авторизация успешна")
            except smtplib.SMTPAuthenticationError as e:
                log(f"❌ Ошибка авторизации: {e}")
                log("   Проверьте логин/пароль. Для Gmail нужен app-password.")
                server.quit()
                return False
            except Exception as e:
                log(f"❌ Ошибка авторизации: {e}")
                server.quit()
                return False

            # SEND
            log("   📤 Отправка письма ...")
            try:
                server.send_message(msg)
                log("   ✅ Письмо отправлено")
            except Exception as e:
                log(f"❌ Ошибка отправки: {e}")
                server.quit()
                return False

            # QUIT
            try:
                server.quit()
                log("   👋 Соединение закрыто")
            except Exception:
                pass

            log(f"🎉 Отчет успешно отправлен на {receiver}")
            log("=" * 60)
            return True

        except Exception as e:
            log(f"❌ Непредвиденная ошибка SMTP: {e}")
            traceback.print_exc()
            try:
                server.quit()
            except Exception:
                pass
            return False


# Глобальный экземпляр
report_generator = ReportGenerator()