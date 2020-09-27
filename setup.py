from os import path
from setuptools import setup, find_packages


with open(path.join(path.abspath(path.dirname(__file__)), "README.md")) as f:
    long_description = f.read()


setup(
    name="lnch-vekslak",
    version="0.2.0",
    url="https://github.com/Kixunil/lnch-vekslak",
    author="Martin Habovstiak",
    author_email="martin.habovstiak@gmail.com",
    maintainer="Martin Habovstiak",
    maintainer_email="martin.habovstiak@gmail.com",
    license="MIT",
    description="A tool for selling Lightning channels on the street",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="bitcoin lightning-network lnurl",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Utilities",
    ],
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.7",
    install_requires=["toml", "bottle"],
    extras_require={ "eclair": ["pyhocon"] },
    entry_points={
        "console_scripts": [ "lnch-vekslak = lnch_vekslak:main" ],
    },
    zip_safe=False,
)
