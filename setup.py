from setuptools import setup

setup(
    name="python-imodb",
    version="0.1.0",
    author="Alexander Ryzhov",
    author_email="aryzhov07@gmail.com",
    description=("IMODB - In-Memory Object Database"),
    license="MIT",
    keywords="python memory object database",
    url="https://github.com/aryzhov/python-imodb",
    packages=["imodb"],
    package_dir={"imodb": "src/imodb"},
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    long_description="GitHub: https://github.com/aryzhov/python-imodb",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
)
