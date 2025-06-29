import tkinter as tk
from tkinter import Scrollbar
from PIL import Image, ImageTk

class ImageCropper:
    def __init__(self, root, image_path):
        self.root = root
        self.root.title("Image Cropper")
        self.root.geometry("800x600")

        self.image = Image.open(image_path)
        self.tk_image = ImageTk.PhotoImage(self.image)

        self.frame = tk.Frame(root)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbars
        self.h_scroll = Scrollbar(self.frame, orient=tk.HORIZONTAL)
        self.v_scroll = Scrollbar(self.frame, orient=tk.VERTICAL)
        self.canvas = tk.Canvas(self.frame,
                                xscrollcommand=self.h_scroll.set,
                                yscrollcommand=self.v_scroll.set,
                                bg='gray')
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.canvas_image = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

        # Cropping logic
        self.start_x = self.start_y = self.rect = None
        self.crop_coords = None

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.crop_button = tk.Button(root, text="Crop and Save", command=self.crop_image)
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
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        self.crop_coords = (int(min(self.start_x, end_x)), int(min(self.start_y, end_y)),
                            int(max(self.start_x, end_x)), int(max(self.start_y, end_y)))

    def crop_image(self):
        if self.crop_coords:
            cropped = self.image.crop(self.crop_coords)
            cropped.save("cropped.jpg")
            print("Cropped image saved as cropped.jpg")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCropper(root, "input.jpg")
    root.mainloop()
