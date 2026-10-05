from setuptools import setup, find_packages

package_name = 'jarvis_piper_tools'

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
    description='Developer and debugging tools for JARVIS PiPER: mock streamer, visualizer, inspector',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'pika_piper_mock_streamer = jarvis_piper_tools.pika_piper_mock_streamer:main',
            'episode_visualizer = jarvis_piper_tools.episode_visualizer:main',
            'dataset_inspector = jarvis_piper_tools.dataset_inspector:main',
        ],
    },
)
