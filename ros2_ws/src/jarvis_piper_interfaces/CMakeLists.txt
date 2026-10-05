cmake_minimum_required(VERSION 3.12)
project(jarvis_piper_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(trajectory_msgs REQUIRED)

set(msg_files
  "msg/EpisodeMetadata.msg"
  "msg/SynchronizedFrame.msg"
  "msg/PikaTeleopStatus.msg"
  "msg/QualityAuditResult.msg"
  "msg/RecorderStatus.msg"
)

set(srv_files
  "srv/StartEpisode.srv"
  "srv/StopEpisode.srv"
  "srv/DiscardEpisode.srv"
  "srv/GetRecorderStatus.srv"
  "srv/ExportDataset.srv"
)

rosidl_generate_interfaces(${PROJECT_NAME}
  ${msg_files}
  ${srv_files}
  DEPENDENCIES
    builtin_interfaces
    sensor_msgs
    geometry_msgs
    trajectory_msgs
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
