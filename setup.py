from setuptools import setup, find_packages

setup(
    name='openaci',
    version='0.1.0',
    description='Abstraction platform for developing open source GUI agents',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Simular',
    packages=find_packages(),  # Automatically find packages in the current directory
    include_package_data=True,
    install_requires=[
        'xlm',
        'requests',
        'openai',
        'pyautogui',
        'pyqt6',
        'Pillow',
        'pyobjc'
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: Apache License 2.0',
        'Operating System :: MacOS',
    ],
    python_requires='>=3.9',  # Specify the minimum Python version required
)