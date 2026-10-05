from setuptools import setup, find_packages

package_name = 'jarvis_piper_world_model'

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
    description='Spatial forward kinematics, phase segmentation, and transition builders for JARVIS PiPER',
    license='Apache-2.0',
)
