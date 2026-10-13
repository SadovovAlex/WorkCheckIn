import cv2
import time

for backend_name, backend in [
    ("default", None),
    ("DSHOW", cv2.CAP_DSHOW),
    ("MSMF", cv2.CAP_MSMF),
]:
    for cam_id in range(3):
        print(f"\n--- {backend_name}, camera_id={cam_id} ---")
        try:
            cap = cv2.VideoCapture(cam_id, backend) if backend is not None else cv2.VideoCapture(cam_id)
            if not cap.isOpened():
                print("  ❌ не открылась")
                cap.release()
                continue

            ok_count = 0
            for i in range(30):
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    ok_count += 1
                time.sleep(0.033)

            print(f"  ✅ открылась, кадров получено: {ok_count}/30")
            if ok_count > 0:
                print(f"     размер кадра: {frame.shape}")
            cap.release()
        except Exception as e:
            print(f"  ❌ ошибка: {e}")