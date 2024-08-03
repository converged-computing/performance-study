#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>

#define NGPUS_PER_NODE 4

#if (PRECISION==1)
#  define gemm_t float
#else
#  define gemm_t double
#endif

int mpi_thread=0;
int mpi_rank=0;
int mpi_size=1;
#ifdef USE_MPI
#include <mpi.h>
#define mprintf if( mpi_rank==0 ) printf
#else
#define mprintf printf
#endif

// ------------------------------------------------------- //
// Function: get_seconds
// ------------------------------------------------------- //
double get_seconds() {

#ifdef USE_MPI
  MPI_Barrier( MPI_COMM_WORLD );
#endif

  struct timeval now;
  gettimeofday(&now, NULL);

  const double seconds = (double) now.tv_sec;
  const double usec    = (double) now.tv_usec;

  return seconds + (usec * 1.0e-6);
}

#if defined( USE_MKL ) || defined (USE_CBLAS)
// ------------------------------------------------------- //
// CBLAS interface version
// ------------------------------------------------------- //
#ifdef USE_CBLAS
#  include "cblas.h"
#elif USE_MKL
#  include "mkl.h"
#endif



static inline double calc_gemm(int repeats, int N, gemm_t alpha, gemm_t beta, 
                             gemm_t *matrixA, gemm_t *matrixB, gemm_t *matrixC) {
  // Repeat multiple times
  const double start = get_seconds();
  for (int r = 0; r < repeats; r++) {
#if (PRECISION==1)
    cblas_sgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans,
                N, N, N, alpha, matrixA, N, matrixB, N, beta, matrixC, N);
#else
    cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans,
                N, N, N, alpha, matrixA, N, matrixB, N, beta, matrixC, N);
#endif
  }
  const double end = get_seconds();

  return(end - start);
}

#elif defined ( USE_CUBLAS ) || defined (USE_HIPBLAS)
// ------------------------------------------------------- //
// CUBLAS/HIPBLAS interface version
// ------------------------------------------------------- //
#ifdef USE_HIPBLAS
#  include <hip/hip_runtime.h>
#  include <hipblas.h>
#  define cudaDeviceSynchronize hipDeviceSynchronize
#  define cudaMalloc hipMalloc
#  define cudaFree hipFree
#  define cudaSuccess hipSuccess
#  define cudaError_t hipError_t
#  define cublasStatus_t hipblasStatus_t
#  define cublasHandle_t hipblasHandle_t
#  define cublasCreate hipblasCreate
#  define cublasSetMatrix hipblasSetMatrix
#  define cublasSetMatrix hipblasSetMatrix
#  define cublasGetMatrix hipblasGetMatrix
#  define cublasDgemm hipblasDgemm
#  define cublasSgemm hipblasSgemm
#  define cublasDestroy hipblasDestroy
#  define CUBLAS_STATUS_SUCCESS HIPBLAS_STATUS_SUCCESS
#  define CUBLAS_OP_N HIPBLAS_OP_N
#else
#  include <cuda_runtime.h>
#  include "cublas_v2.h"
#endif

static inline double calc_gemm(int repeats, int N, gemm_t alpha, gemm_t beta,
                             gemm_t *matrixA, gemm_t *matrixB, gemm_t *matrixC) {

  cudaError_t errorA, errorB, errorC;
  gemm_t *d_matrixA, *d_matrixB, *d_matrixC;
  errorA = cudaMalloc ((void**)&d_matrixA, N*N*sizeof(gemm_t));
  errorB = cudaMalloc ((void**)&d_matrixB, N*N*sizeof(gemm_t));
  errorC = cudaMalloc ((void**)&d_matrixC, N*N*sizeof(gemm_t));
  if(  (errorA != cudaSuccess) 
    || (errorB != cudaSuccess) 
    || (errorC != cudaSuccess) ) { 
    printf("ERROR: allocating device matrices\n"); 
    exit(1); 
  }

  cublasStatus_t status;
  cublasHandle_t handle;
  status = cublasCreate(&handle);
  if( status != CUBLAS_STATUS_SUCCESS ) { 
    printf("ERROR: creating a device handle\n"); 
    exit(1); 
  }

  cublasStatus_t statusA, statusB, statusC;
  statusA = cublasSetMatrix (N, N, sizeof(gemm_t), matrixA, N, d_matrixA, N);
  statusB = cublasSetMatrix (N, N, sizeof(gemm_t), matrixB, N, d_matrixB, N);
  statusC = cublasSetMatrix (N, N, sizeof(gemm_t), matrixC, N, d_matrixC, N);
  if(  (statusA != CUBLAS_STATUS_SUCCESS) 
    || (statusB != CUBLAS_STATUS_SUCCESS) 
    || (statusC != CUBLAS_STATUS_SUCCESS) ) { 
    printf("ERROR: intializing device matrices\n"); 
    exit(1); 
  }

  // Repeat multiple times
  const double start = get_seconds();
  for (int r = 0; r < repeats; r++) {
#if (PRECISION==1)
    cublasSgemm( handle, CUBLAS_OP_N, CUBLAS_OP_N, N, N, N,
                 &alpha, d_matrixA, N, d_matrixB, N, &beta, d_matrixC, N );
#else
    cublasDgemm( handle, CUBLAS_OP_N, CUBLAS_OP_N, N, N, N,
                 &alpha, d_matrixA, N, d_matrixB, N, &beta, d_matrixC, N );
#endif
  }
  cudaDeviceSynchronize();
  const double end = get_seconds();

  cublasGetMatrix(N, N, sizeof(gemm_t), d_matrixC, N, matrixC, N);
  cudaFree(d_matrixA);
  cudaFree(d_matrixB);
  cudaFree(d_matrixC);
  cublasDestroy(handle);

  return(end-start);
}

#else
// ------------------------------------------------------- //
// OpenMP version
// ------------------------------------------------------- //
static inline double calc_gemm(int repeats, int N, gemm_t alpha, gemm_t beta, 
                             gemm_t *matrixA, gemm_t *matrixB, gemm_t *matrixC) {
  // Repeat multiple times
  const double start = get_seconds();
  for (int r = 0; r < repeats; r++) {
    #pragma omp parallel for
    for (int i = 0; i < N; i++) {
      for (int j = 0; j < N; j++) {
        gemm_t sum = 0;
        for (int k = 0; k < N; k++)
          sum += matrixA[i*N + k] * matrixB[k*N + j];
        matrixC[i*N + j] = (alpha * sum) + (beta * matrixC[i*N + j]);
      }
    }
  }
  const double end = get_seconds();
  return(end - start);
}
#endif

// ------------------------------------------------------- //
// Function: main
// ------------------------------------------------------- //
int main(int argc, char* argv[]) {

  #ifdef USE_MPI
  MPI_Init_thread( &argc, &argv, MPI_THREAD_FUNNELED, &mpi_thread );
  MPI_Comm_size( MPI_COMM_WORLD, &mpi_size );
  MPI_Comm_rank( MPI_COMM_WORLD, &mpi_rank );
  #endif
 
  cudaSetDevice(mpi_rank % NGPUS_PER_NODE);
  int N = 256;
  int repeats = 30;

  gemm_t alpha = 1.0;
  gemm_t beta  = 1.0;

  // argv[1] is the matrix size
  if (argc > 1) {
    N = atoi(argv[1]);
    mprintf("Matrix size input by command line: %d\n", N);

    // argv[2] is the number of trials
    if (argc > 2) {
      repeats = atoi(argv[2]);
      mprintf("Repeat multiply %d times.\n", repeats);

      // argv[3] is alpha
      if (argc > 3) {
        alpha = (gemm_t) atof(argv[3]);

        // argv[4] is beta
        if (argc > 4) {
          beta = (gemm_t) atof(argv[4]);
        }
      }
    } else {
      mprintf("Repeat multiply defaulted to %d\n", repeats);
    }
  } else {
    mprintf("Matrix size defaulted to %d\n", N);
  }

  mprintf("Alpha =    %f\n", alpha);
  mprintf("Beta  =    %f\n", beta);

  mprintf("Allocating Matrices...\n");

  gemm_t* __restrict__ matrixA = (gemm_t*) malloc(sizeof(gemm_t) * N * N);
  gemm_t* __restrict__ matrixB = (gemm_t*) malloc(sizeof(gemm_t) * N * N);
  gemm_t* __restrict__ matrixC = (gemm_t*) malloc(sizeof(gemm_t) * N * N);

  mprintf("Allocation complete, populating with values...\n");

  #pragma omp parallel for
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      matrixA[i*N + j] = 2.0;
      matrixB[i*N + j] = 0.5;
      matrixC[i*N + j] = 1.0;
    }
  }

  mprintf("Performing multiplication...\n");

  const double time_taken = calc_gemm(repeats, N, alpha, beta, matrixA, matrixB, matrixC);

  mprintf("Calculating matrix check...\n");

  double final_sum = 0;
  long long int count     = 0;
  #pragma omp parallel for reduction(+:final_sum, count)
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      final_sum += matrixC[i*N + j];
      count++;
    }
  }

  // Print results
  mprintf("\n");
  mprintf("===============================================================\n");

  double N_dbl = (double) N;
  double matrix_memory = (3 * N_dbl * N_dbl) * ((double) sizeof(gemm_t));
  const double count_dbl = (double) count;
  const double scaled_result = (final_sum / (count_dbl * repeats));

  mprintf("Final Sum is:         %f\n", scaled_result);

  const double check_sum = N_dbl + (1.0 / (double) (repeats));
  const double allowed_margin = 1.0e-8;

  if ( (check_sum >= (scaled_result - allowed_margin)) &&
       (check_sum <= (scaled_result + allowed_margin)) ) {
    mprintf(" -> Solution check PASSED successfully.\n");
  } else {
    mprintf(" -> Solution check FAILED.\n");
  }

  mprintf("Memory for Matrices:  %f MB\n", (matrix_memory / (1024 * 1024)));

  mprintf("Multiply time:        %f seconds\n", time_taken);

  const double flops_computed = ( (N_dbl * N_dbl * N_dbl * 2.0 * (double)(repeats)) +
				  (N_dbl * N_dbl * 3 * (double)(repeats)) ) * (double)(mpi_size);

  //mprintf("FLOPs computed:       %f\n", flops_computed);
  mprintf("GFLOP/s rate:         %f GF/s\n", (flops_computed / time_taken) / 1.0e9);

  mprintf("===============================================================\n");
  mprintf("\n");

  free(matrixA);
  free(matrixB);
  free(matrixC);

  #ifdef USE_MPI
  MPI_Finalize();
  #endif
  
  return 0;
}
