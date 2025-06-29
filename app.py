from flask import Flask, render_template_string, request, send_file, redirect, url_for, flash
from PIL import Image
import io
import os

app = Flask(__name__)
app.secret_key = 'secret123'  # for flashing messages

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Image Cropper</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 20px auto; }
        canvas { border: 1px solid #ccc; cursor: crosshair; }
        label { display: block; margin-top: 10px; }
        input[type="number"] { width: 100px; }
        #crop-info { margin-top: 10px; font-weight: bold; }
        button { margin-top: 10px; padding: 8px 16px; }
    </style>
</head>
<body>
    <h2>Image Cropper with Fixed Aspect Ratio</h2>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul style="color:red;">
          {% for msg in messages %}
            <li>{{msg}}</li>
          {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}
    <form method="post" enctype="multipart/form-data" id="upload-form">
        <label>Select Image (jpg/png): <input type="file" name="image" accept="image/*" required></label>
        <label>Target File Size (KB): <input type="number" name="target_kb" value="15" min="1" required></label>
        <label>Width (cm): <input type="number" step="0.01" name="width_cm" value="6" min="0.1" required></label>
        <label>Height (cm): <input type="number" step="0.01" name="height_cm" value="2" min="0.1" required></label>
        <label>DPI: <input type="number" name="dpi" value="300" min="1" required></label>
        <button type="submit">Upload & Crop</button>
    </form>

    {% if img_url %}
    <h3>Crop the image</h3>
    <canvas id="canvas"></canvas>
    <div id="crop-info">Drag to select area. Aspect ratio is fixed.</div>
    <form method="post" action="{{ url_for('crop') }}">
        <input type="hidden" name="filename" value="{{ filename }}">
        <input type="hidden" id="crop_x" name="crop_x">
        <input type="hidden" id="crop_y" name="crop_y">
        <input type="hidden" id="crop_w" name="crop_w">
        <input type="hidden" id="crop_h" name="crop_h">
        <input type="hidden" name="target_kb" value="{{ target_kb }}">
        <input type="hidden" name="width_cm" value="{{ width_cm }}">
        <input type="hidden" name="height_cm" value="{{ height_cm }}">
        <input type="hidden" name="dpi" value="{{ dpi }}">
        <button type="submit">Crop & Download</button>
    </form>

    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        img.src = "{{ img_url }}";
        let rect = {};
        let drag = false;
        let aspectRatio = {{ width_cm / height_cm }};

        img.onload = () => {
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);

            canvas.addEventListener('mousedown', (e) => {
                const rectCanvas = canvas.getBoundingClientRect();
                rect.startX = e.clientX - rectCanvas.left;
                rect.startY = e.clientY - rectCanvas.top;
                rect.w = 0;
                rect.h = 0;
                drag = true;
                draw();
            });

            canvas.addEventListener('mousemove', (e) => {
                if (drag) {
                    const rectCanvas = canvas.getBoundingClientRect();
                    let mouseX = e.clientX - rectCanvas.left;
                    let mouseY = e.clientY - rectCanvas.top;

                    let dx = mouseX - rect.startX;
                    let dy = mouseY - rect.startY;

                    // Constrain to aspect ratio
                    if (Math.abs(dx) > Math.abs(dy)) {
                        dy = dx / aspectRatio;
                    } else {
                        dx = dy * aspectRatio;
                    }

                    rect.w = dx;
                    rect.h = dy;

                    // Prevent selection outside image bounds
                    if (rect.startX + rect.w > canvas.width) {
                        rect.w = canvas.width - rect.startX;
                        rect.h = rect.w / aspectRatio;
                    }
                    if (rect.startY + rect.h > canvas.height) {
                        rect.h = canvas.height - rect.startY;
                        rect.w = rect.h * aspectRatio;
                    }
                    if (rect.startX + rect.w < 0) {
                        rect.w = -rect.startX;
                        rect.h = rect.w / aspectRatio;
                    }
                    if (rect.startY + rect.h < 0) {
                        rect.h = -rect.startY;
                        rect.w = rect.h * aspectRatio;
                    }

                    draw();
                }
            });

            canvas.addEventListener('mouseup', (e) => {
                drag = false;
                updateForm();
            });

            canvas.addEventListener('mouseout', (e) => {
                if(drag) {
                    drag = false;
                    updateForm();
                }
            });

            function draw() {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0);
                if (rect.w && rect.h) {
                    ctx.strokeStyle = 'red';
                    ctx.lineWidth = 3;
                    ctx.setLineDash([6]);
                    ctx.strokeRect(rect.startX, rect.startY, rect.w, rect.h);
                    ctx.setLineDash([]);
                    ctx.fillStyle = 'rgba(255,0,0,0.2)';
                    ctx.fillRect(rect.startX, rect.startY, rect.w, rect.h);
                }
            }

            function updateForm() {
                const x = Math.min(rect.startX, rect.startX + rect.w);
                const y = Math.min(rect.startY, rect.startY + rect.h);
                const w = Math.abs(rect.w);
                const h = Math.abs(rect.h);
                document.getElementById('crop_x').value = Math.round(x);
                document.getElementById('crop_y').value = Math.round(y);
                document.getElementById('crop_w').value = Math.round(w);
                document.getElementById('crop_h').value = Math.round(h);
                document.getElementById('crop-info').textContent = `Crop area: ${Math.round(w)} x ${Math.round(h)} px`;
            }
        };
    </script>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("image")
        if not file:
            flash("No file selected")
            return redirect(request.url)
        filename = "uploaded_image.jpg"
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        # Store input params for next step
        target_kb = request.form.get("target_kb", "15")
        width_cm = request.form.get("width_cm", "6")
        height_cm = request.form.get("height_cm", "2")
        dpi = request.form.get("dpi", "300")

        return render_template_string(HTML_PAGE,
                                      img_url=url_for('uploaded_file', filename=filename),
                                      filename=filename,
                                      target_kb=target_kb,
                                      width_cm=float(width_cm),
                                      height_cm=float(height_cm),
                                      dpi=int(dpi))
    return render_template_string(HTML_PAGE, img_url=None)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_file(os.path.join(UPLOAD_FOLDER, filename))

@app.route("/crop", methods=["POST"])
def crop():
    filename = request.form.get("filename")
    crop_x = int(request.form.get("crop_x", 0))
    crop_y = int(request.form.get("crop_y", 0))
    crop_w = int(request.form.get("crop_w", 0))
    crop_h = int(request.form.get("crop_h", 0))

    target_kb = int(request.form.get("target_kb", 15))
    width_cm = float(request.form.get("width_cm", 6))
    height_cm = float(request.form.get("height_cm", 2))
    dpi = int(request.form.get("dpi", 300))

    if crop_w == 0 or crop_h == 0:
        flash("Invalid crop area!")
        return redirect(url_for("index"))

    path = os.path.join(UPLOAD_FOLDER, filename)
    image = Image.open(path)

    cropped = image.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))

    px_width = int((dpi / 2.54) * width_cm)
    px_height = int((dpi / 2.54) * height_cm)
    resized = cropped.resize((px_width, px_height), Image.Resampling.LANCZOS)

    quality = 95
    buffer = io.BytesIO()
    while quality > 10:
        buffer.seek(0)
        buffer.truncate()
        resized.save(buffer, format="JPEG", quality=quality, dpi=(dpi, dpi))
        kb_size = buffer.tell() / 1024
        if kb_size <= target_kb:
            break
        quality -= 5
    else:
        flash("Could not compress image to target size.")

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="final_output.jpg", mimetype="image/jpeg")

if __name__ == "__main__":
    app.run(debug=True)
