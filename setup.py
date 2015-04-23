import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

try:
    readme = open(os.path.join(here, 'README.md')).read()
except IOError:
    readme = ''

install_requires = [
    'pymongo>=2.7.0',
]
setup_requires = [
    'coverage>=3.7.0',
    'nose>=1.3.0',
]

setup(
    name='bearfield',
    version='1.9.1',
    description="Small MongoDB object layer.",
    long_description=readme,
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: BSD License",
        "Topic :: Database",
    ],
    keywords='python mongodb',
    author='WiFast',
    author_email='rgb@wifast.com',
    url='https://github.com/WiFast/bearfield',
    license='BSD-derived',
    zip_safe=False,
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=install_requires,
    setup_requires=setup_requires,
    test_suite = 'nose.collector',
    entry_points='',
)
