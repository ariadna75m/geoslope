import base64
import streamlit as st
import streamlit.components.v1 as components


def render_camera_ghost_overlay(reference_image_bytes: bytes = None):
    """
    Superpone la fotografia de referencia semitransparente (fantasma)
    sobre el preview de la camara en vivo para replicar encuadre.
    """
    img_b64 = ""
    if reference_image_bytes:
        img_b64 = f"data:image/jpeg;base64,{base64.b64encode(reference_image_bytes).decode('utf-8')}"

    html_code = f"""
    <div style="position: relative; width: 100%; max-width: 520px; margin: auto; background: #111; border-radius: 8px; overflow: hidden; padding: 8px;">
        <div style="position: relative; width: 100%; height: 380px; background: #000; border-radius: 6px; overflow: hidden;">
            <!-- Camara en vivo -->
            <video id="webcam" autoplay playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>
            
            <!-- Capa fantasma (foto de referencia con opacidad) -->
            <img id="ghost-layer" src="{img_b64}" 
                 style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
                        object-fit: cover; opacity: 0.45; pointer-events: none; 
                        display: {'block' if img_b64 else 'none'};" />
        </div>

        <div style="margin-top: 10px; display: flex; align-items: center; justify-content: space-between; font-family: sans-serif; font-size: 13px; color: #eee;">
            <label style="display: flex; align-items: center; gap: 8px;">
                <span>Opacidad guía:</span>
                <input type="range" id="opacitySlider" min="0" max="1" step="0.05" value="0.45" 
                       oninput="document.getElementById('ghost-layer').style.opacity = this.value">
            </label>
            <button id="capture-btn" style="padding: 6px 14px; background: #0284c7; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: bold;">
                Capturar Foto
            </button>
        </div>
        <canvas id="canvas" style="display: none;"></canvas>
    </div>

    <script>
        const video = document.getElementById('webcam');
        const captureBtn = document.getElementById('capture-btn');
        const canvas = document.getElementById('canvas');

        navigator.mediaDevices.getUserMedia({{
            video: {{ facingMode: "environment" }},
            audio: false
        }})
        .then(stream => {{
            video.srcObject = stream;
        }})
        .catch(err => {{
            console.error("Error de acceso a camara:", err);
        }});

        captureBtn.onclick = function() {{
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        }};
    </script>
    """
    components.html(html_code, height=450)
