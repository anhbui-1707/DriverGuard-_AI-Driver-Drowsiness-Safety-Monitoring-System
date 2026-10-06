"""Isolated UI QA entry point; production runs app.py, never this file."""
import os
import runpy
import sys
from dataclasses import replace
from pathlib import Path
import streamlit as st

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from config import SETTINGS
from core.runtime import MonitorRuntime

if "runtime" not in st.session_state:
    path = Path(os.environ["DRIVERGUARD_QA_DATABASE"])
    st.session_state.runtime = MonitorRuntime(replace(SETTINGS, database_path=path,
                                                     snapshot_root=path.parent, audio_enabled=False))
runpy.run_path(str(root / "app.py"), run_name="__main__")
