"""
Setup configuration for the project.
Allows the package to be installed in development mode.
"""

from setuptools import setup, find_packages

setup(
    name="veryfi-invoice-extractor",
    version="1.0.0",
    description="Extract structured invoice data using Veryfi OCR API",
    author="Data Annotations Engineer Candidate",
    packages=find_packages(),
    install_requires=[
        "veryfi>=0.1.8",
        "pandas>=2.0.0",
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0",
        "python-dotenv>=1.0.0",
        "regex>=2023.10.3",
    ],
    python_requires=">=3.8",
)

