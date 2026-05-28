from setuptools import setup, find_packages

setup(
    name="scalper-bot",
    version="1.0.0",
    description="Intraday Scalping Trading Assistant for NSE/BSE via AngelOne SmartAPI",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "smartapi-python>=1.3.4",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "plotly>=5.15.0",
        "rich>=13.7.0",
        "python-dotenv>=1.0.0",
        "websocket-client>=1.6.0",
        "requests>=2.31.0",
        "pyotp>=2.9.0",
        "scipy>=1.11.0",
    ],
    entry_points={
        "console_scripts": ["scalper=main:main"],
    },
)
