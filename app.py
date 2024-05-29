import tkinter as tk
import tkinter.font as tkFont
from datetime import datetime
import threading
import pystray
from PIL import Image, ImageDraw, ImageTk

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
        self.settings_button = CanvasButton(self.canvas, 40, 190, 'sw', 'img/settings.png', 'img/settings_hover.png', 0)


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


if __name__ == '__main__':
    root = tk.Tk()
    app = FloatingApp(root)
    root.protocol("WM_DELETE_WINDOW", app.hide_app)  # Ensure the app hides when the close button is pressed
    root.mainloop()

