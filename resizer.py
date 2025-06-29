import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import io

class ImageCropper:
    def __init__(self, root, image_path):
        self.root = root
        self.root.title("Image Cropper")
        self.root.geometry("800x600")

        self.image = Image.open(image_path)
        self.tk_image = ImageTk.PhotoImage(self.image)

        # Scrollable Canvas Setup
        self.outer_frame = tk.Frame(root)
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

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.crop_button = tk.Button(root, text="Crop and Continue", command=self.crop_image)
        self.crop_button.pack(pady=5)

        self.start_x = self.start_y = self.rect = None
        self.crop_coords = None

    def on_button_press(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline='red')

    def on_drag(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        self.crop_coords = (int(min(self.start_x, end_x)), int(min(self.start_y, end_y)),
                            int(max(self.start_x, end_x)), int(max(self.start_y, end_y)))

    def crop_image(self):
        if not self.crop_coords:
            messagebox.showerror("Error", "No crop area selected!")
            return
        self.cropped_img = self.image.crop(self.crop_coords)
        self.show_input_window()

    def show_input_window(self):
        win = tk.Toplevel(self.root)
        win.title("Resize and Compress Options")
        win.geometry("300x250")

        tk.Label(win, text="Target File Size (KB):").pack()
        size_entry = tk.Entry(win)
        size_entry.insert(0, "15")
        size_entry.pack()

        tk.Label(win, text="Width (cm):").pack()
        width_entry = tk.Entry(win)
        width_entry.insert(0, "6")
        width_entry.pack()

        tk.Label(win, text="Height (cm):").pack()
        height_entry = tk.Entry(win)
        height_entry.insert(0, "2")
        height_entry.pack()

        tk.Label(win, text="DPI:").pack()
        dpi_entry = tk.Entry(win)
        dpi_entry.insert(0, "300")
        dpi_entry.pack()

        def process():
            try:
                target_kb = int(size_entry.get())
                width_cm = float(width_entry.get())
                height_cm = float(height_entry.get())
                dpi = int(dpi_entry.get())

                width_px = int((dpi / 2.54) * width_cm)
                height_px = int((dpi / 2.54) * height_cm)

                # Resize with stretching
                resized = self.cropped_img.resize((width_px, height_px), Image.Resampling.LANCZOS)

                # Compress to target KB
                quality = 95
                while quality > 10:
                    buffer = io.BytesIO()
                    resized.save(buffer, format="JPEG", quality=quality, dpi=(dpi, dpi))
                    kb_size = len(buffer.getvalue()) / 1024
                    if kb_size <= target_kb:
                        with open("final_output.jpg", "wb") as f:
                            f.write(buffer.getvalue())
                        messagebox.showinfo("Success", f"Saved as final_output.jpg\nSize: {int(kb_size)} KB")
                        return
                    quality -= 5

                messagebox.showwarning("Warning", "Could not compress to target size.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(win, text="Save Final Image", command=process).pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCropper(root, "input.jpg")
    root.mainloop()
