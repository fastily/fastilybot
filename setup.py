import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="fastilybot",
    version="2.2.0",
    author="Fastily",
    author_email="fastily@users.noreply.github.com",
    description="Fastily's Wikipedia Bots",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fastily/fastilybot",
    project_urls={
        "Bug Tracker": "https://github.com/fastily/fastilybot/issues",
    },
    include_package_data=True,
    packages=setuptools.find_packages(include=["fastilybot"]),
    install_requires=['pwiki', 'rich'],
    entry_points={
        'console_scripts': [
            'fastilybot = fastilybot.__main__:_main'
        ]
    },
    classifiers=[
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.11',
)
