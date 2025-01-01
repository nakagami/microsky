from setuptools import setup

setup(name='microsky',
      version=__import__('microsky').__version__,
      description='Simple bsky.app client',
      long_description=open('README.rst').read(),
      keywords=['Bluesky'],
      url='https://github.com/nakagami/microsky',
      author='Hajime Nakagami',
      author_email='nakagami@gmail.com',
      license='MIT',
      py_modules=['microsky'])
