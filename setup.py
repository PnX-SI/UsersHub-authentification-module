import setuptools
from pathlib import Path


root_dir = Path(__file__).absolute().parent
with (root_dir / 'VERSION').open() as f:
    version = f.read()
with (root_dir / 'README.md').open() as f:
    long_description = f.read()



setuptools.setup(
    name='pypnusershub',
    version=version,
    description="Python lib to authenticate using PN's UsersHub",
    long_description=long_description,
    long_description_content_type='text/markdown',
    maintainer='Parcs nationaux des Écrins et des Cévennes',
    maintainer_email='geonature@ecrins-parcnational.fr',
    url='https://github.com/PnX-SI/UsersHub-authentification-module',
    packages=setuptools.find_packages('src'),
    package_dir={'': 'src'},
    package_data={'pypnusershub.migrations': ['data/*.sql']},
    install_requires=(
        list(open("requirements-common.in", "r"))
        + list(open("requirements-dependencies.in", "r"))
    ),
    extras_require={
        'tests': [ 'pytest', 'pytest-flask', ],
    },
    entry_points={
        'alembic': [
            'migrations = pypnusershub.migrations:versions',
        ],
    },
    classifiers=['Development Status :: 1 - Planning',
                 'Intended Audience :: Developers',
                 'Natural Language :: English',
                 'Programming Language :: Python :: 3',
                 'Programming Language :: Python :: 3.4',
                 'Programming Language :: Python :: 3.5',
                 'Programming Language :: Python :: 3.6',
                 'Programming Language :: Python :: 3.7',
                 'Programming Language :: Python :: 3.8',
                 'License :: OSI Approved :: GNU Affero General Public License v3',
                 'Operating System :: OS Independent'],
)
