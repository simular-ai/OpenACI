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
        'requests==2.28.1',
        'openai==0.27.0',
        'pyautogui==0.9.53',
        'pyqt6==6.3.1',
        'Pillow==9.2.0',
        'pyobjc==8.5',
        'backoff==2.1.2',
        'xlm==0.3.1',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS',
    ],
    python_requires='>=3.9',  # Specify the minimum Python version required
)
