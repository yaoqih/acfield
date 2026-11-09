"""Resource-order compatibility wrapper for pupil-apriltags 1.0.4.post11.

Destroying registered tag families before the detector can leave the detector
holding dangling pointers on Linux. See pupil-labs/apriltags#65 and #76.
Keep this local to ACField instead of modifying installed package files.
"""
from pupil_apriltags import Detector as PupilDetector


class Detector(PupilDetector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # pupil-apriltags 1.0.4 truncates this floating-point parameter to int.
        self.tag_detector_ptr.contents.decode_sharpening = float(self.params['decode_sharpening'])

    def __del__(self):
        detector = getattr(self, "tag_detector_ptr", None)
        if detector is None:
            return
        # The detector still references its families while releasing its state.
        self.libc.apriltag_detector_destroy.restype = None
        self.libc.apriltag_detector_destroy(detector)
        self.tag_detector_ptr = None
        for family, pointer in getattr(self, "tag_families", {}).items():
            destroy = getattr(self.libc, family + "_destroy")
            destroy.restype = None
            destroy(pointer)
        self.tag_families = {}
