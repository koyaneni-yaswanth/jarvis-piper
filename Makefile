.PHONY: all doctor robot-model-audit hardware-connection-test teleoperation-test recorder-test \
        dataset-validate dataset-export-test public-dataset-audit isaac-doctor isaac-gui-test \
        isaac-robot-test imitation-pilot rl-pilot evaluate-policy export-policy policy-dry-run \
        jarvis-pick-place-sim jarvis-hardware-readiness readme-command-test final-report test clean build

all: build

doctor:
	python python/jarvis_piper/cli/main.py doctor

robot-model-audit:
	python scripts/robot_model_audit.py

hardware-connection-test:
	python scripts/hardware_connection_test.py

teleoperation-test:
	python scripts/teleoperation_test.py

recorder-test:
	python -m pytest tests/dataset/ -v

dataset-validate:
	python python/jarvis_piper/cli/main.py validate --dataset dataset/raw/

dataset-export-test:
	python -m pytest tests/dataset/test_exporters.py -v

public-dataset-audit:
	python scripts/download_public_dataset_sample.py --dataset lerobot_aloha_sample --output dataset/public/lerobot_aloha_sample

isaac-doctor:
	python scripts/isaac/isaac_doctor.py

isaac-gui-test:
	python scripts/isaac/urdf_to_usd.py --urdf ros2_ws/src/jarvis_piper_bringup/urdf/piper.urdf --output models/usd/piper.usda

isaac-robot-test:
	python scripts/isaac/test_isaac_headless.py

imitation-pilot:
	python python/learning/imitation/train_imitation.py --epochs 10 --model-type bc

rl-pilot:
	python python/learning/rl/train_rl.py --epochs 15 --steps 200

evaluate-policy:
	python python/learning/imitation/eval_imitation.py --checkpoint models/checkpoints/imitation/bc_piper_policy.pt

export-policy:
	python python/learning/export_onnx.py --checkpoint models/checkpoints/imitation/bc_piper_policy.pt

policy-dry-run:
	python scripts/policy_dry_run.py

jarvis-pick-place-sim:
	python -c "import sys; sys.path.insert(0, 'python'); from jarvis_piper.tasks.pick_and_place import PickAndPlaceTask; t = PickAndPlaceTask(); res = t.execute_task('Pick up red cube and place in blue tray'); sys.exit(0 if res['success'] else 1)"

jarvis-hardware-readiness:
	python scripts/hardware_readiness_audit.py

audit-and-validate:
	python scripts/audit_and_validate.py

readme-command-test:
	python scripts/test_readme_commands.py

final-report:
	cat docs/FINAL_ACCEPTANCE_REPORT.md

test:
	pytest tests/ -v

build:
	bash scripts/build.sh

clean:
	bash scripts/clean.sh
