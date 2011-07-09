from setuptools import setup, find_packages

version = '1.0.1'

long_description = (file('README.rst').read() +
    '\n\n' + file('HISTORY.txt').read())


setup(name='TermEmulator',
      version=version,
      description="Emulator for V100 terminal programs",
      long_description=long_description,
      author="Siva Chandran P",
      author_email="siva.chandran.p@gmail.com",
      url="https://github.com/sivachandran/TermEmulator",
      license="LGPL",
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          'setuptools',
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
