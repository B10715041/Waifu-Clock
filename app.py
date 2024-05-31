from PIL import Image, ImageTk
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from tkinter import ttk, messagebox, filedialog
import glob
import json
import pystray
import random
import re
import requests
import threading
import tkinter as tk

import contextlib
with contextlib.redirect_stdout(None):
    import pygame



class AlarmManager:
    def __init__(self, app):
        pygame.mixer.init()
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.jobs = {}
        self.channels = {i: None for i in range(pygame.mixer.get_num_channels())}  # 8 channels by default?
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
        sound = pygame.mixer.Sound(sound_file)
        available_channel = self.find_available_channel()
        if available_channel:
            available_channel.play(sound)
            self.app.root.deiconify()
        else:
            print('No available channels')

    def find_available_channel(self):
        for i in range(pygame.mixer.get_num_channels()):
            if not pygame.mixer.Channel(i).get_busy():
                return pygame.mixer.Channel(i)
        return None

    def stop_all_sounds(self):
        pygame.mixer.stop()

    def shutdown(self):
        pygame.mixer.quit()
        self.scheduler.shutdown()


class EditAlarmDialog:
    def __init__(self, master, alarm_index, alarm_data, update_callback, delete_callback):
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
        try:
            with open('config.json', 'r') as f:
                data = json.load(f)
                pos = data.get('AlarmDialogPosition', '+1000+500')
                self.top.geometry(pos)
        except (FileNotFoundError, json.JSONDecodeError):
            self.top.geometry('+1000+500')

    def save_alarm_dialog_position(self):
        pos = f'+{self.top.winfo_x()}+{self.top.winfo_y()}'
        try:
            with open('config.json', 'r+') as f:
                data = json.load(f)
                data['AlarmDialogPosition'] =  pos
                f.seek(0)
                f.truncate()
                json.dump(data, f)
        except (FileNotFoundError, json.JSONDecodeError):
            with open('config.json', 'w') as f:
                json.dump({'AlarmDialogPosition': pos}, f)

    def on_close(self):
        self.save_alarm_dialog_position()
        self.top.destroy()


class SettingsWindow:
    def __init__(self, master, alarm_manager):
        self.top = tk.Toplevel(master.root)
        self.load_window_position()
        self.top.protocol('WM_DELETE_WINDOW', self.on_close)
        self.top.title('Settings')
        self.top.iconbitmap('images/icon.ico')
        self.top.transient(master.root)
        self.top.grab_set() # Direct all events to this window
        self.top.lift()
        self.top.focus_set()
        self.master = master

        self.notebook = ttk.Notebook(self.top)
        self.notebook.pack(fill='both', expand=True)

        self.alarm_tab = ttk.Frame(self.notebook)
        self.timer_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.alarm_tab, text='アラーム')
        self.notebook.add(self.timer_tab, text='キャラ選択')

        self.populate_alarm_tab()
        self.populate_chara_tab()
        self.load_alarms()
        self.alarm_manager = alarm_manager

        self.top.wait_window()  # Wait for the window to be closed

    def add_alarm(self):
        new_alarm = {'time': '07:00', 'music': 'audios/default.mp3', 'name': ''}
        self.alarms.append(new_alarm)
        self.display_alarms()

    def edit_alarm(self, index):
        data = self.alarms[index]
        EditAlarmDialog(self.top, index, data, self.update_alarm, self.delete_alarm)

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
        try:
            with open('config.json', 'r') as f:
                self.alarms = json.load(f).get('Alarms', [])
        except:
            self.alarms = []
        self.display_alarms()

    def save_alarms(self):
        try:
            with open('config.json', 'r+') as f:
                data = json.load(f)
                data['Alarms'] = self.alarms
                f.seek(0)
                f.truncate()
                json.dump(data, f)
        except (FileNotFoundError, json.JSONDecodeError):
            with open('config.json', 'w') as f:
                json.dump({'Alarms': self.alarms}, f)

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
        with open('config.json', 'r') as f:
            data = json.load(f)
            self.selected_chara = tk.StringVar(value=data.get('Character', 'erika'))
        options = ['瑛里華', '白', '陽菜', '桐葉', '伽耶', 'フィーナ', '麻衣', 'さやか', '菜月', 'リースリット', 'フィアッカ', 'シンシア', 'エステル', 'カレン']
        value = ['erika', 'siro', 'hina', 'kiriha', 'kaya', 'feena', 'mai', 'sayaka', 'natsuki', 'wreath', 'fiacca', 'cynthia', 'estel', 'karen']
        for i, chara in enumerate(options):
            col = i // 7
            row = i % 7
            rb = tk.Radiobutton(self.timer_tab, text=chara, variable=self.selected_chara, value=value[i], command=lambda chara=value[i]: self.change_chara(chara))
            rb.grid(row=row, column=col, sticky='w')

    def change_chara(self, chara):
        if self.master.avatar_schedule is not None:
            self.master.root.after_cancel(self.master.avatar_schedule)
        self.master.png_files = glob.glob(f"images/chara/{chara}/*.png")
        self.master.change_chara()
        try:
            with open('config.json', 'r+') as f:
                data = json.load(f)
                data['Character'] = chara
                f.seek(0)
                f.truncate()
                json.dump(data, f)
        except (FileNotFoundError, json.JSONDecodeError):
            with open('config.json', 'w') as f:
                json.dump({'Character': chara}, f)

    def load_window_position(self):
        try:
            with open('config.json', 'r') as f:
                data = json.load(f)
                pos = data.get('SettingsWindowPosition', '+1000+500')
                self.top.geometry(pos)
        except (FileNotFoundError, json.JSONDecodeError):
            self.top.geometry('+1000+500')

    def save_window_position(self):
        pos = f'+{self.top.winfo_x()}+{self.top.winfo_y()}'
        try:
            with open('config.json', 'r+') as f:
                data = json.load(f)
                data['SettingsWindowPosition'] =  pos
                f.seek(0)
                f.truncate()
                json.dump(data, f)
        except (FileNotFoundError, json.JSONDecodeError):
            with open('config.json', 'w') as f:
                json.dump({'SettingsWindowPosition': pos}, f)

    def on_close(self):
        self.save_window_position()
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

    def on_click(self, event):
        self.command()

    def on_enter(self, event):
        self.canvas.itemconfig(self.img, image=self.image_hover)

    def on_leave(self, event):
        self.canvas.itemconfig(self.img, image=self.image)

class FloatingApp:
    def __init__(self, root):
        self.root = root
        self.load_app_position()
        self.root.overrideredirect(True)  # Remove window border
        self.root.attributes('-topmost', True)

        self.bg_image = tk.PhotoImage(file="images/bg.png")
        self.avatar_image = tk.PhotoImage(file="./images/eri.png")

        self.create_widgets()
        self.load_chara()
        self.update_weather()
        self.update_time()

        self.tray_icon = self.create_tray_icon()
        self.tray_thread = threading.Thread(target=self.tray_icon.run)
        self.tray_thread.start()

        # Make the window draggable
        self.root.bind('<Button-1>', self.start_move)
        self.root.bind('<B1-Motion>', self.do_move)

        # Make the background transparent
        self.root.wm_attributes('-transparentcolor', self.root['bg'])

        self.alarm_manager = AlarmManager(self)
        self.load_alarms()

    def load_alarms(self):
        try:
            with open('config.json', 'r') as f:
                data = json.load(f)
                alarms = data.get('Alarms', [])
                for i, alarm in enumerate(alarms):
                    self.alarm_manager.update_alarm(i, alarm)
        except:
            pass

    def create_widgets(self):
        self.canvas = tk.Canvas(self.root, width=320, height=260)
        self.canvas.pack(fill='both', expand=True)

        self.canvas.create_image(2, 260, image=self.bg_image, anchor='sw')
        self.avatar = self.canvas.create_image(215, 265, image=self.avatar_image, anchor='s')

        self.weather_frame = tk.Frame(self.canvas)
        self.weather_icon_image = tk.PhotoImage(file='images/weather.png')
        self.weather_icon = self.canvas.create_image(20, 145, image=self.weather_icon_image, anchor='w')
        self.weather_text = self.canvas.create_text(70, 145, text='', font=('なつめもじ', 12), fill='black', anchor='w')

        self.time_text = self.canvas.create_text(15, 190, text='', font=('なつめもじ', 25), fill='black', anchor='w', tags='time')
        self.date_text = self.canvas.create_text(20, 220, text='', font=('なつめもじ', 12), fill='black', anchor='w', tags='time')

        self.hide_button = CanvasButton(self.canvas, 20, 255, 'sw', 'images/close.png', 'images/close_hover.png', self.hide_app)
        self.settings_button = CanvasButton(self.canvas, 40, 255, 'sw', 'images/settings.png', 'images/settings_hover.png', self.open_settings)

    def load_chara(self):
        with open('config.json', 'r') as f:
            data = json.load(f)
            chara = data.get('Character', 'erika')
        if hasattr(self, 'avatar_schedule') and self.avatar_schedule is not None:
            self.root.after_cancel(self.avatar_schedule)
        self.png_files = glob.glob(f"images/chara/{chara}/*.png")
        self.change_chara()

    def change_chara(self):
        img = random.choice(self.png_files)
        self.avatar_image = tk.PhotoImage(file=img)
        self.canvas.itemconfig(self.avatar, image=self.avatar_image)
        self.avatar_schedule = self.root.after(30000, self.change_chara)

    def get_weather(self, city, api_key):
        url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
        data = requests.get(url).json()
        if data.get('cod') != 200:
            return f"Error: {data.get('message')}", None
        temperture = data['main']['temp']
        icon_url = f"http://openweathermap.org/img/wn/{data['weather'][0]['icon']}.png"
        return temperture, icon_url

    def update_weather(self):
        city = 'Taipei'
        api = 'defdfdbe2f16581c1462ab4776db03fb'
        temp, icon_url = self.get_weather(city, api)

        if temp:
            img = Image.open(requests.get(icon_url, stream=True).raw).resize((50, 50))
            self.weather_icon_image = ImageTk.PhotoImage(img)
            self.canvas.itemconfigure(self.weather_icon, image=self.weather_icon_image)
            self.canvas.itemconfigure(self.weather_text, text=f'{temp}°C')

        self.root.after(300000, self.update_weather)  # Update every minute

    def update_time(self):
        # Update the label with the current date and time
        current_time = datetime.now().strftime('%H:%M:%S')
        self.canvas.itemconfigure(self.time_text, text=current_time)

        days_in_jp = ['月', '火', '水', '木', '金', '土', '日']
        day_of_week = days_in_jp[datetime.now().weekday()]
        current_date = datetime.now().strftime(f'%m月%d日 ({day_of_week})')
        self.canvas.itemconfigure(self.date_text, text=current_date)

        self.root.after(1000, self.update_time)  # Update every second

    def start_move(self, event):
        self.alarm_manager.stop_all_sounds()

        if event.widget == self.canvas:
            item = self.canvas.find_withtag('current')
            if 'canvas_btn' in self.canvas.gettags(item):
                return
            # Reletive position of the mouse pointer to the window
            self.x = self.root.winfo_pointerx() - self.root.winfo_rootx()
            self.y = self.root.winfo_pointery() - self.root.winfo_rooty()


    def do_move(self, event):
        if event.widget == self.canvas:
            item = self.canvas.find_withtag('current')
            if 'canvas_btn' in self.canvas.gettags(item):
                return
            x = self.root.winfo_pointerx() - self.x
            y = self.root.winfo_pointery() - self.y

            target_y = self.root.winfo_screenheight() - 40
            snap_threshold = 20
            if abs(y + 260 - target_y) < snap_threshold:
                y = target_y - 260

            self.root.geometry(f'+{x}+{y}')

    def hide_app(self, event=None):
        self.root.withdraw()

    def exit_app(self, icon=None, item=None):
        if icon:
            icon.stop()
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

    def load_app_position(self):
        try:
            with open('config.json', 'r') as f:
                data = json.load(f)
                pos = data.get('AppPosition', '+1000+500')
                self.root.geometry(pos)
        except (FileNotFoundError, json.JSONDecodeError):
            self.root.geometry('+1000+500')

    def save_app_position(self):
        pos = f'+{self.root.winfo_x()}+{self.root.winfo_y()}'
        try:
            with open('config.json', 'r+') as f:
                data = json.load(f)
                data['AppPosition'] =  pos
                f.seek(0)
                f.truncate()
                json.dump(data, f)
        except (FileNotFoundError, json.JSONDecodeError):
            with open('config.json', 'w') as f:
                json.dump({'AppPosition': pos}, f)



if __name__ == '__main__':
    root = tk.Tk()
    app = FloatingApp(root)
    root.protocol("WM_DELETE_WINDOW", app.hide_app)  # Ensure the app hides when the close button is pressed
    root.mainloop()

