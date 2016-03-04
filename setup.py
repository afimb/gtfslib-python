"""
@author: Laurent GREGOIRE <laurent.gregoire@mecatran.com>
"""

from setuptools import setup, find_packages
import gtfslib


setup(
    name='gtfslib',
    version=gtfslib.__version__,
    description="GTFS database library",
    long_description="An open source library for reading, databasing, querying and manipulating GTFS-based transit data",
    url='https://github.com/afimb/gtfslib-python',
    author='AFIMB / CEREMA / MECATRAN',
    author_email='laurent.gregoire@mecatran.com',
    license='GPLv3',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: GIS',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3'
    ],
    keywords='GTFS transit',
    packages=find_packages(),
    install_requires=['sqlalchemy', 'six', 'docopt', 'requests', 'pyqtree', 'pyshp'],
    extras_require={
        'dev': ['check-manifest'],
        'test': ['coverage'],
    },
    entry_points={
        'console_scripts': [
            'gtfsdbloader=gtfslib.gtfsdbloader:main',
            'gtfsrun=gtfsplugins.gtfsrun:main'
        ],
    },
)
