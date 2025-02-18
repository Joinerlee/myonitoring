# tests/test_camera.py
import unittest
from hardware.camera import CameraIMX219

class TestCamera(unittest.TestCase):
    def setUp(self):
        self.camera = CameraIMX219()
    
    def test_camera_initialization(self):
        self.assertIsNotNone(self.camera.picam2)
