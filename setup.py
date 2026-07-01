from pathlib import Path

from setuptools import find_packages, setup


VERSION = "1.0.0"
DESCRIPTION = "Python library for interacting with Zalo."


this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")


setup(
    name="zjr_api",
    version=VERSION,
    author="Lâm Minh Phú (PhuDev)",
    author_email="zbllf2lollpll@gmail.com",
    author_facebook="https://facebook.com/phudev2010",
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/PhuDev-2010/zjr_api",
    project_urls={
        "Homepage": "https://github.com/PhuDev-2010/zjr_api",
        "Documentation": "https://github.com/PhuDev-2010/zjr_api",
        "Source": "https://github.com/PhuDev-2010/zjr_api",
        "Issues": "https://github.com/PhuDev-2010/zjr_api/issues",
    },
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "requests",
        "aiohttp",
        "aenum",
        "attrs",
        "pycryptodome",
        "munch",
        "websockets",
    ],
    keywords=[
        "python",
        "zalo",
        "api",
        "zalo api",
        "chatbot",
        "zalo bot",
        "automation",
        "messaging",
        "zjr_api",
        "phudev",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Communications :: Chat",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)