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
  body {
    font-family: Arial, sans-serif;
    max-width: 900px;
    margin: 20px auto;
    padding: 0 10px;
  }
  h2, h3 { text-align: center; }
  form > label {
    display: block;
    margin: 10px 0 5px;
    font-weight: bold;
  }
  input[type="file"], input[type="number"] {
    width: 100%;
    max-width: 300px;
    padding: 6px;
    box-sizing: border-box;
  }
  button {
    margin-top: 15px;
    padding: 10px 20px;
    font-size: 1rem;
    cursor: pointer;
  }
  canvas {
    display: block;
    margin: 20px auto;
    border: 2px solid #ccc;
    max-width: 100%;
    touch-action: none;
  }
  #crop-info {
    text-align: center;
    font-weight: bold;
    margin-top: 5px;
  }
  ul.flashes {
    color: red;
    list-style: none;
    padding-left: 0;
  }
</style>
</head>
<body>
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
  <canvas id="canvas"></canvas>
  <div id="crop-info">Drag to select area. Aspect ratio is fixed. After selection, drag rectangle to move it.</div>

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
let rect = null;  // {x, y, w, h}
let drag = false;
let dragOffsetX = 0;
let dragOffsetY = 0;
let isDrawing = false;

function getMousePos(e) {
  const rectCanvas = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rectCanvas.width;
  const scaleY = canvas.height / rectCanvas.height;
  return {
    x: (e.clientX - rectCanvas.left) * scaleX,
    y: (e.clientY - rectCanvas.top) * scaleY
  };
}

img.onload = () => {
  canvas.width = img.width;
  canvas.height = img.height;
  draw();

  canvas.addEventListener('mousedown', e => {
    const pos = getMousePos(e);
    if (rect && pointInRect(pos.x, pos.y, rect)) {
      drag = true;
      dragOffsetX = pos.x - rect.x;
      dragOffsetY = pos.y - rect.y;
      isDrawing = false;
    } else {
      // Start drawing new rect
      rect = { x: pos.x, y: pos.y, w: 0, h: 0 };
      isDrawing = true;
      drag = false;
    }
  });

  canvas.addEventListener('mousemove', e => {
    const pos = getMousePos(e);
    if (drag && rect) {
      // Move rect but keep inside canvas
      let newX = pos.x - dragOffsetX;
      let newY = pos.y - dragOffsetY;

      newX = Math.min(Math.max(0, newX), canvas.width - rect.w);
      newY = Math.min(Math.max(0, newY), canvas.height - rect.h);

      rect.x = newX;
      rect.y = newY;
      draw();
      updateForm();
    } else if (isDrawing && rect) {
      // Calculate size while keeping aspect ratio
      let dx = pos.x - rect.x;
      let dy = pos.y - rect.y;

      if (Math.abs(dx) > Math.abs(dy)) {
        dy = dx / aspectRatio;
      } else {
        dx = dy * aspectRatio;
      }

      // Adjust if out of canvas bounds
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
  });

  canvas.addEventListener('mouseup', e => {
    if (isDrawing) {
      // Make width/height positive and adjust x,y accordingly
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
  });

  canvas.addEventListener('mouseout', e => {
    drag = false;
    isDrawing = false;
  });

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
