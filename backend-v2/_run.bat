@echo off
cd /d "d:\Anti Gravity LIMS\rd-lab-instance\backend-v2"
python -m scripts.seed_test_templates --validate-only > _val.txt 2>&1
echo EXIT=%ERRORLEVEL% >> _val.txt
