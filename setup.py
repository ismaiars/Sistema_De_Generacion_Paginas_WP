#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Generación de Páginas y Tarjetas de Productos
Configuración del proyecto para distribución e instalación
"""

from setuptools import setup, find_packages
import os

# Leer el archivo README para la descripción larga
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Leer requirements.txt para las dependencias
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="sistema-generacion-paginas-wp",
    version="2.0.0",
    author="Ópticas Kairoz - Equipo de Desarrollo",
    author_email="desarrollo@opticaskairoz.com.mx",
    description="Sistema completo para generación masiva de páginas y tarjetas de productos para WordPress",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/opticaskairoz/sistema-generacion-paginas",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Office/Business :: Financial :: Point-Of-Sale",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Win32 (MS Windows)",
        "Natural Language :: Spanish",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "generador-paginas=programa_2:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.html", "*.txt", "*.md"],
    },
    keywords=[
        "wordpress", "ecommerce", "product-pages", "html-generator", 
        "catalog", "optics", "eyewear", "automation", "web-development"
    ],
    project_urls={
        "Bug Reports": "https://github.com/opticaskairoz/sistema-generacion-paginas/issues",
        "Source": "https://github.com/opticaskairoz/sistema-generacion-paginas",
        "Documentation": "https://github.com/opticaskairoz/sistema-generacion-paginas/wiki",
        "Company": "https://opticaskairoz.com.mx",
    },
)