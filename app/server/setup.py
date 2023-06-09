from setuptools import find_packages, setup

name = "pr1_server"


setup(
  name="pr1_server",
  version="0.0.0",

  packages=find_packages(),

  entry_points={
    "console_scripts": [
      "pr1=pr1_server:main"
    ]
  },

  install_requires=[
    "aiohttp==3.7.4",
    "bcrypt==3.2.2",
    "pyOpenSSL==23.0.0",
    "websockets==10.2",
    "zeroconf==0.47.1"
  ]
)
