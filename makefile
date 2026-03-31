# PyScript-dict Makefile
# 可自定义的配置项
PYTHON = python

# 使用 uv 运行主程序
run:
	uv run main.py

# 兼容的直接运行方式
run-python:
	$(PYTHON) main.py