from setuptools import setup, find_packages

setup(
    name="cortex-protocol",
    version="0.5.1",
    description="Cortex Protocol — Sovereignty Abstraction Layer for Human-AI Interaction",
    license="GPL-3.0",
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "numpy>=1.24,<3.0",
        "scipy>=1.11,<2.0",
        "cryptography>=41.0,<44.0",
    ],
)
