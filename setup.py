from setuptools import setup, find_packages

setup(
    name="xmaintnote",
    version="0.0.2_rc1",
    packages=find_packages(),
    install_requires=[
        'icalendar>=3.0',
    ],
)
