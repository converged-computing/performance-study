##
## Copyright (c) 2016, Lawrence Livermore National Security, LLC.
##
## Produced at the Lawrence Livermore National Laboratory.
##
## All rights reserved.
##
##

set(RAJA_COMPILER "RAJA_COMPILER_GNU" CACHE STRING "")
set(RAJA_HOST_CONFIG_LOADED On CACHE Bool "")

set(CMAKE_C_COMPILER   "gcc" CACHE PATH "")
set(CMAKE_CXX_COMPILER "g++" CACHE PATH "")
set(CMAKE_LINKER       "g++" CACHE PATH "")

set(CMAKE_CXX_FLAGS "" CACHE STRING "")
set(CMAKE_CXX_FLAGS_RELEASE "-O3" CACHE STRING "")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O3 -g" CACHE STRING "")
set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g" CACHE STRING "")

set(ENABLE_OPENMP Off CACHE BOOL "")
set(ENABLE_CHAI On CACHE BOOL "")
set(ENABLE_MPI On CACHE BOOL "")
set(ENABLE_MPI_WRAPPER Off CACHE BOOL "")

set(RAJA_HOST_CONFIG_LOADED On CACHE Bool "")
set(CMAKE_BUILD_TYPE "Release" CACHE STRING "")
set(CMAKE_EXE_LINKER_FLAGS "-lstdc++ -pthread" CACHE STRING "")
