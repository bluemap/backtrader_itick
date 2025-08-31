# 港美股量化交易通知系统 Makefile

.PHONY: help install install-dev test lint format clean run backtest docs

# 默认目标
help:
	@echo "可用命令:"
	@echo "  install     - 安装项目依赖"
	@echo "  install-dev - 安装开发依赖"
	@echo "  test        - 运行测试"
	@echo "  lint        - 代码风格检查"
	@echo "  format      - 代码格式化"
	@echo "  clean       - 清理临时文件"
	@echo "  run         - 运行系统"
	@echo "  backtest    - 运行回测"
	@echo "  docs        - 生成文档"
	@echo "  setup       - 初始设置"

# 安装项目依赖
install:
	pip install -r requirements.txt

# 安装开发依赖
install-dev:
	pip install -r requirements.txt
	pip install -e .[dev]

# 运行测试
test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# 代码风格检查
lint:
	flake8 src/ main.py cli.py
	mypy src/

# 代码格式化
format:
	black src/ main.py cli.py setup.py
	isort src/ main.py cli.py setup.py

# 清理临时文件
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

# 运行系统
run:
	python main.py --mode run

# 运行回测
backtest:
	python main.py --mode backtest --start-date 2023-01-01 --end-date 2023-12-31

# 测试通知
test-notifications:
	python main.py --mode test

# 生成文档
docs:
	@echo "生成文档..."
	@echo "请查看 docs/ 目录中的文档文件"

# 初始设置
setup:
	@echo "初始化项目..."
	mkdir -p logs
	mkdir -p data/historical
	@echo "请编辑 config/config.yaml 文件设置您的配置"
	@echo "特别是 iTick API Key 和通知配置"

# 检查配置
check-config:
	python -c "from src.core.config_manager import config_manager; print('配置验证:', config_manager.validate_config())"

# 查看系统状态
status:
	python cli.py status

# 查看日志
logs:
	python cli.py logs --lines 50

# 安装为可执行命令
install-cli:
	pip install -e .

# 构建分发包
build:
	python setup.py sdist bdist_wheel

# 上传到PyPI (需要配置凭据)
upload:
	twine upload dist/*

# 创建虚拟环境
venv:
	python -m venv venv
	@echo "激活虚拟环境: source venv/bin/activate"

# 导出依赖
freeze:
	pip freeze > requirements-freeze.txt

# 安全检查
security:
	safety check
	bandit -r src/

# 性能分析
profile:
	python -m cProfile -o profile.stats main.py --mode test
	python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"

# Docker相关 (如果有Docker支持)
docker-build:
	docker build -t backtrader-itick .

docker-run:
	docker run -v $(PWD)/config:/app/config -v $(PWD)/logs:/app/logs backtrader-itick

# 全面检查
check: lint test security
	@echo "所有检查完成"

# 准备发布
release: clean test lint build
	@echo "发布准备完成"