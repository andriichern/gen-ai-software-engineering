#!/bin/bash
# Install project dependencies without venv
# Uses PIP_BREAK_SYSTEM_PACKAGES for this run only (project-scoped, not global)
PIP_BREAK_SYSTEM_PACKAGES=1 pip3 install -r requirements.txt
