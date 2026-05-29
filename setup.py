from setuptools import setup, find_packages

setup(
    name="yftickers",
    version="0.1.0",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    package_data={
        "yftickers": ["data/*.json"],
    },
    install_requires=[
        "pandas>=2.0.0",
        "requests>=2.30.0",
        "lxml>=4.9.0",
    ],
    author="Armin",
    description="A unified, optimized library for retrieving stock tickers in Yahoo Finance format with dynamic parallel scraping and offline caching.",
    long_description=open("README.md", encoding="utf-8").read() if open("README.md") else "",
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
