# Changelog

All notable changes to **JARVIS-PiPER** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-05

### Added
- Complete embodied-AI data collection platform for AgileX PIKA Sense + PiPER 6-DOF arm.
- ROS 2 Lyrical multi-modal time synchronizer and asynchronous lossless episode recorder.
- 4 operating modes: `hardware`, `simulation`, `mock`, and `replay`.
- Hardware Abstraction Layer (HAL) with mock and hardware adapters.
- 7-Point automated dataset quality assurance suite (Tiers A, B, C, D).
- Universal multi-format dataset exporter: LeRobot 2.0, ALOHA HDF5/NPZ, RLDS, and MCAP.
- V-JEPA visual world model learning module with multi-frame sampling, ViT context/target encoders, and rollout predictor.
- Full CLI suite (`jarvis-piper doctor`, `demo`, `record`, `stop`, `status`, `validate`, `inspect`, `replay`, `dataset`, `train`, `evaluate`, `export`, `version`).
- Interactive live terminal TUI and HTML5 Web operator dashboard.
- GitHub Actions CI workflows for ROS 2, Python, and linting.
