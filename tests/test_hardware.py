# main.py
from hardware.camera import CameraIMX219

def main():
    camera = CameraIMX219()
    try:
        image_files = camera.start_capture()
        print(f"Captured {len(image_files)} images")
    finally:
        camera.cleanup()

if __name__ == "__main__":
    main()
