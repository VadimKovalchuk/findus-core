from setuptools import find_packages, setup

setup(
    name='findus-edge',
    packages=find_packages(
        include=['findus-edge']
    ),
    install_requires=[
        'finvizfinance=={{ finvizfinance_version }}',
         'yfinance=={{ yfinance_version }}'
    ],
    version='0.0.1',
    description='Findus edge toolset',
    author='Vadym Kovalchuk',
    license='MIT',
)
