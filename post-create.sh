#!/bin/sh
# activate pre-commit hooks
pre-commit install
echo "pre-commit hooks installed"

echo "installing local python module in editable mode"
pip3 install -e .
