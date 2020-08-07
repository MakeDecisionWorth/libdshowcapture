import os
import platform
import sys
import numpy as np
from ctypes import *
from PIL import Image
import cv2

def resolve(name):
    f = os.path.join(os.path.dirname(__file__), name)
    return f

lib = None

#    int DSHOWCAPTURE_EXPORT get_frame(void *cap, int timeout, unsigned char *buffer, int size);
#    void DSHOWCAPTURE_EXPORT stop_capture(void *cap);
#    void DSHOWCAPTURE_EXPORT destroy_capture(void *cap);
#    int DSHOWCAPTURE_EXPORT capturing(void *cap);
#    void DSHOWCAPTURE_EXPORT lib_test(int n, int width, int height, int fps);

def create_frame_buffer(width, height):
    buffer = bytearray(width * height * 4)
    char_array = c_char * len(buffer)
    return char_array.from_buffer(buffer)

class DShowCapture():
    def __init__(self):
        global lib
        if lib is None:
            dll_path = resolve(os.path.join("vs", "2013", "x64", "Release", "dshowcapture_x64.dll"))
            lib = cdll.LoadLibrary(dll_path)
            lib.create_capture.restype = c_void_p
            lib.get_devices.argtypes = [c_void_p]
            lib.get_device.argtypes = [c_void_p, c_int, c_char_p, c_int]
            lib.capture_device.argtypes = [c_void_p, c_int, c_int, c_int, c_int]
            lib.capture_device_default.argtypes = [c_void_p, c_int]
            lib.get_width.argtypes = [c_void_p]
            lib.get_height.argtypes = [c_void_p]
            lib.get_fps.argtypes = [c_void_p]
            lib.get_flipped.argtypes = [c_void_p]
            lib.get_colorspace.argtypes = [c_void_p]
            lib.get_frame.argtypes = [c_void_p, c_int, c_char_p, c_int]
            lib.stop_capture.argtypes = [c_void_p]
            lib.destroy_capture.argtypes = [c_void_p]
        self.lib = lib
        self.cap = lib.create_capture()
        self.name_buffer = create_string_buffer(255);
        self.buffer = None

    def __del__(self):
        if not self.buffer is None:
            del self.buffer
        del self.name_buffer
        self.destroy_capture()

    def get_devices(self):
        return self.lib.get_devices(self.cap)

    def get_device(self, device_number):
        self.lib.get_device(self.cap, device_number, self.name_buffer, 255)
        name_str = str(self.name_buffer.value.decode('utf8'))
        return name_str

    def capture_device(self, cam, width, height, fps):
        ret = self.lib.capture_device(self.cap, cam, width, height, fps) == 1
        if ret:
            self.width = self.get_width()
            self.height = self.get_height()
            self.flipped = self.get_flipped()
            self.size = self.width * self.height * 4
            self.buffer = create_frame_buffer(self.width, self.height)
        return ret;

    def capture_device_default(self, cam):
        ret = self.lib.capture_device_default(self.cap, cam) == 1
        if ret:
            self.width = self.get_width()
            self.height = self.get_height()
            self.flipped = self.get_flipped()
            self.size = self.width * self.height * 4
            self.buffer = create_frame_buffer(self.width, self.height)
        return ret;

    def get_width(self):
        return self.lib.get_width(self.cap)

    def get_height(self):
        return self.lib.get_height(self.cap)

    def get_fps(self):
        return self.lib.get_fps(self.cap)

    def get_flipped(self):
        return self.lib.get_flipped(self.cap) != 0

    def get_colorspace(self):
        return self.lib.get_colorspace(self.cap)

    def get_frame(self, timeout):
        if self.lib.get_frame(self.cap, timeout, self.buffer, self.size) == 0:
            return None
        img = Image.frombuffer('RGBA', (self.width, self.height), self.buffer, 'raw', 'BGRA', 0, 1)
        img = np.array(img)
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR);
        if not self.flipped:
            img = cv2.flip(img, 0)
        return img

    def stop_capture(self):
        return self.lib.stop_capture(self.cap)

    def destroy_capture(self):
        if self.cap is None:
            return 0
        ret = self.lib.destroy_capture(self.cap)
        self.cap = None
        return ret

if __name__ == "__main__":
    cam = 0
    width = 1280
    height = 720
    fps = 30
    if len(sys.argv) > 1:
        cam = int(sys.argv[1])
    if len(sys.argv) > 2:
        width = int(sys.argv[2])
    if len(sys.argv) > 3:
        height = int(sys.argv[3])
    if len(sys.argv) > 4:
        fps = int(sys.argv[4])

    cap = DShowCapture()
    devices = cap.get_devices()
    print("Devices: ", devices)
    for i in range(devices):
        print(f"{i} {cap.get_device(i)}")

    print(f"Capturing: {cap.capture_device(cam, width, height, fps)}")
    #print(f"Capturing: {cap.capture_device_default(cam)}")
    width = cap.get_width()
    height = cap.get_height()
    flipped = cap.get_flipped()
    print(f"Width: {width} Height: {height} FPS: {cap.get_fps()} Flipped: {flipped} Colorspace: {cap.get_colorspace()}")
    
    while True:
        img = cap.get_frame(1000)
        if not img is None:
            cv2.imshow("DShowCapture", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                sys.exit(0)
        else:
            print("Lost frame")

    cap.stop_capture()
    cap.destroy_capture()
    del cap