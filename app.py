from PIL import Image
from datetime import datetime
from tkinter import ttk
import json
import pystray
import threading
import tkinter as tk


class EditAlarmDialog:
    def __init__(self, master, alarm_data=None):
        self.top = tk.Toplevel(master)
        self.top.title('Edit Alarm')
        self.top.grab_set()

        self.alarm_data = alarm_data if alarm_data else { 'time': '', 'music': '', 'comment': '' }

        ttk.Label(self.top, text='Time:').pack()
        self.time_entry = ttk.Entry(self.top)
        self.time_entry.pack()
        self.time_entry.insert(0, self.alarm_data.get('time', ''))

        ttk.Label(self.top, text='Music:').pack()
        self.music_entry = ttk.Entry(self.top)
        self.music_entry.pack()
        self.music_entry.insert(0, self.alarm_data.get('music', ''))

        self.comment_label = ttk.Label(self.top, text='Comment:')
        self.comment_label.pack()
        self.comment_entry = tk.Text(self.top, height=5, width=30)
        self.comment_entry.pack()
        self.comment_entry.insert('1.0', self.alarm_data.get('comment', ''))
        self.comment_entry.config(wrap='word')

        ttk.Button(self.top, text='Save', command=self.save).pack()

    def save(self):
        self.alarm_data['time'] = self.time_entry.get()
        self.alarm_data['music'] = self.music_entry.get()
        self.alarm_data['comment'] = self.comment_entry.get('1.0', 'end-1c')
        self.top.destroy()


class SettingsWindow:
    def __init__(self, master):
        self.top = tk.Toplevel(master)
        self.top.title('Settings')
        self.top.iconbitmap('img/icon.ico')
        self.top.transient(master)
        self.top.grab_set() # Direct all events to this window

        self.notebook = ttk.Notebook(self.top)
        self.notebook.pack(fill='both', expand=True)

        self.alarm_tab = ttk.Frame(self.notebook)
        self.timer_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.alarm_tab, text='Alarm')
        self.notebook.add(self.timer_tab, text='Timer')

        self.canvas = tk.Canvas(self.alarm_tab)
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

        ttk.Button(self.alarm_tab, text='Add Alarm', command=self.add_alarm).pack()
        self.alarms = []

        self.populate_alarm_tab()
        self.populate_timer_tab()

        self.top.wait_window()  # Wait for the window to be closed

    def add_alarm(self):
        new_alarm = {'time': '07:00', 'music': 'audios/default.mp3', 'comment': ''}
        self.alarms.append(new_alarm)
        ttk.Button(self.scrollable_frame, text=f"Alarm at {new_alarm['time']}", command=lambda: self.edit_alarm(new_alarm)).pack()

    def edit_alarm(self, alarm_data):
        EditAlarmDialog(self.top, alarm_data=alarm_data)

    def populate_alarm_tab(self):
        self.alarm_label = ttk.Label(self.alarm_tab, text='Alarm Settings')
        self.alarm_label.pack(pady=10, padx=10)

    def populate_timer_tab(self):
        self.timer_label = ttk.Label(self.timer_tab, text='Timer Settings')
        self.timer_label.pack(pady=10, padx=10)



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
        self.root.overrideredirect(True)  # Remove window border
        self.root.attributes('-topmost', True)

        self.bg_image = tk.PhotoImage(file="img/bg.png")
        self.avatar_image = tk.PhotoImage(file="img/erika.png")

        self.create_widgets()
        self.update_time()

        self.tray_icon = self.create_tray_icon()
        self.tray_thread = threading.Thread(target=self.tray_icon.run)
        self.tray_thread.start()

        # Make the window draggable
        self.root.bind('<Button-1>', self.start_move)
        self.root.bind('<B1-Motion>', self.do_move)

        # Make the background transparent
        self.root.wm_attributes('-transparentcolor', self.root['bg'])

    def create_widgets(self):
        self.canvas = tk.Canvas(self.root, width=320, height=195)
        self.canvas.pack(fill='both', expand=True)

        self.canvas.create_image(0, 195, image=self.bg_image, anchor='sw')
        self.avatar = self.canvas.create_image(320, 200, image=self.avatar_image, anchor='se')

        # current time
        self.time = self.canvas.create_text(20, 115, text='', font=('なつめもじ', 20), fill='black', anchor='w', tags='time')

        self.hide_button = CanvasButton(self.canvas, 20, 190, 'sw', 'img/close.png', 'img/close_hover.png', self.hide_app)
        self.settings_button = CanvasButton(self.canvas, 40, 190, 'sw', 'img/settings.png', 'img/settings_hover.png', self.open_settings)

    def update_time(self):
        # Update the label with the current date and time
        current_time = datetime.now().strftime('  %H:%M:%S')

        days_in_jp = ['月', '火', '水', '木', '金', '土', '日']
        day_of_week = days_in_jp[datetime.now().weekday()]
        current_date = datetime.now().strftime(f'%m月%d日\n      ({day_of_week})')

        self.canvas.itemconfigure(self.time, text=f"{current_time}\n{current_date}")
        self.root.after(1000, self.update_time)  # Update every second

    def start_move(self, event):
        if event.widget == self.canvas:
            item = self.canvas.find_withtag('current')
            if 'canvas_btn' in self.canvas.gettags(item):
                return
            # Calculate absolute position of the cursor on screen
            self.x = self.root.winfo_pointerx() - self.root.winfo_rootx()
            self.y = self.root.winfo_pointery() - self.root.winfo_rooty()

    def do_move(self, event):
        if event.widget == self.canvas:
            item = self.canvas.find_withtag('current')
            if 'canvas_btn' in self.canvas.gettags(item):
                return
            x = self.root.winfo_pointerx() - self.x
            y = self.root.winfo_pointery() - self.y
            self.root.geometry(f'+{x}+{y}')

    def hide_app(self, event=None):
        self.root.withdraw()

    def exit_app(self, icon=None, item=None):
        # Stop the tray icon and quit the application
        if icon:
            icon.stop()
        self.root.after(0, self.root.quit)

    def create_tray_icon(self):
        icon_image = Image.open("img/icon.ico").convert('RGBA')
        return pystray.Icon(
            name='WaifuClock',
            icon=icon_image,
            title='Waifu Clock',
            menu=pystray.Menu(
                pystray.MenuItem('Show', self.root.deiconify, default=True),
                pystray.MenuItem('Exit', self.exit_app)
        ))

    def open_settings(self):
        self.settings_panel = SettingsWindow(self.root)


if __name__ == '__main__':
    root = tk.Tk()
    app = FloatingApp(root)
    root.protocol("WM_DELETE_WINDOW", app.hide_app)  # Ensure the app hides when the close button is pressed
    root.mainloop()

