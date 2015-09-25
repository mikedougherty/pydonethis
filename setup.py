import os.path
from setuptools import setup, find_packages

ROOT_DIR = os.path.dirname(__file__)

import pydonethis

def requirements_deps():
    with open(os.path.join(ROOT_DIR, 'requirements.txt')) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield line

def main():
    setup(
        name='pydonethis',
        version=pydonethis.VERSION,
        description="CLI client for idonethis.com",
        url="https://github.com/mikedougherty/pydonethis",
        install_requires=list(requirements_deps()),
        include_package_data=True,
        packages=find_packages(),
        entry_points=dict(
            console_scripts=[
                'pydonethis = pydonethis.app:main',
            ]
        )
    )


if __name__ == '__main__':
    main()
