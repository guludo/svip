import setuptools

setuptools.setup(
    name='svip',
    version='0.0.1',
    packages=['svip'],
    install_requires=[
        'semantic_version~=2.8',
    ],
    extras_require={
        'tests': [
            'pytest~=6.2',
            'coverage~=5.5',
        ],
    },
)
