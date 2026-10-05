from setuptools import setup, find_packages

package_name = 'jarvis_piper_dataset'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Yash',
    maintainer_email='recvn@example.com',
    description='Universal dataset exporters for JARVIS PiPER: LeRobot 2.0, ALOHA HDF5, RLDS, and World Model',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'export_pipeline = jarvis_piper_dataset.export_pipeline:main',
        ],
    },
)
