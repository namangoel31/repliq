#!/bin/bash
set -euo pipefail

#activating conda env inside container instead of doing from manifest file.
. /opt/conda/etc/profile.d/conda.sh
conda activate repliq

#setting python output to unbuffered.
export PYTHONUNBUFFERED=1

#Forcing jupyter to run as PID 1 for the logs to show up in kubectl logs and cloudwatch
cd /home/repliq
exec uvicorn main:app --reload --host 0.0.0.0 --port 8000