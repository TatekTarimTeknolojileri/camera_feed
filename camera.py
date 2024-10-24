from flask import Flask, render_template, Response
import cv2
import pyzed.sl as sl
import threading

app = Flask(__name__)

# Global değişkenler
camera_running = False
output_frame = None
lock = threading.Lock()

def zed_camera_stream():
    global output_frame, camera_running

    # Eğer kamera zaten çalışıyorsa, bir daha başlatma
    if camera_running:
        return

    camera_running = True
    zed = sl.Camera()
    
    # Kamera yapılandırma parametreleri
    init_params = sl.InitParameters()
    init_params.camera_resolution = sl.RESOLUTION.HD1080
    init_params.depth_mode = sl.DEPTH_MODE.PERFORMANCE
    init_params.coordinate_units = sl.UNIT.MILLIMETER
    
    # Kamerayı aç
    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        zed.close()
        camera_running = False
        return

    # Çalışma parametreleri
    runtime_params = sl.RuntimeParameters()
    image_size = zed.get_camera_information().camera_configuration.resolution
    image_size.width = image_size.width // 2
    image_size.height = image_size.height // 2

    # Görüntü alanı
    image_zed = sl.Mat(image_size.width, image_size.height, sl.MAT_TYPE.U8_C4)

    while camera_running:
        # Görüntü al
        if zed.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
            zed.retrieve_image(image_zed, sl.VIEW.LEFT)
            frame = image_zed.get_data()

            # OpenCV formatına çevir
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

            # Lock kullanarak güvenli bir şekilde frame'i kaydet
            with lock:
                output_frame = frame.copy()

    zed.close()

# Kamera akışını sürekli çalıştıran fonksiyon
def generate():
    global output_frame
    while True:
        with lock:
            if output_frame is None:
                continue

            # JPEG formatında kodla
            ret, jpeg = cv2.imencode('.jpg', output_frame)
            if not ret:
                continue

        # HTTP yanıtı olarak çerçeveyi döndür
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')

# Video akışını sağlayan route
@app.route('/video_feed')
def video_feed():
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Ana sayfa route'u
@app.route('/')
def index():
    return render_template('index.html')

# Ana thread ile kamera başlatma işlemi
if __name__ == "__main__":
    # Kamerayı başlatan thread'i burada başlat
    camera_thread = threading.Thread(target=zed_camera_stream)
    camera_thread.daemon = True
    camera_thread.start()

    app.run(host='0.0.0.0', port=5000, debug=False)
