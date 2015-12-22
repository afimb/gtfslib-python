"""
@author: Laurent GRÉGOIRE <laurent.gregoire@mecatran.com>
"""

from setuptools import setup, find_packages


setup(
    name='gtfslib',
    version='0.1.0',
    description="A sample Python project",
    long_description="An open source library for reading, querying and manipulating GTFS-based transit data",
    url='https://github.com/afimb/gtfslib-python',
    author='AFIMB / CEREMA / MECATRAN',
    author_email='laurent.gregoire@mecatran.com',
    license='TODO',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: GIS',
        # 'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3'
    ],
    keywords='GTFS transit',
    packages=find_packages(),
    install_requires=['sqlalchemy', 'six', 'docopt'],
    extras_require={
        'dev': ['check-manifest'],
        'test': ['coverage'],
    },
    entry_points={
        'console_scripts': [
            'gtfsdbloader=gtfslib.gtfsdbloader:main',
        ],
    },
)