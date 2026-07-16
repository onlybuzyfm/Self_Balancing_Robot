cmake_minimum_required(VERSION 3.8)
project(tumbller_gazebo)

find_package(ament_cmake REQUIRED)

install(DIRECTORY
  config
  launch
  models
  worlds
  DESTINATION share/${PROJECT_NAME}
)

install(PROGRAMS
  scripts/moe_balance_controller.py
  scripts/balance_controller.py
  scripts/balance_observer.py
  scripts/balance_csv_logger.py
  scripts/reset_simulation.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()