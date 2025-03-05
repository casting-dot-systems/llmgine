from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="llmgine",
    version="0.1.0",
    author="LLMgine Team",
    author_email="your.email@example.com",
    description="A framework for building LLM-powered applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/llmgine",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.25.0",
        "jsonschema>=3.2.0",
    ],
    entry_points={
        "console_scripts": [
            "llmgine=llmgine.__main__:main",
        ],
    },
)
