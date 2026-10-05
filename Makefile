.PHONY: all install setup build test clean doctor demo validate export

all: build

install:
	bash scripts/install.sh

check-env:
	bash scripts/check_environment.sh

setup:
	bash scripts/setup.sh --mode mock

setup-hardware:
	bash scripts/setup.sh --mode hardware

setup-sim:
	bash scripts/setup.sh --mode simulation

build:
	bash scripts/build.sh

doctor:
	python3 python/jarvis_piper/cli/main.py doctor

demo:
	python3 python/jarvis_piper/cli/main.py demo --episodes 2 --steps 60

test:
	pytest tests/ -v

validate:
	python3 python/jarvis_piper/cli/main.py validate --dataset dataset/raw/

export:
	python3 python/jarvis_piper/cli/main.py export --format all

clean:
	bash scripts/clean.sh
