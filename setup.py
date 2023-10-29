from setuptools import setup, find_packages

setup(
   name='gradys',
   version='0.1.0',
   description='A framework for implementing distributed algorithms in a simulated network environment',
   keywords='network distributed algorithm simulation gradys LAC PUC drone sensor',
   author='Thiago de Souza Lamenza',
   url='https://github.com/Thlamz/GrADyS-SIM-TNG',
   project_urls={
       'Documentation': 'https://thlamz.github.io/gradys-sim-tng/'
   },
   author_email='thlamenza@hotmail.com',
   license='MIT',
   packages=find_packages(),
   install_requires=[
      'matplotlib>=3'
   ],
   python_requires='>=3.8',
)