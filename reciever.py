from flask import Flask, render_template, Response
import cv2
import socket
import pickle
import struct

app = Flask(__name__)

# Socket setup for receiving camera frames
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    server_socket.bind(('192.168.1.20', 9999))  # Replace with your IP and port
except OSError as e:
    print(f"Error binding to port: {e}")
    exit(1)
server_socket.listen(10)

conn, addr = server_socket.accept()

data = b""
payload_size = struct.calcsize(">L")

def receive_frames():
    global data
    while True:
        # Retrieve message size
        while len(data) < payload_size:
            data += conn.recv(4096)

        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack(">L", packed_msg_size)[0]

        # Retrieve all data based on message size
        while len(data) < msg_size:
            data += conn.recv(4096)

        frame_data = data[:msg_size]
        data = data[msg_size:]

        # Deserialize frame
        frame = pickle.loads(frame_data)

        # Decode the frame
        frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)

        if frame is None:
            print("No frame received")
            continue

        print("Frame received")

        # Convert frame to JPEG for streaming
        _, jpeg = cv2.imencode('.jpg', frame)

        # Yield frame in the MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    print("Client requested video feed")
    return Response(receive_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

