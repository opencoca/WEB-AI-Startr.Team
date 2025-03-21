from setuptools import setup, find_packages

setup(
    name="strteam",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "pyyaml",
        # Add other dependencies
    ],
    description="An AI-powered software development framework",
    author="Startr.LLC & CAMEL-AI.org",
    author_email="info@startr.cloud",
    url="https://github.com/startr-team/WEB-AI-strteam",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    include_package_data=True,
)