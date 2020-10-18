from setuptools import setup, find_packages

setup(
    name="xmaintnote",
    version="0.0.2rc1",
    packages=find_packages(),
    install_requires=[
        'icalendar>=4.0.7',
        'jira>=2.0.0'
    ],
)
