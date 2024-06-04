from PIL import Image, ImageTk
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from pathlib import Path
from screeninfo import get_monitors
from tkinter import ttk, messagebox, filedialog
import glob
import json
import pystray
import random
import re
import requests
import threading
import tkinter as tk
import webbrowser
import contextlib
with contextlib.redirect_stdout(None):
    import pygame




class AlarmManager:
    def __init__(self, app):
        try:
            pygame.mixer.init()
            self.intialized = True
            self.channels = {i: None for i in range(pygame.mixer.get_num_channels())}  # 8 channels by default?
        except Exception as e:
            print(e)
            self.intialized = False
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.jobs = {}
        self.app = app

    def update_alarm(self, alarm_id, alarm_data):
        if alarm_id in self.jobs:
            self.jobs[alarm_id].remove()

        hour, minute = map(int, alarm_data['time'].split(':'))
        trigger = CronTrigger(hour = hour, minute = minute, second=0)
        job = self.scheduler.add_job(self.play_sound, trigger, args=[alarm_data['music']])
        self.jobs[alarm_id] = job

    def delete_alarm(self, alarm_id):
        if alarm_id in self.jobs:
            self.jobs[alarm_id].remove()
            del self.jobs[alarm_id]

    def play_sound(self, sound_file):
        try:
            sound = pygame.mixer.Sound(sound_file)
            available_channel = self.find_available_channel()
            if available_channel and self.intialized:
                available_channel.play(sound)
                self.app.root.deiconify()
        except Exception as e:
            print('Error playing sound: ', e)

    def find_available_channel(self):
        for i in range(pygame.mixer.get_num_channels()):
            if not pygame.mixer.Channel(i).get_busy():
                return pygame.mixer.Channel(i)
        return None

    def stop_all_sounds(self):
        try:
            pygame.mixer.stop()
        except Exception as e:
            print(e)

    def shutdown(self):
        try:
            pygame.mixer.quit()
            self.scheduler.shutdown()
        except Exception as e:
            print(e)


class EditAlarmDialog:
    def __init__(self, master, app, alarm_index, alarm_data, update_callback, delete_callback):
        self.main_app = app
        self.top = tk.Toplevel(master)
        self.load_alarm_dialog_position()
        self.top.protocol('WM_DELETE_WINDOW', self.on_close)
        self.top.title('Edit Alarm')
        self.top.iconbitmap('images/icon.ico')
        self.top.transient(master)
        self.top.grab_set()
        self.top.lift()
        self.top.focus_set()

        self.alarm_data = alarm_data if alarm_data else { 'time': '', 'music': '', 'name': '' }
        self.update_callback = update_callback
        self.delete_callback = delete_callback
        self.alarm_index = alarm_index

        self.name_frame = tk.Frame(self.top)
        self.name_frame.pack(fill=tk.X, padx=5)
        self.name_image = tk.PhotoImage(file='images/edit.png')
        tk.Label(self.name_frame, image=self.name_image).pack(side=tk.LEFT, pady=5)
        self.name_entry = tk.Entry(self.name_frame)
        self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.name_entry.insert('0', self.alarm_data.get('name', ''))

        self.time_frame = tk.Frame(self.top)
        self.time_frame.pack(fill=tk.X, padx=5)
        self.time_image = tk.PhotoImage(file='images/alarm.png')
        tk.Label(self.time_frame, image=self.time_image).pack(side=tk.LEFT, pady=5)
        self.time_entry = tk.Entry(self.time_frame)
        self.time_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.time_entry.insert(0, self.alarm_data.get('time', ''))

        self.music_entry_frame = ttk.Frame(self.top)
        self.music_entry_frame.pack(fill=tk.X, padx=5)
        self.music_entry_image = tk.PhotoImage(file='images/note.png')
        ttk.Label(self.music_entry_frame, image=self.music_entry_image).pack(side=tk.LEFT, pady=5)
        self.music_entry = ttk.Entry(self.music_entry_frame)
        self.music_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.music_entry.insert(0, self.alarm_data.get('music', ''))
        self.music_button_image = tk.PhotoImage(file='images/search.png')
        self.music_button = ttk.Button(self.music_entry_frame, image=self.music_button_image, command=self.browse_music)
        self.music_button.pack(side=tk.RIGHT)

        self.bottom_frame = ttk.Frame(self.top)
        self.bottom_frame.pack(fill=tk.X, pady=5)
        ttk.Button(self.bottom_frame, text='Save', command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.bottom_frame, text='Delete', command=self.delete).pack(side=tk.RIGHT, padx=5)

    def browse_music(self):
        file_path = filedialog.askopenfilename(
            filetypes=[('Audio Files', '*.mp3 *.wav *.ogg'), ('All Files', '*.*')])
        if file_path:
            self.music_entry.delete(0, tk.END)
            self.music_entry.insert(0, file_path)

    def validate_time(self, time_str):
        """ Validate time foramat HH:MM """
        if not re.match(r'^\d{2}:\d{2}$', time_str):
            return False
        hour, minute = map(int, time_str.split(':'))
        return 0 <= hour < 24 and 0 <= minute < 60

    def save(self):
        self.alarm_data['time'] = self.time_entry.get()
        self.alarm_data['music'] = self.music_entry.get()
        self.alarm_data['name'] = self.name_entry.get()

        if not self.validate_time(self.alarm_data['time']):
            messagebox.showerror('Invalid Time', 'Please enter a valid time in the format HH:MM')
            return

        self.update_callback(self.alarm_index, self.alarm_data)
        self.on_close()

    def delete(self):
        self.delete_callback(self.alarm_index)
        self.on_close()

    def load_alarm_dialog_position(self):
        pos = self.main_app.data.get('AlarmDialogPosition', '+1000+500')
        self.top.geometry(pos)

    def save_alarm_dialog_position(self):
        pos = f'+{self.top.winfo_x()}+{self.top.winfo_y()}'
        self.main_app.data['AlarmDialogPosition'] = pos
        self.main_app.save_data()

    def on_close(self):
        self.save_alarm_dialog_position()
        self.top.destroy()


class SettingsWindow:
    def __init__(self, master, alarm_manager):
        self.master = master
        self.top = tk.Toplevel(master.root)
        self.load_window_position()
        self.top.protocol('WM_DELETE_WINDOW', self.on_close)
        self.top.title('Settings')
        self.top.iconbitmap('images/icon.ico')
        self.top.transient(master.root)
        self.top.grab_set() # Direct all events to this window
        # self.top.lift()
        # self.top.focus_set()

        self.notebook = ttk.Notebook(self.top)
        self.notebook.pack(fill='both', expand=True)

        self.alarm_tab = ttk.Frame(self.notebook)
        self.timer_tab = ttk.Frame(self.notebook)
        self.bg_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.alarm_tab, text='アラーム')
        self.notebook.add(self.timer_tab, text='キャラ選択')
        self.notebook.add(self.bg_tab, text='背景選択')

        self.populate_alarm_tab()
        self.populate_chara_tab()
        self.populate_bg_tab()
        self.load_alarms()
        self.alarm_manager = alarm_manager

        self.top.wait_window()  # Wait for the window to be closed

    def add_alarm(self):
        new_alarm = {'time': '07:00', 'music': 'audios/default.mp3', 'name': ''}
        self.alarms.append(new_alarm)
        self.display_alarms()

    def edit_alarm(self, index):
        data = self.alarms[index]
        EditAlarmDialog(self.top, self.master, index, data, self.update_alarm, self.delete_alarm)

    def update_alarm(self, index, alarm_data):
        self.alarms[index] = alarm_data
        self.save_alarms()
        self.display_alarms()
        self.alarm_manager.update_alarm(index, alarm_data)

    def delete_alarm(self, index):
        del self.alarms[index]
        self.save_alarms()
        self.display_alarms()
        self.alarm_manager.delete_alarm(index)

    def display_alarms(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        style = ttk.Style()
        style.configure('TButton', font=('なつめもじ', 12), background='#f0f0f0', relief='ridge')
        for i, alarm in enumerate(self.alarms):
            ttk.Button(self.scrollable_frame, text=f"{alarm['time']} {alarm['name']}", style="TButton", command=lambda: self.edit_alarm(i)).pack(pady=2)

    def load_alarms(self):
        self.alarms = self.master.data.get('Alarms', [])
        self.display_alarms()

    def save_alarms(self):
        self.master.data['Alarms'] = self.alarms
        self.master.save_data()

    def populate_alarm_tab(self):
        self.canvas = tk.Canvas(self.alarm_tab, width=140, height=200)
        self.scrollbar = ttk.Scrollbar(self.alarm_tab, orient='vertical', command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        tk.Button(self.alarm_tab, text='＋', command=self.add_alarm).place(anchor='sw', x=110, y=200, width=30, height=30)

    def populate_chara_tab(self):
        self.selected_chara = tk.StringVar(value=self.master.data.get('Character', 'erika'))
        options = ['瑛里華', '白', '陽菜', '桐葉', '伽耶', 'フィーナ', '麻衣', 'さやか', '菜月', 'リースリット', 'フィアッカ', 'シンシア', 'エステル', 'カレン']
        value = ['erika', 'siro', 'hina', 'kiriha', 'kaya', 'feena', 'mai', 'sayaka', 'natsuki', 'wreath', 'fiacca', 'cynthia', 'estel', 'karen']
        for i, chara in enumerate(options):
            col = i // 7
            row = i % 7
            rb = tk.Radiobutton(self.timer_tab, text=chara, variable=self.selected_chara, value=value[i], command=lambda chara=value[i]: self.change_chara(chara))
            rb.grid(row=row, column=col, sticky='w')

    def populate_bg_tab(self):
        self.selected_bg = tk.StringVar(value=self.master.data.get('Background', 'bg.png'))
        options = ['FA', 'けよりな']
        value = ['bg.png', 'bg2.png']
        for i, bg in enumerate(options):
            col = i % 2 
            row = 0
            rb = tk.Radiobutton(self.bg_tab, text=bg, variable=self.selected_bg, value=value[i], command=lambda bg=value[i]: self.master.change_bg(bg))
            rb.grid(row=row, column=col, sticky='w', padx=5, pady=5)


    def change_chara(self, chara):
        if hasattr(self.master, 'avatar_schedule') and self.master.avatar_schedule is not None:
            self.master.root.after_cancel(self.master.avatar_schedule)
        self.master.png_files = glob.glob(f"images/chara/{chara}/*.png")
        self.master.png_files = [str(Path(file).as_posix()) for file in self.master.png_files]
        self.master.change_chara()

        self.master.data['Character'] = chara
        self.master.save_data()

    def load_window_position(self):
        pos = self.master.data.get('SettingsWindowPosition', '+1000+500')
        self.top.geometry(pos)

    def save_window_position(self):
        pos = f'+{self.top.winfo_x()}+{self.top.winfo_y()}'
        self.master.data['SettingsWindowPosition'] = pos
        self.master.save_data()

    def on_close(self):
        self.save_window_position()
        self.master.settings_button.ignore_next_focus = True
        self.top.destroy()


class CanvasButton:
    def __init__(self, canvas, x, y, anchor, image, image_hover, command):
        self.canvas = canvas
        self.image = tk.PhotoImage(file=image)
        self.image_hover = tk.PhotoImage(file=image_hover)
        self.command = command
        self.img = canvas.create_image(x, y, anchor=anchor, image=self.image)
        self.canvas.tag_bind(self.img, '<Enter>', self.on_enter)
        self.canvas.tag_bind(self.img, '<Leave>', self.on_leave)
        self.canvas.tag_bind(self.img, '<ButtonRelease-1>', self.on_click)
        self.ignore_next_focus = False

    def on_click(self, event):
        self.command()

    def on_enter(self, event):
        if self.ignore_next_focus: # Prevent the button from being focused after closing the settings window (I don't know why this happens)
            self.ignore_next_focus = False
            return
        self.canvas.itemconfig(self.img, image=self.image_hover)

    def on_leave(self, event):
        self.canvas.itemconfig(self.img, image=self.image)

class FloatingApp:
    def __init__(self, root):
        self.root = root
        self.load_data()
        self.load_app_position()
        self.root.overrideredirect(True)  # Remove window border
        self.root.attributes('-topmost', True)

        self.root.option_add('*Menu.Font', 'なつめもじ 12')

        self.bg_image = tk.PhotoImage(file='images/' + self.data.get('Background', 'bg.png'))
        self.avatar_image = tk.PhotoImage(file="./images/eri.png")

        self.create_widgets()

        self.alarm_manager = AlarmManager(self)
        self.load_alarms()
        self.load_chara()
        self.update_weather()
        self.update_time()

        self.tray_icon = self.create_tray_icon()
        self.tray_thread = threading.Thread(target=self.tray_icon.run)
        self.tray_thread.start()

        self.root.bind('<Button-1>', self.on_mouse_down)
        self.root.bind('<B1-Motion>', self.on_drag)
        self.root.bind('<Button-3>', lambda e: self.right_click_menu.post(e.x_root, e.y_root))
        self.canvas.tag_bind(self.avatar, '<ButtonRelease-1>', self.on_mouse_up)

        self.root.wm_attributes('-transparentcolor', self.root['bg'])


    def save_data(self):
        with open('config.json', 'w') as f:
            json.dump(self.data, f)

    def load_data(self):
        try:
            with open('config.json', 'r') as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {}

    def load_alarms(self):
        alarms = self.data.get('Alarms', [])
        for i, alarm in enumerate(alarms):
            self.alarm_manager.update_alarm(i, alarm)

    def create_widgets(self):
        self.canvas = tk.Canvas(self.root, width=320, height=260)
        self.canvas.pack(fill='both', expand=True)

        self.bg = self.canvas.create_image(2, 260, image=self.bg_image, anchor='sw')
        self.avatar = self.canvas.create_image(215, 265, image=None, anchor='s')

        self.weather_frame = tk.Frame(self.canvas)
        self.weather_icon = self.canvas.create_image(80, 145, image=None, anchor='w')
        self.weather_text = self.canvas.create_text(33, 145, text='', font=('なつめもじ', 12), fill='black', anchor='w')

        self.create_weather_panel()
        self.canvas.tag_bind(self.weather_icon, '<Enter>', self.show_forecast)
        self.canvas.tag_bind(self.weather_icon, '<Leave>', lambda e: self.weather_window.withdraw())

        self.time_text = self.canvas.create_text(15, 190, text='', font=('なつめもじ', 25), fill='black', anchor='w', tags='time')
        self.date_text = self.canvas.create_text(20, 220, text='', font=('なつめもじ', 12), fill='black', anchor='w', tags='time')

        self.hide_button = CanvasButton(self.canvas, 20, 255, 'sw', 'images/close.png', 'images/close_hover.png', self.hide_app)
        self.settings_button = CanvasButton(self.canvas, 40, 255, 'sw', 'images/settings.png', 'images/settings_hover.png', self.open_settings)

        self.right_click_menu = tk.Menu(self.root, tearoff=0)
        self.right_click_menu.add_command(label='VNDB', command=lambda: webbrowser.open('https://vndb.org'))
        self.right_click_menu.add_command(label='VGMdb', command=lambda: webbrowser.open('https://vgmdb.net'))
        self.right_click_menu.add_command(label='批評空間', command=lambda: webbrowser.open('https://erogamescape.dyndns.org/'))
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(label='城プロ', command=lambda: webbrowser.open('https://pc-play.games.dmm.com/play/oshirore/'))
        self.right_click_menu.add_command(label='あいミス', command=lambda: webbrowser.open('https://pc-play.games.dmm.co.jp/play/imys_r/'))
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(label='巴哈', command=lambda: webbrowser.open('https://forum.gamer.com.tw/myBoard.php'))
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(label='HackMD', command=lambda: webbrowser.open('https://hackmd.io/'))
        self.right_click_menu.add_command(label='GitHub', command=lambda: webbrowser.open('https://github.com/'))
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(label='Exit', command=self.exit_app)


    def load_chara(self):
        with open('voice.json', 'r') as f:
            self.voice_data = json.load(f)
        chara = self.data.get('Character', 'erika')
        if hasattr(self, 'avatar_schedule') and self.avatar_schedule is not None:
            self.root.after_cancel(self.avatar_schedule)
        self.png_files = glob.glob(f"images/chara/{chara}/*.png")
        self.png_files = [str(Path(file).as_posix()) for file in self.png_files]
        self.change_chara()

    def change_chara(self):
        img = random.choice(self.png_files)
        self.avatar_image = tk.PhotoImage(file=img)
        self.canvas.itemconfig(self.avatar, image=self.avatar_image)
        # self.avatar_schedule = self.root.after(30000, self.change_chara)

        prefix = img.split('/')[-1].replace('.png', '').replace('face_', '')
        voice_files = self.voice_data.get(prefix, [])
        if voice_files:
            voice_file = 'audios/voice/' + random.choice(voice_files) + '.ogg'
            self.alarm_manager.stop_all_sounds()
            self.alarm_manager.play_sound(voice_file)

    def change_bg(self, img):
        self.bg_image = tk.PhotoImage(file='images/' + img)
        self.canvas.itemconfig(self.bg, image=self.bg_image)
        self.data['Background'] = img
        self.save_data()

    def update_weather(self):
        api_key = 'ea7f114334c04d3abcb10653240206'
        location = 'Taipei'
        days = 7 
        url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={location}&days={days}"

        response = requests.get(url)
        self.weather_data = response.json()

        if 'error' in self.weather_data:
            self.canvas.itemconfigure(self.weather_text, text='Error')
            return

        img = Image.open(requests.get('https:' + self.weather_data['current']['condition']['icon'], stream=True).raw).resize((40, 40))
        self.weather_icon_image = ImageTk.PhotoImage(img)
        self.canvas.itemconfigure(self.weather_icon, image=self.weather_icon_image)
        self.canvas.itemconfigure(self.weather_text, text=f'{self.weather_data['current']['temp_c']}°C')

        self.update_forecast()

        update_period = 300000  # 5 minutes
        self.root.after(update_period, self.update_weather)

    def update_time(self):
        # Update the label with the current date and time
        current_time = datetime.now().strftime('%H:%M:%S')
        self.canvas.itemconfigure(self.time_text, text=current_time)

        days_in_jp = ['月', '火', '水', '木', '金', '土', '日']
        day_of_week = days_in_jp[datetime.now().weekday()]
        current_date = datetime.now().strftime(f'%m月%d日 ({day_of_week})')
        self.canvas.itemconfigure(self.date_text, text=current_date)

        self.root.after(1000, self.update_time)  # Update every second

    def on_mouse_down(self, event):
        try:
            self.alarm_manager.stop_all_sounds()
        except Exception as e:
            print(e)

        self.mdown_time = datetime.now()

        if event.widget == self.canvas:
            item = self.canvas.find_withtag('current')
            if 'canvas_btn' in self.canvas.gettags(item):
                return
            # Reletive position of the mouse pointer to the window
            self.x = self.root.winfo_pointerx() - self.root.winfo_rootx()
            self.y = self.root.winfo_pointery() - self.root.winfo_rooty()

    def on_drag(self, event):
        if event.widget == self.canvas:
            item = self.canvas.find_withtag('current')
            if 'canvas_btn' in self.canvas.gettags(item):
                return
            x = self.root.winfo_pointerx() - self.x
            y = self.root.winfo_pointery() - self.y

            monitors = get_monitors()
            if len(monitors) > 1 and (x > monitors[0].width or y + 260 > monitors[0].height):
                target_y = monitors[1].height - 40 + monitors[1].y
            else:
                target_y = self.root.winfo_screenheight() - 40

            snap_threshold = 20
            if abs(y + 260 - target_y) < snap_threshold:
                y = target_y - 260

            self.root.geometry(f'+{x}+{y}')

    def on_mouse_up(self, event):
        # click event
        if (datetime.now() - self.mdown_time).total_seconds() < 0.2:
            self.change_chara()

    def hide_app(self, event=None):
        self.root.withdraw()

    def exit_app(self):
        self.tray_icon.stop()
        self.alarm_manager.shutdown()
        self.save_app_position()
        self.root.after(0, self.root.quit)

    def create_tray_icon(self):
        icon_image = Image.open("images/icon.ico").convert('RGBA')
        return pystray.Icon(
            name='WaifuClock',
            icon=icon_image,
            title='Waifu Clock',
            menu=pystray.Menu(
                pystray.MenuItem('Show', self.root.deiconify, default=True),
                pystray.MenuItem('Exit', self.exit_app)
        ))

    def open_settings(self):
        self.settings_panel = SettingsWindow(self, self.alarm_manager)
        self.settings_button.on_leave(None)

    def load_app_position(self):
        pos = self.data.get('AppPosition', '+1000+500')
        self.root.geometry(pos)

    def save_app_position(self):
        self.data['AppPosition'] = f'+{self.root.winfo_x()}+{self.root.winfo_y()}'
        self.save_data()
    
    def create_weather_panel(self):
        self.weather_window = tk.Toplevel(self.root)
        self.weather_window.overrideredirect(True)
        # self.weather_window.geometry('400x300')
        self.weather_window.attributes('-topmost', True)
        self.weather_window.withdraw()

    def show_forecast(self, event=None):
        self.weather_window.deiconify()

        width = self.weather_window.winfo_width()
        height = self.weather_window.winfo_height()

        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        monitors = get_monitors()
        if x > screen_width and len(monitors) > 1:
            screen_width = monitors[1].width + monitors[1].x
            screen_height = monitors[1].height + monitors[1].y

        if x + width > screen_width:
            x = x - width
        if y + height > screen_height:
            y = y - height

        self.weather_window.geometry(f'+{x}+{y}')


    def update_forecast(self):
        for widget in self.weather_window.winfo_children():
            widget.destroy()

        current = self.weather_data['current']
        forecast = self.weather_data['forecast']['forecastday']

        current_hour = datetime.now().hour

        current_frame = tk.Frame(self.weather_window, pady=10)
        current_frame.pack(fill='x', expand=True)
        
        icon_size = 50
        font = ('なつめもじ', 14)
        info_frame = tk.Frame(current_frame)
        info_frame.pack(side='left', padx=(70, 0), pady=(30, 0))
        tk.Label(info_frame, text=f"{current['temp_c']}°C", font=font).pack()
        tk.Label(info_frame, text=f"{current['condition']['text']}", font=font).pack()
        tk.Label(info_frame, text=f"Chance of Rain: " + str(forecast[0]['hour'][current_hour]['chance_of_rain']) + "%", font=font).pack()

        img = Image.open(requests.get('https:' + current['condition']['icon'], stream=True).raw).resize((70, 70))
        icon = ImageTk.PhotoImage(img)
        icon_label = tk.Label(current_frame, image=icon)
        icon_label.image = icon
        icon_label.pack(side='left', padx=(30, 0), pady=(15, 0))

        tk.Label(self.weather_window, text='').pack(pady=10)

        # Hourly Forecast
        hourly_forecast = forecast[0]['hour']
        relevant_hours = [hour for hour in hourly_forecast if int(hour['time'].split(' ')[1].split(':')[0]) >= current_hour][:7]
        hourly_frame = tk.Frame(self.weather_window, pady=10, padx=10)
        hourly_frame.pack(fill='x', expand=True)
        for hour in relevant_hours:
            frame = tk.Frame(hourly_frame)
            frame.pack(side='left')
            tk.Label(frame, text=hour['time'].split(' ')[1]).pack(pady=10)
            temp = round(hour['temp_c'])
            tk.Label(frame, text=f"{temp}°C").pack()
            icon_path = f"https:{hour['condition']['icon']}"
            img = Image.open(requests.get(icon_path, stream=True).raw).resize((icon_size, icon_size))
            photo = ImageTk.PhotoImage(img)
            icon_label = tk.Label(frame, image=photo)
            icon_label.image = photo
            icon_label.pack()
            tk.Label(frame, text=f"{hour['chance_of_rain']}%").pack()

        # split hourly and daily forecast
        tk.Label(self.weather_window, text='').pack(pady=10)

        # Daily Forecast for the next 7 days
        daily_forecast = forecast[:7]  # Adjust according to how many days are actually available
        daily_frame = tk.Frame(self.weather_window, pady=10, padx=10)
        daily_frame.pack(fill='x', expand=True)
        for day in daily_forecast:
            frame = tk.Frame(daily_frame)
            frame.pack(side='left')
            day_of_week = datetime.strptime(day['date'], '%Y-%m-%d').strftime('%a')
            tk.Label(frame, text=day_of_week).pack(pady=10)
            temp = round(day['day']['maxtemp_c'])
            tk.Label(frame, text=f"{temp}°C").pack()
            icon_path = f"https:{day['day']['condition']['icon']}"
            img = Image.open(requests.get(icon_path, stream=True).raw).resize((icon_size, icon_size))
            photo = ImageTk.PhotoImage(img)
            icon_label = tk.Label(frame, image=photo)
            icon_label.image = photo
            icon_label.pack()





if __name__ == '__main__':
    root = tk.Tk()
    app = FloatingApp(root)
    root.protocol("WM_DELETE_WINDOW", app.hide_app)  # Ensure the app hides when the close button is pressed
    root.mainloop()

