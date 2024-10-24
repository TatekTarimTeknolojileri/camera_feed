import sys
import numpy as np
import pyzed.sl as sl
import cv2
import socket
import pickle
import struct

def main():
    # Create a ZED camera object
    zed = sl.Camera()

    # Set configuration parameters
    init = sl.InitParameters()
    init.camera_resolution = sl.RESOLUTION.HD1080
    init.depth_mode = sl.DEPTH_MODE.PERFORMANCE
    init.coordinate_units = sl.UNIT.MILLIMETER

    # Open the camera
    err = zed.open(init)
    if err != sl.ERROR_CODE.SUCCESS:
        print(repr(err))
        zed.close()
        exit(1)

    # Set runtime parameters after opening the camera
    runtime = sl.RuntimeParameters()

    # Prepare new image size to retrieve half-resolution images
    image_size = zed.get_camera_information().camera_configuration.resolution
    image_size.width = image_size.width / 2
    image_size.height = image_size.height / 2

    # Declare sl.Mat matrices
    image_zed = sl.Mat(image_size.width, image_size.height, sl.MAT_TYPE.U8_C4)

    # Socket setup for transmitting
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('192.168.1.20', 9999))  # Replace with receiver IP and port
    connection = client_socket.makefile('wb')

    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]  # JPEG compression quality

    while True:
        err = zed.grab(runtime)
        if err == sl.ERROR_CODE.SUCCESS:
            # Retrieve the left image
            zed.retrieve_image(image_zed, sl.VIEW.LEFT, sl.MEM.CPU, image_size)

            # Convert ZED image to OpenCV format
            image_ocv = image_zed.get_data()

            # JPEG compression
            result, frame = cv2.imencode('.jpg', image_ocv, encode_param)

            # Serialize frame for sending
            data = pickle.dumps(frame, 0)
            size = len(data)

            # Send frame size first, then the frame data
            client_socket.sendall(struct.pack(">L", size) + data)

            cv2.imshow("Streaming", image_ocv)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    client_socket.close()
    cv2.destroyAllWindows()
    zed.close()

if __name__ == "__main__":
    main()
