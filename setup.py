from setuptools import setup, find_packages

setup(
    name="anki_drive",
    version="0.1.0",
    description="Custom racecontroller voor Anki Overdrive met webinterface",
    author="Jouw Naam",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Flask>=2.2",
        "bleak>=0.20",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "anki-run = anki_drive.cli.run:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
