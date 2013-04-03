from setuptools import setup, find_packages

def long_description(changelog_releases=10):
    import re
    import textwrap

    readme = open('README.rst').read()
    changes = ['Changes\n-------\n']
    version_line_re = re.compile('^\d\.\d+\.\d+\S*\s20\d\d-\d\d-\d\d')
    more_changes = False
    for line in open('CHANGES.txt'):
        if version_line_re.match(line):
            if changelog_releases == 0:
                more_changes = True
                break
            changelog_releases -= 1
        changes.append(line)

    if more_changes:
        changes.append(textwrap.dedent('''
            Older changes
            -------------
            See https://raw.github.com/mapproxy/renderd/master/CHANGES.txt
            '''))
    return readme + ''.join(changes)

setup(
    name='MapProxy-Renderd',
    version="1.6.0a",
    description='Background render daemon for MapProxy with priority queueing.',
    long_description=long_description(7),
    author='Oliver Tonnhofer',
    author_email='olt@omniscale.de',
    url='http://mapproxy.org',
    license='Apache Software License 2.0',
    packages=find_packages(),
    include_package_data=True,
    entry_points = {
        'console_scripts': [
            'mapproxy-renderd = mp_renderd.app:main',
        ],
    },
    install_requires=[
        'MapProxy',
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Internet :: Proxy Servers",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    zip_safe=False,
    test_suite='nose.collector',
)
