##
## Copyright (c) 2016, Lawrence Livermore National Security, LLC.
##
## Produced at the Lawrence Livermore National Laboratory.
##
## All rights reserved.
##
##

set(CMAKE_CUDA_ARCHITECTURES "70" CACHE STRING "")
set(CUDA_ARCH "sm_70" CACHE STRING "")
set(RAJA_COMPILER "RAJA_COMPILER_GNU" CACHE STRING "")
set(RAJA_HOST_CONFIG_LOADED On CACHE Bool "")
set(RAJA_ENABLE_CUDA On CACHE Bool "")
set(USE_CUDA 1 CACHE BOOL "")
set(CUDA_INSTALL_PATH "/usr/local/cuda/" CACHE STRING "")
#set(SAMPLER_PATH "/usr/WS2/variorum/gpu-benchmarking/tools/nvml-nvcd-sampler/" CACHE STRING "")

set(CMAKE_C_COMPILER   "/usr/bin/gcc" CACHE PATH "")
set(CMAKE_CXX_COMPILER "/usr/bin/g++" CACHE PATH "")
set(CMAKE_LINKER       "/usr/bin/g++" CACHE PATH "")

set(CMAKE_CUDA_C_COMPILER   "/usr/bin/gcc" CACHE PATH "")
set(CMAKE_CUDA_CXX_COMPILER "/usr/bin/g++" CACHE PATH "")

set(CMAKE_CXX_FLAGS "-I$(CUDA_INSTALL_PATH)/include" CACHE STRING "")
set(CMAKE_CXX_FLAGS_RELEASE "-I$(CUDA_INSTALL_PATH)/include -O3 " CACHE STRING "")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-I$(CUDA_INSTALL_PATH)/include -O3" CACHE STRING "")
set(CMAKE_CXX_FLAGS_DEBUG "-I$(CUDA_INSTALL_PATH)/include -O0" CACHE STRING "")

set(CMAKE_C_FLAGS "-I$(CUDA_INSTALL_PATH)/include" CACHE STRING "")
set(CMAKE_C_FLAGS_RELEASE "-I$(CUDA_INSTALL_PATH)/include -O3 " CACHE STRING "")
set(CMAKE_C_FLAGS_RELWITHDEBINFO "-I$(CUDA_INSTALL_PATH)/include -O3" CACHE STRING "")
set(CMAKE_C_FLAGS_DEBUG "-I$(CUDA_INSTALL_PATH)/include -O0" CACHE STRING "")

set(ENABLE_MPI On CACHE BOOL "")
set(ENABLE_CHAI On CACHE BOOL "")
set(ENABLE_CUDA On CACHE BOOL "")
set(ENABLE_OPENMP Off CACHE BOOL "")
set(ENABLE_MPI_WRAPPER Off CACHE BOOL "")

set(CMAKE_BUILD_TYPE "Release" CACHE STRING "")

set(CMAKE_CUDA_FLAGS "-restrict -gencode=arch=compute_70,code=sm_70 -I$(CUDA_INSTALL_PATH)/include" CACHE STRING "")
set(CMAKE_CUDA_FLAGS_RELEASE "-O3 --expt-extended-lambda -Xcompiler -std=c++14" CACHE STRING "")
set(CMAKE_CUDA_FLAGS_RELWITHDEBINFO "-O3 -lineinfo --expt-extended-lambda -Xcompiler -std=c++14" CACHE STRING "")
set(CMAKE_CUDA_FLAGS_DEBUG "-O0 -G --expt-extended-lambda -Xcompiler -std=c++14" CACHE STRING "")
set(CMAKE_CUDA_HOST_COMPILER "${CMAKE_CUDA_CXX_COMPILER}" CACHE STRING "")


set(CMAKE_EXE_LINKER_FLAGS " -L$(CUDA_INSTALL_PATH)/lib64 -lnvidia-ml -ldl -lstdc++ -pthread" CACHE STRING "")
