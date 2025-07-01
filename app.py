from flask import Flask, render_template_string, request, send_file, redirect, url_for, flash
from PIL import Image
import io
import os

app = Flask(__name__)
app.secret_key = 'secret123'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Image Cropper</title>
<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background-color: #f4f7fa;
  color: #333;
  line-height: 1.6;
  padding: 20px;
}
.container {
  max-width: 700px;
  margin: auto;
  background: #fff;
  padding: 30px;
  border-radius: 15px;
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}
h2, h3 {
  text-align: center;
  margin-bottom: 20px;
  color: #2c3e50;
}
ul.flashes {
  list-style: none;
  padding-left: 0;
  color: red;
  margin-bottom: 15px;
  text-align: center;
}
form label {
  display: block;
  margin-top: 15px;
  font-weight: 600;
}
input[type="file"],
input[type="number"] {
  width: 100%;
  padding: 10px;
  margin-top: 5px;
  border: 1px solid #ccc;
  border-radius: 8px;
  font-size: 1rem;
}
button {
  margin-top: 20px;
  background: #3498db;
  color: #fff;
  padding: 12px 20px;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  cursor: pointer;
  transition: background 0.3s ease;
  display: block;
  width: 100%;
}
button:hover {
  background: #2980b9;
}
canvas {
  display: block;
  margin: 30px auto;
  border: 2px dashed #ccc;
  max-width: 100%;
  height: auto;
  touch-action: none;
  border-radius: 8px;
}
#crop-info {
  text-align: center;
  font-weight: 600;
  color: #555;
  margin-top: 10px;
}

.loader {
  border: 6px solid #f3f3f3;
  border-top: 6px solid #3498db;
  border-radius: 50%;
  width: 40px;
  height: 40px;
  animation: spin 1s linear infinite;
  margin: auto;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

</style>
</head>
<body>
  <div class="container">
  <h2>Image Cropper with Fixed Aspect Ratio</h2>

  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <ul class="flashes">
      {% for msg in messages %}
        <li>{{ msg }}</li>
      {% endfor %}
      </ul>
    {% endif %}
  {% endwith %}

  <form method="post" enctype="multipart/form-data" id="upload-form">
    <label>Select Image (jpg/png):</label>
    <input type="file" name="image" accept="image/*" required />
    <label>Target File Size (KB):</label>
    <input type="number" name="target_kb" value="15" min="1" required />
    <label>Width (cm):</label>
    <input type="number" step="0.01" name="width_cm" value="6" min="0.1" required />
    <label>Height (cm):</label>
    <input type="number" step="0.01" name="height_cm" value="2" min="0.1" required />
    <label>DPI:</label>
    <input type="number" name="dpi" value="300" min="1" required />
    <button type="submit">Upload & Crop</button>
  </form>

  {% if img_url %}

  <h3>Crop the image</h3>
  <div id="canvas-container" style="position: relative; width: 100%; min-height: 300px;">
    <div id="spinner" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 10;">
      <div class="loader"></div>
    </div>
    <canvas id="canvas" style="display: none;"></canvas>
  </div>
  <div id="crop-info">Drag to select area. Aspect ratio is fixed. Touch supported.</div>

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

let aspectRatio = {{ width_cm / height_cm }};
let rect = null;
let drag = false;
let dragOffsetX = 0;
let dragOffsetY = 0;
let isDrawing = false;

function getMousePos(e) {
  const rectCanvas = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rectCanvas.width;
  const scaleY = canvas.height / rectCanvas.height;
  const clientX = e.clientX || e.pageX;
  const clientY = e.clientY || e.pageY;
  return {
    x: (clientX - rectCanvas.left) * scaleX,
    y: (clientY - rectCanvas.top) * scaleY
  };
}

img.onload = () => {
  canvas.width = img.width;
  canvas.height = img.height;
  draw();

  canvas.addEventListener('mousedown', handleStart);
  canvas.addEventListener('mousemove', handleMove);
  canvas.addEventListener('mouseup', handleEnd);
  canvas.addEventListener('mouseout', handleEnd);

  canvas.addEventListener('touchstart', e => handleStart(e.touches[0]));
  canvas.addEventListener('touchmove', e => {
    e.preventDefault();
    handleMove(e.touches[0]);
  }, { passive: false });
  canvas.addEventListener('touchend', handleEnd);
};

function handleStart(e) {
  const pos = getMousePos(e);
  if (rect && pointInRect(pos.x, pos.y, rect)) {
    drag = true;
    dragOffsetX = pos.x - rect.x;
    dragOffsetY = pos.y - rect.y;
    isDrawing = false;
  } else {
    rect = { x: pos.x, y: pos.y, w: 0, h: 0 };
    isDrawing = true;
    drag = false;
  }
}

function handleMove(e) {
  const pos = getMousePos(e);
  if (drag && rect) {
    let newX = pos.x - dragOffsetX;
    let newY = pos.y - dragOffsetY;

    newX = Math.min(Math.max(0, newX), canvas.width - rect.w);
    newY = Math.min(Math.max(0, newY), canvas.height - rect.h);

    rect.x = newX;
    rect.y = newY;
    draw();
    updateForm();
  } else if (isDrawing && rect) {
    let dx = pos.x - rect.x;
    let dy = pos.y - rect.y;

    if (Math.abs(dx) > Math.abs(dy)) {
      dy = dx / aspectRatio;
    } else {
      dx = dy * aspectRatio;
    }

    if (rect.x + dx > canvas.width) {
      dx = canvas.width - rect.x;
      dy = dx / aspectRatio;
    }
    if (rect.y + dy > canvas.height) {
      dy = canvas.height - rect.y;
      dx = dy * aspectRatio;
    }
    if (rect.x + dx < 0) {
      dx = -rect.x;
      dy = dx / aspectRatio;
    }
    if (rect.y + dy < 0) {
      dy = -rect.y;
      dx = dy * aspectRatio;
    }

    rect.w = dx;
    rect.h = dy;
    draw();
  }
}

function handleEnd(e) {
  if (isDrawing) {
    if (rect.w < 0) {
      rect.x += rect.w;
      rect.w = -rect.w;
    }
    if (rect.h < 0) {
      rect.y += rect.h;
      rect.h = -rect.h;
    }
  }
  drag = false;
  isDrawing = false;
  updateForm();
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0);
  if (rect) {
    ctx.strokeStyle = 'red';
    ctx.lineWidth = 3;
    ctx.setLineDash([6]);
    ctx.strokeRect(rect.x, rect.y, rect.w, rect.h);
    ctx.setLineDash([]);
    ctx.fillStyle = 'rgba(255, 0, 0, 0.2)';
    ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
  }
}

function updateForm() {
  if (!rect) return;
  document.getElementById('crop_x').value = Math.round(rect.x);
  document.getElementById('crop_y').value = Math.round(rect.y);
  document.getElementById('crop_w').value = Math.round(rect.w);
  document.getElementById('crop_h').value = Math.round(rect.h);
  document.getElementById('crop-info').textContent =
    `Crop area: ${Math.round(rect.w)} x ${Math.round(rect.h)} px`;
}

function pointInRect(x, y, r) {
  return x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h;
}

img.onload = () => {
  const spinner = document.getElementById('spinner');
  const canvasEl = document.getElementById('canvas');

  canvas.width = img.width;
  canvas.height = img.height;
  draw();

  // Hide spinner and show canvas
  spinner.style.display = "none";
  canvasEl.style.display = "block";

  canvas.addEventListener('mousedown', handleStart);
  canvas.addEventListener('mousemove', handleMove);
  canvas.addEventListener('mouseup', handleEnd);
  canvas.addEventListener('mouseout', handleEnd);

  canvas.addEventListener('touchstart', e => handleStart(e.touches[0]));
  canvas.addEventListener('touchmove', e => {
    e.preventDefault();
    handleMove(e.touches[0]);
  }, { passive: false });
  canvas.addEventListener('touchend', handleEnd);
};

</script>
{% endif %}
</div>

<footer style="text-align:center; margin-top:40px; padding:15px 0; font-size:0.9rem; color:#888;">
  Made with ❤️ by <a href="https://github.com/imvickykumar999/Image-Resizer" target="_blank" style="color:#3498db; text-decoration:none;">
    @imvickykumar999
  </a><br>
</footer>

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

    if resized.mode == 'RGBA':
        resized = resized.convert('RGB')

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
    app.run(debug=True, host="0.0.0.0")
