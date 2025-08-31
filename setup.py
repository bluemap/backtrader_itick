"""
港美股量化交易通知系统安装配置
"""

from setuptools import setup, find_packages
import os


def read_requirements():
    """读取requirements.txt文件"""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            requirements = []
            for line in f:
                line = line.strip()
                # 跳过注释和空行
                if line and not line.startswith('#'):
                    requirements.append(line)
            return requirements
    return []


def read_readme():
    """读取README文件"""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "港美股量化交易通知系统"


setup(
    name="backtrader-itick",
    version="1.0.0",
    author="量化交易团队",
    author_email="quant@example.com",
    description="基于iTick和Backtrader的港美股量化交易信号生成和通知系统",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/backtrader-itick",
    
    # 包信息
    packages=find_packages(),
    include_package_data=True,
    
    # Python版本要求
    python_requires=">=3.8",
    
    # 依赖包
    install_requires=read_requirements(),
    
    # 额外依赖组
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'flake8>=5.0.0',
            'black>=22.0.0',
            'mypy>=0.991',
        ],
        'visualization': [
            'plotly>=5.10.0',
            'dash>=2.6.0',
            'dash-bootstrap-components>=1.2.0',
        ],
        'jupyter': [
            'jupyter>=1.0.0',
            'ipykernel>=6.15.0',
            'ipywidgets>=8.0.0',
        ],
        'database': [
            'sqlalchemy>=1.4.0',
            'pymysql>=1.0.0',
            'psycopg2-binary>=2.9.0',
        ],
        'performance': [
            'numba>=0.56.0',
            'cython>=0.29.0',
        ]
    },
    
    # 命令行工具
    entry_points={
        'console_scripts': [
            'quant-trading=main:main',
            'qt-cli=cli:cli',
        ],
    },
    
    # 分类信息
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    
    # 关键词
    keywords=[
        "quantitative trading",
        "algorithmic trading", 
        "backtrader",
        "itick",
        "stock trading",
        "financial analysis",
        "trading signals",
        "notification system"
    ],
    
    # 许可证
    license="MIT",
    
    # 项目URLs
    project_urls={
        "Bug Reports": "https://github.com/your-org/backtrader-itick/issues",
        "Source": "https://github.com/your-org/backtrader-itick",
        "Documentation": "https://backtrader-itick.readthedocs.io/",
    },
    
    # 包数据
    package_data={
        'config': ['*.yaml', '*.yml'],
        'data': ['*.csv'],
        'docs': ['*.md', '*.rst'],
    },
    
    # 数据文件
    data_files=[
        ('config', ['config/config.yaml']),
        ('data', ['data/sample_stock_pool.csv']),
    ],
    
    # ZIP安全
    zip_safe=False,
)