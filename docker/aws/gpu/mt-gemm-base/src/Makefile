BLAS = CUBLAS
# default is OpenMP
ifeq ($(BLAS),CBLAS)
	CC = g++
	CFLAGS = -std=c++11 -O3 -DUSE_CBLAS
	# modify to suit your platform
	CFLAGS += -I../blis/install/include/blis
	LIBS = -L../blis/install/lib -lblis-mt
else ifeq ($(BLAS),MKL)
	CC = icpc
	CFLAGS = -std=c++11 -O3 -DUSE_MKL -mkl=parallel -qopenmp
else ifeq ($(BLAS),CUBLAS)
	CC = nvcc
	CFLAGS = --std c++11 -O3 -DUSE_CUBLAS -I$(CUDA_HOME)/include
	LIBS = -L$(CUDA_HOME)/lib64 -lcublas -lcudart
else ifeq ($(BLAS),HIPBLAS)
	CC = hipcc
	CFLAGS = -std=c++11 -O3 -DUSE_HIPBLAS
	LIBS = -L$(ROCM_PATH)/hipblas/lib -lhipblas
else
	CC = g++
	CFLAGS = -std=c++11 -O3 -fopenmp
endif

#uncomment if you want to enable MPI
CC = mpicc
CFLAGS += -DUSE_MPI

EXE = mt-dgemm.x

# PRECISION = [ 1 | 2 ]
# 1 is single-precision
# 2 is double-precision
# default is double-precision
ifeq ($(PRECISION),1)
	CFLAGS += -DPRECISION=1
	EXE = mt-sgemm.x
endif

$(EXE): mt-gemm.cpp Makefile
	$(CC) $(CFLAGS) -o $(EXE) mt-gemm.cpp $(LIBS)

clean:
	rm -f *.x

