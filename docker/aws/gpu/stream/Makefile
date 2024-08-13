CC = g++
ARCH=sm_70

stream : stream.cu Makefile
	nvcc -O3 -DSTREAM_ARRAY_SIZE=80000000 -DNTIMES=20 -std=c++11 -ccbin=$(CC) stream.cu -arch=$(ARCH) -o stream 

.PHONY: clean
clean :
	rm -f stream
