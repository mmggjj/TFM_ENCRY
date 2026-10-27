cmake_minimum_required(VERSION 3.16)
# El acceso al motor por I2C es un componente compartido con el medidor.
set(EXTRA_COMPONENT_DIRS ../componentes)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(verificador)
