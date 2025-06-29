import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import io

class ImageCropper:
    def __init__(self, root, image_path):
        self.root = root
        self.root.title("Image Cropper")
        self.image_path = image_path
        self.get_user_inputs()

    def get_user_inputs(self):
        self.input_window = tk.Toplevel(self.root)
        self.input_window.title("Enter Image Output Settings")
        self.input_window.geometry("300x250")

        tk.Label(self.input_window, text="Target File Size (KB):").pack()
        self.size_entry = tk.Entry(self.input_window)
        self.size_entry.insert(0, "15")
        self.size_entry.pack()

        tk.Label(self.input_window, text="Width (cm):").pack()
        self.width_entry = tk.Entry(self.input_window)
        self.width_entry.insert(0, "6")
        self.width_entry.pack()

        tk.Label(self.input_window, text="Height (cm):").pack()
        self.height_entry = tk.Entry(self.input_window)
        self.height_entry.insert(0, "2")
        self.height_entry.pack()

        tk.Label(self.input_window, text="DPI:").pack()
        self.dpi_entry = tk.Entry(self.input_window)
        self.dpi_entry.insert(0, "300")
        self.dpi_entry.pack()

        tk.Button(self.input_window, text="Next", command=self.setup_canvas).pack(pady=10)

    def setup_canvas(self):
        # Read values
        try:
            self.target_kb = int(self.size_entry.get())
            self.width_cm = float(self.width_entry.get())
            self.height_cm = float(self.height_entry.get())
            self.dpi = int(self.dpi_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid input values.")
            return

        self.aspect_ratio = self.width_cm / self.height_cm
        self.input_window.destroy()

        # Load image
        self.image = Image.open(self.image_path)
        self.tk_image = ImageTk.PhotoImage(self.image)

        # Scrollable canvas
        self.outer_frame = tk.Frame(self.root)
        self.outer_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.outer_frame, bg='gray')
        self.h_scroll = tk.Scrollbar(self.outer_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.v_scroll = tk.Scrollbar(self.outer_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.h_scroll.grid(row=1, column=0, sticky="ew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.outer_frame.grid_rowconfigure(0, weight=1)
        self.outer_frame.grid_columnconfigure(0, weight=1)

        self.canvas_image = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.canvas.config(scrollregion=(0, 0, self.image.width, self.image.height))

        # Mouse bindings
        self.start_x = self.start_y = self.rect = None
        self.crop_coords = None
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.crop_button = tk.Button(self.root, text="Crop and Save", command=self.process_crop)
        self.crop_button.pack(pady=5)

    def on_button_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red')

    def on_drag(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)

        # Constrain to aspect ratio
        dx = cur_x - self.start_x
        dy = cur_y - self.start_y

        if abs(dx) > abs(dy):
            dy = dx / self.aspect_ratio
        else:
            dx = dy * self.aspect_ratio

        new_x = self.start_x + dx
        new_y = self.start_y + dy

        self.canvas.coords(self.rect, self.start_x, self.start_y, new_x, new_y)

    def on_release(self, event):
        coords = self.canvas.coords(self.rect)
        self.crop_coords = tuple(map(int, coords))

    def process_crop(self):
        if not self.crop_coords:
            messagebox.showerror("Error", "No crop area selected!")
            return

        cropped = self.image.crop(self.crop_coords)

        # Resize
        px_width = int((self.dpi / 2.54) * self.width_cm)
        px_height = int((self.dpi / 2.54) * self.height_cm)
        resized = cropped.resize((px_width, px_height), Image.Resampling.LANCZOS)

        # Compress to target size
        quality = 95
        while quality > 10:
            buffer = io.BytesIO()
            resized.save(buffer, format="JPEG", quality=quality, dpi=(self.dpi, self.dpi))
            kb_size = len(buffer.getvalue()) / 1024
            if kb_size <= self.target_kb:
                with open("images/final_output.jpg", "wb") as f:
                    f.write(buffer.getvalue())
                messagebox.showinfo("Success", f"Saved as images/final_output.jpg\nSize: {int(kb_size)} KB")
                return
            quality -= 5

        messagebox.showwarning("Warning", "Could not compress to target size.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCropper(root, "images/input.jpg")
    root.mainloop()
