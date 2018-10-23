from setuptools import setup, find_packages
import os
from os import path

script_dir = os.path.dirname(os.path.realpath(__file__))

from dsportal import __version__ as version

packages = list()
links = list()
with open(path.join(script_dir, "requirements.txt")) as f:
    for line in f:
        if line.startswith("#"):
            continue
        if "#egg" in line:
            links.append(line)
            packagespec = line.split("#egg=")[1].replace("-", "==")
            packages.append(packagespec)
        else:
            packages.append(line)

data_files = list()

module_dir = path.join(script_dir, "dsportal")
for root, subdirs, filenames in os.walk(module_dir):
    data_files += [path.join(root, filename) for filename in filenames]

print(data_files)

setup(
    name="dsportal",
    version=version,
    packages=find_packages(),
    dependency_links=links,
    entry_points={
        "console_scripts": [
            "dsportal-server = dsportal.server:main",
            "dsportal-worker = dsportal.worker:main",
            "dsportal-screenshots = dsportal.screenshots:main",
        ]
    },
    install_requires=packages,
    package_data={"": data_files},
    author="Callan Bryant",
    author_email="callan.bryant@gmail.com",
    maintainer="Callan Bryant",
    maintainer_email="callan.bryant@gmail.com",
    description="Monitoring portal",
    license="MIT",
    keywords="discourse",
    url="https://callanbryant.co.uk/",
)
