"""Task 2: 60 s of MediaPipe Hands, headless, 30 fps pacing, on synthetic person-free frames
(seeded noise + gradient). No hand is present, so this is the palm-detector-every-frame path."""
import time
import numpy as np
import os
import mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision

W, H, FPS, SECONDS = 640, 480, 30, int(os.environ.get("HANDS_SECONDS", 60))
rng = np.random.default_rng(0)
grad = np.linspace(0, 255, W, dtype=np.uint8)[None, :, None].repeat(H, 0).repeat(3, 2)
frames = [np.clip(grad.astype(np.int16) + rng.integers(-20, 20, (H, W, 3)), 0, 255).astype(np.uint8)
          for _ in range(30)]
MODEL = os.path.expanduser("~/joules-spike/env/hand_landmarker.task")
hands = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
    base_options=mpt.BaseOptions(model_asset_path=MODEL),
    running_mode=vision.RunningMode.VIDEO, num_hands=2))
t0 = time.perf_counter(); n = 0; found = 0
while True:
    due = t0 + n / FPS
    if due - t0 >= SECONDS:
        break
    now = time.perf_counter()
    if due > now:
        time.sleep(due - now)
    r = hands.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=frames[n % len(frames)]),
                              int(n * 1000 / FPS))
    found += bool(r.hand_landmarks)
    n += 1
print("frames=%d hands_found=%d" % (n, found))
