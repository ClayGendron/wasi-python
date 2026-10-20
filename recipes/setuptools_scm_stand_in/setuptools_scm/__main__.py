"""Print the Version: header of PKG-INFO in the current directory: meson runs this from the
source tree's top, where the sdist keeps it. Anything else stops the build in one line."""

from setuptools_scm import get_version

print(get_version("."))
