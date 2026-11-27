from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'lab_3'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ubuntu',
    maintainer_email='joshuacurtis.brown@mail.utoronto.ca',
    description='ROB301 Lab 3: EKF localization from a landmark bearing',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'localizer = lab_3.localizer:main',
            'noisy_vel_publisher = lab_3.noisy_vel_publisher:main',
            'scan_angle_publisher = lab_3.scan_angle_publisher:main',
            'plot_kf_log = lab_3.plot_kf_log:main',
            'live_plot = lab_3.live_plot:main',
        ],
    },
)
