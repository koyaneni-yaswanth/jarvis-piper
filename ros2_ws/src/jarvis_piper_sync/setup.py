from setuptools import setup, find_packages

package_name = 'jarvis_piper_sync'

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
    description='High-precision multi-modal time synchronizer for PIKA PiPER data collection',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'time_synchronizer_node = jarvis_piper_sync.time_synchronizer_node:main',
        ],
    },
)
