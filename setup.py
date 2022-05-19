import setuptools

with open('README.md', 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name='vapordmods',
    version='0.1.2',
    author='FireFollet',
    author_email='',
    description='Manage multiples mods provider like Thunderstore, Nexismods and Steam Workshop.',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/FireFollet/vapordmods",
    project_urls={
        "Bug Tracker": "https://github.com/FireFollet/vapordmods/issues",
    },
    package_dir={"": "src"},
    install_requires=['PyYAML~=6.0',
                      'aiohttp~=3.8.1',
                      'aiofiles~=0.8.0',
                      'pandas~=1.4.2',
                      'cerberus~=1.3.4'],
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.8",
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)
