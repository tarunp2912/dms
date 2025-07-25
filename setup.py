from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in dms/__init__.py
from dms import __version__ as version

print("📦 DMS setup.py running — installing:", install_requires)

setup(
	name="dms",
	version=version,
	description="An easy to use, document sharing and management solution.",
	author="Frappe Technologies Pvt. Ltd.",
	author_email="hello@frappe.io",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
