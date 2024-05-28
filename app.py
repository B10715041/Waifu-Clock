import tkinter as tk
from datetime import datetime
import threading
import pystray
from PIL import Image, ImageDraw, ImageTk

class FloatingApp:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)  # Remove window border
        self.root.attributes('-topmost', True)  # Keep the window on top

        self.bg_image = Image.open("img/f2.png")  # Load the background image
        self.bg_photo = ImageTk.PhotoImage(self.bg_image)  # Convert to PhotoImage for Tkinter

        # Adjust the window size to the image size
        self.root.geometry(f'{self.bg_image.width}x{self.bg_image.height}')

        self.create_widgets()
        self.update_time()

        self.tray_icon = self.create_tray_icon()
        self.tray_thread = threading.Thread(target=self.tray_icon.run)
        self.tray_thread.start()

        # Make the window draggable
        self.root.bind('<Button-1>', self.start_move)
        self.root.bind('<B1-Motion>', self.do_move)
        
        # Make the background transparent
        # self.root.wm_attributes('-transparentcolor', 'white')  # Change 'white' to your transparent color if needed
        self.root.wm_attributes('-transparentcolor', self.root['bg']) 

    def create_widgets(self):
        # Create a label with the background image
        self.bg_label = tk.Label(self.root, image=self.bg_photo, bg=self.root['bg'])  # Set 'white' to match the transparent color
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Create a label to display the current time
        self.label = tk.Label(self.root, text='', font=('Helvetica', 12), bg='white', fg='black')
        self.label.pack()

        # Create a button to hide the application
        self.hide_button = tk.Button(self.root, text='Hide', command=self.hide_app, bg='white', fg='black')
        self.hide_button.pack()

    def update_time(self):
        # Update the label with the current date and time
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.label.config(text=now)
        self.root.after(1000, self.update_time)  # Update every second

    def start_move(self, event):
        # Remember the initial position of the window
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        # Move the window to the new position
        x = self.root.winfo_pointerx() - self.x
        y = self.root.winfo_pointery() - self.y
        self.root.geometry(f'+{x}+{y}')

    def hide_app(self):
        # Hide the application window
        self.root.withdraw()

    def exit_app(self, icon=None, item=None):
        # Stop the tray icon and quit the application
        if icon:
            icon.stop()
        self.root.after(0, self.root.quit)

    def create_tray_icon(self):
        # Load the icon for the tray
        icon_image = Image.open("img/icon.ico").convert('RGBA')

        # Convert the icon to the appropriate format for pystray
        icon = pystray.Icon('FloatingApp', icon_image, 'Floating App', self.create_menu())
        return icon

    def create_menu(self):
        # Create the context menu for the tray icon
        return pystray.Menu(
            pystray.MenuItem('Show', self.show_app),
            pystray.MenuItem('Exit', self.exit_app)
        )

    def show_app(self, icon=None, item=None):
        # Show the application window
        self.root.deiconify()

if __name__ == '__main__':
    root = tk.Tk()
    app = FloatingApp(root)
    root.protocol("WM_DELETE_WINDOW", app.hide_app)  # Ensure the app hides when the close button is pressed
    root.mainloop()

