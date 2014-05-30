import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
readme = os.path.join(here, 'README.md')

requires = [
    'pymongo>=2.7.0',
]
testing_extras = []

setup(
    name='minimongo',
    version='0.1',
    description="Small MongoDB object layer.",
    long_description=open(readme).read(),
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
    url='https://github.com/WiFast/minimongo',
    license='BSD-derived',
    zip_safe=False,
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=requires,
    tests_require=requires + testing_extras,
    entry_points="",
)
