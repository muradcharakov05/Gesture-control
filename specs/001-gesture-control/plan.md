# Implementation Plan

**Date**: 2026-11-13 | **Spec**: [spec.md](spec.md)

## Summary
Windows desktop application using local webcam tracking, safe opt-in cursor control and pinch click.

## Technical Context
Python 3.13, Tkinter, MediaPipe Tasks, OpenCV, Pillow, PyAutoGUI. JSON settings in user profile. Windows global F8 via RegisterHotKey. Camera and tracking run in a worker thread; the GUI owns widgets and polls the latest result. No network or recording during operation.

## Constitution Check
Default Spec Kit constitution has no project-specific rules. Pass.

## Project Structure
`app/` contains tracking, gesture logic, settings, hotkey and UI; `models/` contains the MediaPipe model; `tests/` validates safety-critical state transitions. `main.py` starts the application.
