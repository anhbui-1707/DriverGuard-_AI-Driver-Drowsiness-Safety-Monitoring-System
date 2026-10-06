# Phase 1 verification

## Implemented

Streamlit UI; OpenCV local webcam; MediaPipe Face Landmarker VIDEO;
landmark overlay; camera/face status; processing FPS; Start/Stop;
duplicate-start prevention; process-wide camera ownership; UI heartbeat;
read retry limit; error reporting and resource cleanup.

All source files are new. No existing application was overwritten.
No later-phase detectors, risk logic, storage or simulation were added.

## Automated checks completed

- Python 3.12/Linux: 13 pytest checks passed.
- Syntax compilation and imports passed.
- `pip check`: no broken requirements.
- Streamlit server health and HTML endpoint: HTTP 200.
- Streamlit AppTest: cold startup and Start/Stop/rerun with fake camera.
- Real MediaPipe model: two blank frames return no face.
- Real MediaPipe model in background worker: frame processing and Stop cleanup passed.
- Real MediaPipe model: official MediaPipe portrait test image returns 478 landmarks.
- Actual unavailable webcam: readable CameraError and worker termination.
- Windows/Python 3.11: downloaded compatible wheels for all four direct runtime dependencies.

Final versions: Streamlit 1.44.1, MediaPipe 0.10.21, OpenCV 4.11.0.86,
NumPy 1.26.4. The initial MediaPipe 1.0.1 candidate failed the background
worker shutdown check and is not part of this deliverable. The final model
checks run on CPU without extra system libraries.

## Not verified here

There is no physical webcam in this environment. Actual Windows webcam,
DirectShow fallback, hardware release, lighting quality and performance
must be checked using the README checklist. Downloading Windows wheels is
not equivalent to executing the application on Windows.

No public deployment was performed. Use the local startup command in README.
