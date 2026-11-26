from setuptools import find_packages, setup

package_name = 'route_follower'
setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ROB301 team',
    maintainer_email='rob301@example.com',
    description='D2 full route execution without localization',
    license='Proprietary',
    entry_points={'console_scripts': [
        'route_follower = route_follower.route_follower:main',
        'calibrate_colors = route_follower.colors:calibrate_main',
        'color_monitor = route_follower.colors:monitor_main',
    ]},
)
