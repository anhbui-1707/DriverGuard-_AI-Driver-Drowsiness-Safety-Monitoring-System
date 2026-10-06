# Phase 2

Added: vision/eye_detector.py; tests/test_eye_detector.py; this document.
Changed: config.py; core/types.py; core/pipeline.py; core/runtime.py; ui/live_monitor.py; app.py; README.md.

EAR uses pixel coordinates and six landmarks per eye. Combined EAR is the mean of both eyes. Hysteresis reduces threshold oscillation. The closure timer accumulates only consecutive valid CLOSED observations; missing data pauses it. A gap beyond 0.5 seconds resets continuity. A new worker creates a new detector.

Verification: 20 pytest tests; syntax compilation; real MediaPipe worker processing and shutdown. Webcam hardware checks still require Windows testing. Existing Start/Stop/rerun and camera-error tests are retained.

No yawn, head pose, risk engine, audio, confirmation or database implemented. No dependencies added. EAR defaults require personal adjustment for glasses, lighting, head angle and eye shape.
