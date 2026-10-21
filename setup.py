from setuptools import find_packages, setup

from ghost import __version__ as version

setup(
	name="ghost",
	version=version,
	description="Guest User Identity Management",
	author="Muneeb Mohammed",
	author_email="muneebmohammed141@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=[],
)
