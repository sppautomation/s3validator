import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="vsnap",
    version="0.0.1",
    author="Punita Repe",
    author_email="prepe@catalogicsoftware.com",
    description="Vsnap client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="gitrepo2.ad.catalogic.us",
    packages=setuptools.find_packages(),
    install_requires = ['requests'],
    classifiers=(
        "Programming Language :: Python :: 3.4",
        "Operating System :: OS Independent"
    ),
)
