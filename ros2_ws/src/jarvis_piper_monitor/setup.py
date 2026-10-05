from setuptools import setup, find_packages

package_name = 'jarvis_piper_monitor'

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
    description='Live Terminal and Web Operator Dashboards for JARVIS PiPER Data Collection',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'terminal_dashboard = jarvis_piper_monitor.terminal_dashboard:main',
            'web_dashboard_node = jarvis_piper_monitor.web_dashboard_node:main',
        ],
    },
)
