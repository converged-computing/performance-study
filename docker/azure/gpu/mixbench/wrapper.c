#include <unistd.h>
#include <sys/types.h>
#include <errno.h>
#include <stdio.h>
#include <sys/wait.h>
#include <stdlib.h>
#include <mpi.h>

int global; /* In BSS segement, will automatically be assigned '0'*/

int main(int argc, char *argv[])
{
    pid_t child_pid;
    int status;
    int local = 0;
    char load_val[10] ="";

    int inputsize=atoi(argv[1]);

    int devid = 0;
    int c2 = fork();
    if(c2 > 0) {
        int c3 = fork();
        if(c3 > 0) {
            int c4 = fork();
            if(c4 > 0) {
                int c5 = fork();
                if(c5 > 0) {
                    int c6 = fork();
                    if(c6 > 0) {
                        int c7 = fork();
                        if(c7 > 0) {
                            int c8 = fork();
                            if(c8 > 0) {
                                devid=7;
                            }
                            else {
                                devid=6;
                            }
                        }
                        else {
                            devid=5;
                        }
                    }
                    else {
                        devid=4;
                    }
                }
                else {
                    devid=3;
                }
            } else {
                devid=2;
            }
        } else {
            devid=1;
        }
    } else {
        devid=0;
    }

    char launchstr[2048];
    sprintf(launchstr, "CUDA_VISIBLE_DEVICES=%d mixbench-cuda %d", devid, inputsize);
    system(launchstr);
}
