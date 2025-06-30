// 1. DATA SOURCE (Nested by Application)
const allApplicationsData = {
    "LAMMPS": [
        { "experiment": "azure/cyclecloud/gpu", "size": 4, "iterations": 5, "duration": 400.0, "cost": 9.791111 }, { "experiment": "azure/aks/gpu", "size": 4, "iterations": 5, "duration": 450.267913, "cost": 11.021558 }, { "experiment": "azure/cyclecloud/gpu", "size": 8, "iterations": 5, "duration": 242.0, "cost": 11.847244 }, { "experiment": "azure/aks/gpu", "size": 8, "iterations": 5, "duration": 251.584306, "cost": 12.316449 }, { "experiment": "azure/cyclecloud/gpu", "size": 16, "iterations": 5, "duration": 148.0, "cost": 14.490844 }, { "experiment": "azure/aks/gpu", "size": 16, "iterations": 5, "duration": 153.921434, "cost": 15.070619 }, { "experiment": "google/compute-engine/cpu", "size": 64, "iterations": 5, "duration": 169.354155, "cost": 15.234347 }, { "experiment": "azure/cyclecloud/gpu", "size": 32, "iterations": 5, "duration": 85.0, "cost": 16.644889 }, { "experiment": "aws/eks/gpu", "size": 4, "iterations": 5, "duration": 438.918704, "cost": 16.74231 }, { "experiment": "google/gke/gpu", "size": 8, "iterations": 5, "duration": 338.281347, "cost": 17.560561 }, { "experiment": "google/compute-engine/gpu", "size": 8, "iterations": 5, "duration": 340.932703, "cost": 17.698195 }, { "experiment": "aws/parallel-cluster/cpu", "size": 32, "iterations": 5, "duration": 713.0, "cost": 18.2528 }, { "experiment": "aws/eks/gpu", "size": 8, "iterations": 5, "duration": 246.518796, "cost": 18.806645 }, { "experiment": "aws/parallel-cluster/cpu", "size": 64, "iterations": 5, "duration": 374.0, "cost": 19.1488 }, { "experiment": "aws/eks/cpu", "size": 32, "iterations": 5, "duration": 767.756099, "cost": 19.654556 }, { "experiment": "azure/aks/gpu", "size": 32, "iterations": 5, "duration": 111.670663, "cost": 21.867597 }, { "experiment": "google/gke/gpu", "size": 16, "iterations": 5, "duration": 220.54449, "cost": 22.897419 }, { "experiment": "aws/parallel-cluster/cpu", "size": 128, "iterations": 5, "duration": 230.0, "cost": 23.552 }, { "experiment": "google/compute-engine/gpu", "size": 16, "iterations": 5, "duration": 231.828465, "cost": 24.068946 }, { "experiment": "aws/eks/gpu", "size": 16, "iterations": 5, "duration": 160.761477, "cost": 24.528629 }, { "experiment": "aws/eks/cpu", "size": 64, "iterations": 5, "duration": 537.243998, "cost": 27.506893 }, { "experiment": "google/gke/gpu", "size": 32, "iterations": 5, "duration": 151.550476, "cost": 31.468614 }, { "experiment": "aws/parallel-cluster/cpu", "size": 256, "iterations": 5, "duration": 158.0, "cost": 32.3584 }, { "experiment": "google/compute-engine/gpu", "size": 32, "iterations": 5, "duration": 157.359565, "cost": 32.674839 }, { "experiment": "azure/cyclecloud/cpu", "size": 32, "iterations": 5, "duration": 1041.0, "cost": 33.312 }, { "experiment": "azure/aks/cpu", "size": 32, "iterations": 5, "duration": 1179.415025, "cost": 37.741281 }, { "experiment": "google/gke/cpu", "size": 32, "iterations": 5, "duration": 848.195748, "cost": 38.14996 }, { "experiment": "azure/cyclecloud/cpu", "size": 128, "iterations": 5, "duration": 348.0, "cost": 44.544 }, { "experiment": "aws/eks/cpu", "size": 128, "iterations": 5, "duration": 547.896248, "cost": 56.104576 }, { "experiment": "azure/cyclecloud/cpu", "size": 64, "iterations": 5, "duration": 884.0, "cost": 56.576 }, { "experiment": "google/gke/cpu", "size": 64, "iterations": 5, "duration": 715.259097, "cost": 64.341529 }, { "experiment": "google/compute-engine/cpu", "size": 32, "iterations": 5, "duration": 1437.786338, "cost": 64.668434 }, { "experiment": "azure/aks/cpu", "size": 64, "iterations": 5, "duration": 1109.029363, "cost": 70.977879 }, { "experiment": "google/compute-engine/cpu", "size": 128, "iterations": 5, "duration": 563.505083, "cost": 101.380826 }, { "experiment": "azure/cyclecloud/cpu", "size": 256, "iterations": 5, "duration": 399.0, "cost": 102.144 }, { "experiment": "azure/aks/cpu", "size": 128, "iterations": 5, "duration": 891.895958, "cost": 114.162683 }, { "experiment": "google/gke/cpu", "size": 128, "iterations": 5, "duration": 653.111184, "cost": 117.501959 }, { "experiment": "azure/aks/cpu", "size": 256, "iterations": 5, "duration": 528.557068, "cost": 135.310609 }, { "experiment": "aws/eks/cpu", "size": 256, "iterations": 5, "duration": 798.170087, "cost": 163.465234 }, { "experiment": "google/compute-engine/cpu", "size": 256, "iterations": 5, "duration": 598.898858, "cost": 215.497118 }, { "experiment": "google/gke/cpu", "size": 256, "iterations": 5, "duration": 743.184567, "cost": 267.414323 }
    ],
    "AMG2023": [
        { "experiment": "azure/aks/gpu", "size": 4, "iterations": 5, "duration": 6.000251, "cost": 0.146873 }, { "experiment": "google/gke/cpu", "size": 4, "iterations": 5, "duration": 63.006414, "cost": 0.354236 }, { "experiment": "aws/eks/gpu", "size": 4, "iterations": 5, "duration": 27.291072, "cost": 1.041003 }, { "experiment": "azure/aks/gpu", "size": 8, "iterations": 5, "duration": 27.545686, "cost": 1.348514 }, { "experiment": "google/gke/gpu", "size": 4, "iterations": 5, "duration": 53.61919, "cost": 1.391716 }, { "experiment": "aws/eks/gpu", "size": 8, "iterations": 5, "duration": 28.437323, "cost": 2.169452 }, { "experiment": "azure/cyclecloud/gpu", "size": 4, "iterations": 5, "duration": 93.0, "cost": 2.276433 }, { "experiment": "google/gke/gpu", "size": 8, "iterations": 5, "duration": 51.504046, "cost": 2.673632 }, { "experiment": "azure/cyclecloud/gpu", "size": 8, "iterations": 5, "duration": 67.0, "cost": 3.280022 }, { "experiment": "azure/aks/gpu", "size": 16, "iterations": 5, "duration": 41.004234, "cost": 4.01477 }, { "experiment": "aws/eks/gpu", "size": 16, "iterations": 5, "duration": 31.527565, "cost": 4.810406 }, { "experiment": "azure/cyclecloud/gpu", "size": 16, "iterations": 5, "duration": 67.0, "cost": 6.560044 }, { "experiment": "google/gke/gpu", "size": 16, "iterations": 5, "duration": 65.730973, "cost": 6.824336 }, { "experiment": "azure/aks/gpu", "size": 32, "iterations": 5, "duration": 39.34915, "cost": 7.705438 }, { "experiment": "azure/cyclecloud/gpu", "size": 32, "iterations": 5, "duration": 41.0, "cost": 8.028711 }, { "experiment": "google/compute-engine/gpu", "size": 8, "iterations": 5, "duration": 156.875465, "cost": 8.14358 }, { "experiment": "aws/eks/cpu", "size": 32, "iterations": 5, "duration": 399.838421, "cost": 10.235864 }, { "experiment": "aws/parallel-cluster/cpu", "size": 32, "iterations": 5, "duration": 410.0, "cost": 10.496 }, { "experiment": "azure/cyclecloud/cpu", "size": 32, "iterations": 5, "duration": 338.0, "cost": 10.816 }, { "experiment": "azure/aks/cpu", "size": 32, "iterations": 5, "duration": 368.905487, "cost": 11.804976 }, { "experiment": "google/gke/gpu", "size": 32, "iterations": 5, "duration": 67.837902, "cost": 14.086164 }, { "experiment": "google/compute-engine/gpu", "size": 4, "iterations": 5, "duration": 737.720666, "cost": 19.14795 }, { "experiment": "azure/cyclecloud/cpu", "size": 64, "iterations": 5, "duration": 331.0, "cost": 21.184 }, { "experiment": "google/compute-engine/gpu", "size": 16, "iterations": 5, "duration": 207.459722, "cost": 21.538929 }, { "experiment": "aws/parallel-cluster/cpu", "size": 64, "iterations": 5, "duration": 429.0, "cost": 21.9648 }, { "experiment": "aws/eks/cpu", "size": 64, "iterations": 5, "duration": 433.347058, "cost": 22.187369 }, { "experiment": "azure/aks/cpu", "size": 64, "iterations": 5, "duration": 412.536705, "cost": 26.402349 }, { "experiment": "google/compute-engine/cpu", "size": 32, "iterations": 5, "duration": 655.8342, "cost": 29.497965 }, { "experiment": "google/gke/cpu", "size": 32, "iterations": 5, "duration": 708.072598, "cost": 31.847532 }, { "experiment": "azure/cyclecloud/cpu", "size": 256, "iterations": 5, "duration": 185.0, "cost": 47.36 }, { "experiment": "aws/parallel-cluster/cpu", "size": 128, "iterations": 5, "duration": 479.0, "cost": 49.0496 }, { "experiment": "aws/eks/cpu", "size": 128, "iterations": 5, "duration": 524.207904, "cost": 53.678889 }, { "experiment": "google/compute-engine/gpu", "size": 32, "iterations": 5, "duration": 261.919947, "cost": 54.386222 }, { "experiment": "google/compute-engine/cpu", "size": 64, "iterations": 5, "duration": 707.011564, "cost": 63.599618 }, { "experiment": "azure/aks/cpu", "size": 128, "iterations": 5, "duration": 514.62619, "cost": 65.872152 }, { "experiment": "aws/parallel-cluster/cpu", "size": 256, "iterations": 5, "duration": 517.0, "cost": 105.8816 }, { "experiment": "google/compute-engine/cpu", "size": 128, "iterations": 5, "duration": 786.715473, "cost": 141.538855 }, { "experiment": "aws/eks/cpu", "size": 256, "iterations": 5, "duration": 748.134517, "cost": 153.217949 }, { "experiment": "google/gke/cpu", "size": 256, "iterations": 5, "duration": 551.922571, "cost": 198.594006 }, { "experiment": "azure/aks/cpu", "size": 256, "iterations": 5, "duration": 800.762163, "cost": 204.995114 }, { "experiment": "google/compute-engine/cpu", "size": 256, "iterations": 5, "duration": 991.883052, "cost": 356.901564 }
    ],
    "kripke": [
        { "experiment": "aws/parallel-cluster/cpu", "size": 64, "iterations": 5, "duration": 222.0, "cost": 11.3664 }, { "experiment": "aws/parallel-cluster/cpu", "size": 32, "iterations": 5, "duration": 445.0, "cost": 11.392 }, { "experiment": "azure/cyclecloud/cpu", "size": 32, "iterations": 5, "duration": 360.0, "cost": 11.52 }, { "experiment": "aws/eks/cpu", "size": 32, "iterations": 5, "duration": 497.38004, "cost": 12.732929 }, { "experiment": "aws/parallel-cluster/cpu", "size": 128, "iterations": 5, "duration": 156.0, "cost": 15.9744 }, { "experiment": "aws/eks/cpu", "size": 64, "iterations": 5, "duration": 314.879022, "cost": 16.121806 }, { "experiment": "azure/cyclecloud/cpu", "size": 64, "iterations": 5, "duration": 312.0, "cost": 19.968 }, { "experiment": "google/compute-engine/cpu", "size": 32, "iterations": 5, "duration": 565.776724, "cost": 25.44738 }, { "experiment": "aws/parallel-cluster/cpu", "size": 256, "iterations": 5, "duration": 141.0, "cost": 28.8768 }, { "experiment": "azure/cyclecloud/cpu", "size": 128, "iterations": 5, "duration": 227.0, "cost": 29.056 }, { "experiment": "google/compute-engine/cpu", "size": 64, "iterations": 5, "duration": 328.462531, "cost": 29.547029 }, { "experiment": "azure/aks/cpu", "size": 32, "iterations": 5, "duration": 923.487162, "cost": 29.551589 }, { "experiment": "google/gke/cpu", "size": 32, "iterations": 5, "duration": 658.142446, "cost": 29.601785 }, { "experiment": "aws/eks/cpu", "size": 128, "iterations": 5, "duration": 381.413421, "cost": 39.056734 }, { "experiment": "google/gke/cpu", "size": 64, "iterations": 5, "duration": 492.043427, "cost": 44.26204 }, { "experiment": "google/compute-engine/cpu", "size": 128, "iterations": 5, "duration": 315.549572, "cost": 56.770874 }, { "experiment": "azure/cyclecloud/cpu", "size": 256, "iterations": 5, "duration": 225.0, "cost": 57.6 }, { "experiment": "azure/aks/cpu", "size": 64, "iterations": 5, "duration": 1246.093584, "cost": 79.749989 }, { "experiment": "azure/aks/cpu", "size": 128, "iterations": 5, "duration": 731.352554, "cost": 93.613127 }, { "experiment": "azure/aks/cpu", "size": 256, "iterations": 5, "duration": 642.369139, "cost": 164.4465 }, { "experiment": "google/compute-engine/cpu", "size": 256, "iterations": 5, "duration": 478.692692, "cost": 172.244268 }, { "experiment": "aws/eks/cpu", "size": 256, "iterations": 5, "duration": 855.001001, "cost": 175.104205 }, { "experiment": "google/gke/cpu", "size": 256, "iterations": 5, "duration": 501.518385, "cost": 180.45746 }, { "experiment": "google/gke/cpu", "size": 128, "iterations": 5, "duration": 1146.17478, "cost": 206.209578 }
    ],
    "Laghos": [
        { "experiment": "aws/eks/cpu", "size": 32, "iterations": 5, "duration": 1393.078493, "cost": 35.662809 }, { "experiment": "azure/aks/cpu", "size": 32, "iterations": 5, "duration": 1467.147843, "cost": 46.948731 }, { "experiment": "google/gke/cpu", "size": 32, "iterations": 5, "duration": 1239.911574, "cost": 55.768467 }, { "experiment": "aws/eks/cpu", "size": 64, "iterations": 5, "duration": 1511.423655, "cost": 77.384891 }, { "experiment": "google/compute-engine/cpu", "size": 32, "iterations": 5, "duration": 1856.368492, "cost": 83.49533 }, { "experiment": "google/compute-engine/cpu", "size": 64, "iterations": 5, "duration": 1494.855771, "cost": 134.470581 }, { "experiment": "google/gke/cpu", "size": 64, "iterations": 5, "duration": 1533.616023, "cost": 137.957281 }
    ],
    "MiniFE": [
        { "experiment": "azure/aks/gpu", "size": 4, "iterations": 5, "duration": 1.801894, "cost": 0.044106 }, { "experiment": "google/gke/gpu", "size": 4, "iterations": 5, "duration": 1.922417, "cost": 0.049897 }, { "experiment": "azure/aks/gpu", "size": 16, "iterations": 5, "duration": 0.660362, "cost": 0.064657 }, { "experiment": "google/compute-engine/gpu", "size": 4, "iterations": 5, "duration": 3.521814, "cost": 0.091411 }, { "experiment": "azure/aks/gpu", "size": 8, "iterations": 5, "duration": 2.287007, "cost": 0.111962 }, { "experiment": "azure/aks/cpu", "size": 32, "iterations": 5, "duration": 3.859197, "cost": 0.123494 }, { "experiment": "azure/aks/gpu", "size": 32, "iterations": 5, "duration": 0.715433, "cost": 0.140098 }, { "experiment": "azure/cyclecloud/gpu", "size": 4, "iterations": 5, "duration": 6.14875, "cost": 0.150508 }, { "experiment": "google/compute-engine/gpu", "size": 8, "iterations": 5, "duration": 4.244667, "cost": 0.220345 }, { "experiment": "google/gke/gpu", "size": 16, "iterations": 5, "duration": 2.335934, "cost": 0.242522 }, { "experiment": "azure/cyclecloud/gpu", "size": 8, "iterations": 5, "duration": 5.29735, "cost": 0.259335 }, { "experiment": "google/gke/gpu", "size": 8, "iterations": 5, "duration": 5.735687, "cost": 0.297746 }, { "experiment": "google/compute-engine/cpu", "size": 32, "iterations": 5, "duration": 7.15533, "cost": 0.321831 }, { "experiment": "aws/eks/cpu", "size": 64, "iterations": 5, "duration": 6.50823, "cost": 0.333221 }, { "experiment": "aws/eks/gpu", "size": 16, "iterations": 5, "duration": 2.503566, "cost": 0.381989 }, { "experiment": "azure/cyclecloud/gpu", "size": 16, "iterations": 5, "duration": 4.478131, "cost": 0.438459 }, { "experiment": "google/compute-engine/cpu", "size": 64, "iterations": 5, "duration": 5.126766, "cost": 0.461181 }, { "experiment": "google/compute-engine/gpu", "size": 16, "iterations": 5, "duration": 6.558215, "cost": 0.680888 }, { "experiment": "google/gke/cpu", "size": 64, "iterations": 5, "duration": 8.18639, "cost": 0.736411 }, { "experiment": "google/gke/gpu", "size": 32, "iterations": 5, "duration": 4.05978, "cost": 0.842991 }, { "experiment": "azure/cyclecloud/gpu", "size": 32, "iterations": 5, "duration": 4.548454, "cost": 0.890688 }, { "experiment": "aws/eks/cpu", "size": 128, "iterations": 5, "duration": 9.08923, "cost": 0.930737 }, { "experiment": "google/compute-engine/gpu", "size": 32, "iterations": 5, "duration": 5.438467, "cost": 1.129267 }, { "experiment": "azure/aks/cpu", "size": 256, "iterations": 5, "duration": 4.63739, "cost": 1.187172 }, { "experiment": "google/compute-engine/cpu", "size": 128, "iterations": 5, "duration": 7.07502, "cost": 1.272875 }, { "experiment": "azure/aks/cpu", "size": 128, "iterations": 5, "duration": 13.4628, "cost": 1.723238 }, { "experiment": "google/compute-engine/cpu", "size": 256, "iterations": 5, "duration": 6.90533, "cost": 2.484691 }, { "experiment": "aws/eks/cpu", "size": 256, "iterations": 5, "duration": 13.79342, "cost": 2.824892 }, { "experiment": "google/gke/cpu", "size": 128, "iterations": 5, "duration": 15.76192, "cost": 2.835745 }, { "experiment": "aws/parallel-cluster/cpu", "size": 32, "iterations": 5, "duration": 1801.772, "cost": 46.125363 }, { "experiment": "azure/cyclecloud/cpu", "size": 32, "iterations": 5, "duration": 1635.087, "cost": 52.322784 }, { "experiment": "aws/parallel-cluster/cpu", "size": 64, "iterations": 5, "duration": 1374.085, "cost": 70.353152 }, { "experiment": "azure/cyclecloud/cpu", "size": 128, "iterations": 5, "duration": 553.351, "cost": 70.828928 }, { "experiment": "azure/cyclecloud/cpu", "size": 64, "iterations": 5, "duration": 1650.48, "cost": 105.63072 }, { "experiment": "aws/parallel-cluster/cpu", "size": 128, "iterations": 5, "duration": 1399.732, "cost": 143.332557 }, { "experiment": "azure/cyclecloud/cpu", "size": 256, "iterations": 5, "duration": 1118.745, "cost": 286.39872 }, { "experiment": "aws/parallel-cluster/cpu", "size": 256, "iterations": 5, "duration": 1416.924, "cost": 290.186035 }
    ],
    "MT-GEMM": [
        { "experiment": "aws/parallel-cluster/cpu", "size": 32, "iterations": 5, "duration": 56.0, "cost": 1.4336 }, { "experiment": "google/compute-engine/cpu", "size": 32, "iterations": 5, "duration": 36.488251, "cost": 1.64116 }, { "experiment": "aws/eks/cpu", "size": 32, "iterations": 5, "duration": 76.668317, "cost": 1.962709 }, { "experiment": "google/gke/cpu", "size": 32, "iterations": 5, "duration": 60.519207, "cost": 2.722019 }, { "experiment": "aws/parallel-cluster/cpu", "size": 64, "iterations": 5, "duration": 56.0, "cost": 2.8672 }, { "experiment": "google/compute-engine/cpu", "size": 64, "iterations": 5, "duration": 54.999613, "cost": 4.947521 }, { "experiment": "aws/parallel-cluster/cpu", "size": 128, "iterations": 5, "duration": 60.0, "cost": 6.144 }, { "experiment": "aws/eks/cpu", "size": 64, "iterations": 5, "duration": 121.989516, "cost": 6.245863 }, { "experiment": "google/gke/cpu", "size": 64, "iterations": 5, "duration": 77.002273, "cost": 6.926782 }, { "experiment": "azure/aks/cpu", "size": 32, "iterations": 5, "duration": 262.638954, "cost": 8.404447 }, { "experiment": "aws/parallel-cluster/cpu", "size": 256, "iterations": 5, "duration": 70.0, "cost": 14.336 }, { "experiment": "azure/aks/gpu", "size": 4, "iterations": 5, "duration": 603.274758, "cost": 14.766825 }, { "experiment": "google/gke/gpu", "size": 4, "iterations": 5, "duration": 630.480309, "cost": 16.364467 }, { "experiment": "google/compute-engine/gpu", "size": 4, "iterations": 5, "duration": 634.313085, "cost": 16.463949 }, { "experiment": "google/compute-engine/cpu", "size": 128, "iterations": 5, "duration": 124.802549, "cost": 22.453365 }, { "experiment": "aws/eks/gpu", "size": 4, "iterations": 5, "duration": 615.620169, "cost": 23.482489 }, { "experiment": "aws/eks/cpu", "size": 128, "iterations": 5, "duration": 253.032253, "cost": 25.910503 }, { "experiment": "google/gke/cpu", "size": 128, "iterations": 5, "duration": 157.284635, "cost": 28.297253 }, { "experiment": "azure/aks/gpu", "size": 8, "iterations": 5, "duration": 601.026024, "cost": 29.423563 }, { "experiment": "azure/aks/cpu", "size": 64, "iterations": 5, "duration": 486.185069, "cost": 31.115844 }, { "experiment": "google/gke/gpu", "size": 8, "iterations": 5, "duration": 637.376452, "cost": 33.08692 }, { "experiment": "google/compute-engine/gpu", "size": 8, "iterations": 5, "duration": 638.543005, "cost": 33.147477 }, { "experiment": "azure/cyclecloud/gpu", "size": 4, "iterations": 5, "duration": 1424.0, "cost": 34.856356 }, { "experiment": "aws/eks/gpu", "size": 8, "iterations": 5, "duration": 617.375727, "cost": 47.098908 }, { "experiment": "azure/aks/gpu", "size": 16, "iterations": 5, "duration": 602.797489, "cost": 59.020572 }, { "experiment": "google/gke/gpu", "size": 16, "iterations": 5, "duration": 636.613271, "cost": 66.094604 }, { "experiment": "google/compute-engine/gpu", "size": 16, "iterations": 5, "duration": 641.109839, "cost": 66.561448 }, { "experiment": "azure/cyclecloud/gpu", "size": 8, "iterations": 5, "duration": 1418.0, "cost": 69.418978 }, { "experiment": "aws/eks/gpu", "size": 16, "iterations": 5, "duration": 616.187507, "cost": 94.01652 }, { "experiment": "google/gke/cpu", "size": 256, "iterations": 5, "duration": 293.088115, "cost": 105.459617 }, { "experiment": "azure/aks/gpu", "size": 32, "iterations": 5, "duration": 607.372628, "cost": 118.937058 }, { "experiment": "google/compute-engine/cpu", "size": 256, "iterations": 5, "duration": 333.940295, "cost": 120.159139 }, { "experiment": "google/gke/gpu", "size": 32, "iterations": 5, "duration": 637.082072, "cost": 132.286553 }, { "experiment": "google/compute-engine/gpu", "size": 32, "iterations": 5, "duration": 641.84032, "cost": 133.274577 }, { "experiment": "azure/cyclecloud/gpu", "size": 16, "iterations": 5, "duration": 1413.0, "cost": 138.3484 }, { "experiment": "aws/eks/cpu", "size": 256, "iterations": 5, "duration": 739.739289, "cost": 151.498606 }, { "experiment": "azure/cyclecloud/gpu", "size": 32, "iterations": 5, "duration": 1121.0, "cost": 219.516711 }
    ],
    "Mixbench": [
        { "experiment": "aws/eks/cpu", "size": 32, "iterations": 5, "duration": 28.669969, "cost": 0.733951 }, { "experiment": "google/compute-engine/gpu", "size": 4, "iterations": 5, "duration": 32.621873, "cost": 0.846719 }, { "experiment": "azure/aks/cpu", "size": 32, "iterations": 5, "duration": 53.064232, "cost": 1.698055 }, { "experiment": "google/compute-engine/gpu", "size": 8, "iterations": 5, "duration": 35.240112, "cost": 1.829353 }, { "experiment": "google/compute-engine/cpu", "size": 32, "iterations": 5, "duration": 50.568045, "cost": 2.274438 }, { "experiment": "google/compute-engine/gpu", "size": 16, "iterations": 5, "duration": 32.2897, "cost": 3.352388 }, { "experiment": "aws/eks/gpu", "size": 4, "iterations": 5, "duration": 99.367589, "cost": 3.790321 }, { "experiment": "google/compute-engine/cpu", "size": 64, "iterations": 5, "duration": 54.268371, "cost": 4.881741 }, { "experiment": "azure/aks/gpu", "size": 4, "iterations": 5, "duration": 226.787617, "cost": 5.551257 }, { "experiment": "google/gke/gpu", "size": 4, "iterations": 5, "duration": 276.663975, "cost": 7.180967 }, { "experiment": "google/compute-engine/gpu", "size": 32, "iterations": 5, "duration": 34.646825, "cost": 7.194221 }, { "experiment": "aws/eks/gpu", "size": 8, "iterations": 5, "duration": 99.367589, "cost": 7.580643 }, { "experiment": "google/compute-engine/cpu", "size": 128, "iterations": 5, "duration": 50.754113, "cost": 9.131229 }, { "experiment": "aws/eks/gpu", "size": 16, "iterations": 5, "duration": 68.652741, "cost": 10.474883 }, { "experiment": "azure/aks/gpu", "size": 8, "iterations": 5, "duration": 216.184067, "cost": 10.583411 }, { "experiment": "google/gke/gpu", "size": 8, "iterations": 5, "duration": 285.476659, "cost": 14.819411 }, { "experiment": "google/compute-engine/cpu", "size": 256, "iterations": 5, "duration": 50.665977, "cost": 18.230744 }, { "experiment": "azure/aks/gpu", "size": 16, "iterations": 5, "duration": 235.459511, "cost": 23.054102 }, { "experiment": "azure/cyclecloud/cpu", "size": 32, "iterations": 5, "duration": 786.0, "cost": 25.152 }, { "experiment": "google/gke/gpu", "size": 16, "iterations": 5, "duration": 276.272679, "cost": 28.683243 }, { "experiment": "aws/parallel-cluster/cpu", "size": 32, "iterations": 5, "duration": 1380.0, "cost": 35.328 }, { "experiment": "azure/aks/gpu", "size": 32, "iterations": 5, "duration": 231.82029, "cost": 45.395564 }, { "experiment": "azure/cyclecloud/cpu", "size": 64, "iterations": 5, "duration": 776.0, "cost": 49.664 }, { "experiment": "google/gke/gpu", "size": 32, "iterations": 5, "duration": 286.738237, "cost": 59.539602 }, { "experiment": "google/gke/cpu", "size": 32, "iterations": 5, "duration": 1423.450112, "cost": 64.023623 }, { "experiment": "aws/parallel-cluster/cpu", "size": 64, "iterations": 5, "duration": 1389.0, "cost": 71.1168 }, { "experiment": "aws/eks/cpu", "size": 64, "iterations": 5, "duration": 1391.655292, "cost": 71.252751 }, { "experiment": "azure/aks/cpu", "size": 64, "iterations": 5, "duration": 1490.26084, "cost": 95.376694 }, { "experiment": "azure/cyclecloud/cpu", "size": 128, "iterations": 5, "duration": 777.0, "cost": 99.456 }, { "experiment": "google/gke/cpu", "size": 64, "iterations": 5, "duration": 1416.36664, "cost": 127.410048 }, { "experiment": "aws/eks/cpu", "size": 128, "iterations": 5, "duration": 1384.076351, "cost": 141.729418 }, { "experiment": "aws/parallel-cluster/cpu", "size": 128, "iterations": 5, "duration": 1392.0, "cost": 142.5408 }, { "experiment": "azure/aks/cpu", "size": 128, "iterations": 5, "duration": 1399.095298, "cost": 179.084198 }, { "experiment": "azure/cyclecloud/cpu", "size": 256, "iterations": 5, "duration": 779.0, "cost": 199.424 }, { "experiment": "google/gke/cpu", "size": 128, "iterations": 5, "duration": 1410.262067, "cost": 253.721815 }, { "experiment": "aws/eks/cpu", "size": 256, "iterations": 5, "duration": 1374.343377, "cost": 281.465524 }, { "experiment": "aws/parallel-cluster/cpu", "size": 256, "iterations": 5, "duration": 1387.0, "cost": 284.0576 }, { "experiment": "azure/aks/cpu", "size": 256, "iterations": 5, "duration": 1397.968787, "cost": 357.88001 }, { "experiment": "google/gke/cpu", "size": 256, "iterations": 5, "duration": 1411.052188, "cost": 507.727934 }
    ],
    "OSU All Reduce": [
        { "experiment": "azure/aks/gpu", "size": 8, "iterations": 5, "duration": 10.820151, "cost": 0.529707 }, { "experiment": "google/gke/gpu", "size": 4, "iterations": 5, "duration": 42.378436, "cost": 1.099956 }, { "experiment": "azure/aks/gpu", "size": 16, "iterations": 5, "duration": 12.323122, "cost": 1.206571 }, { "experiment": "google/gke/gpu", "size": 8, "iterations": 5, "duration": 53.380249, "cost": 2.771028 }, { "experiment": "azure/aks/gpu", "size": 32, "iterations": 5, "duration": 16.101114, "cost": 3.152956 }, { "experiment": "aws/eks/cpu", "size": 32, "iterations": 5, "duration": 123.960993, "cost": 3.173401 }, { "experiment": "aws/eks/gpu", "size": 16, "iterations": 5, "duration": 30.697072, "cost": 4.683691 }, { "experiment": "google/compute-engine/gpu", "size": 8, "iterations": 5, "duration": 106.54936, "cost": 5.531096 }, { "experiment": "azure/cyclecloud/gpu", "size": 4, "iterations": 5, "duration": 267.0, "cost": 6.535567 }, { "experiment": "google/compute-engine/cpu", "size": 32, "iterations": 5, "duration": 164.118048, "cost": 7.381665 }, { "experiment": "google/gke/cpu", "size": 32, "iterations": 5, "duration": 192.932057, "cost": 8.677655 }, { "experiment": "aws/parallel-cluster/cpu", "size": 32, "iterations": 5, "duration": 404.0, "cost": 10.3424 }, { "experiment": "google/compute-engine/gpu", "size": 4, "iterations": 5, "duration": 404.004946, "cost": 10.486173 }, { "experiment": "azure/cyclecloud/cpu", "size": 128, "iterations": 5, "duration": 93.0, "cost": 11.904 }, { "experiment": "aws/eks/cpu", "size": 64, "iterations": 5, "duration": 283.709185, "cost": 14.52591 }, { "experiment": "google/compute-engine/gpu", "size": 16, "iterations": 5, "duration": 161.134438, "cost": 16.729335 }, { "experiment": "google/compute-engine/cpu", "size": 64, "iterations": 5, "duration": 191.082398, "cost": 17.188923 }, { "experiment": "aws/parallel-cluster/cpu", "size": 64, "iterations": 5, "duration": 403.0, "cost": 20.6336 }, { "experiment": "google/gke/gpu", "size": 32, "iterations": 5, "duration": 104.781043, "cost": 21.757201 }, { "experiment": "azure/cyclecloud/cpu", "size": 32, "iterations": 5, "duration": 816.0, "cost": 26.112 }, { "experiment": "google/gke/cpu", "size": 64, "iterations": 5, "duration": 359.483085, "cost": 32.337501 }, { "experiment": "aws/parallel-cluster/cpu", "size": 128, "iterations": 5, "duration": 425.0, "cost": 43.52 }, { "experiment": "azure/cyclecloud/gpu", "size": 8, "iterations": 5, "duration": 958.0, "cost": 46.899422 }, { "experiment": "google/compute-engine/cpu", "size": 128, "iterations": 5, "duration": 290.419833, "cost": 52.249755 }, { "experiment": "google/compute-engine/gpu", "size": 32, "iterations": 5, "duration": 273.055737, "cost": 56.698507 }, { "experiment": "aws/eks/cpu", "size": 128, "iterations": 5, "duration": 600.750433, "cost": 61.516844 }, { "experiment": "azure/aks/cpu", "size": 64, "iterations": 5, "duration": 1200.567244, "cost": 76.836304 }, { "experiment": "google/compute-engine/cpu", "size": 256, "iterations": 5, "duration": 224.147536, "cost": 80.653264 }, { "experiment": "azure/cyclecloud/cpu", "size": 64, "iterations": 5, "duration": 1569.0, "cost": 100.416 }, { "experiment": "azure/cyclecloud/gpu", "size": 16, "iterations": 5, "duration": 1282.0, "cost": 125.522044 }, { "experiment": "aws/eks/cpu", "size": 256, "iterations": 5, "duration": 793.881815, "cost": 162.586996 }, { "experiment": "azure/aks/cpu", "size": 128, "iterations": 5, "duration": 1324.174377, "cost": 169.49432 }, { "experiment": "azure/cyclecloud/gpu", "size": 32, "iterations": 5, "duration": 931.0, "cost": 182.310489 }, { "experiment": "google/gke/cpu", "size": 128, "iterations": 5, "duration": 1023.604868, "cost": 184.157889 }, { "experiment": "aws/parallel-cluster/cpu", "size": 256, "iterations": 5, "duration": 901.0, "cost": 184.5248 }, { "experiment": "azure/aks/cpu", "size": 256, "iterations": 5, "duration": 1106.4933, "cost": 283.262285 }, { "experiment": "google/gke/cpu", "size": 256, "iterations": 5, "duration": 911.117476, "cost": 327.840315 }, { "experiment": "azure/cyclecloud/cpu", "size": 256, "iterations": 5, "duration": 1483.0, "cost": 379.648 }
    ]
};

// 2. STATE AND CONFIG
let sortState = { column: 'cost', direction: 'asc' };
let groupedData = [];
let flatData = [];
let globalMinCost = 0;
let globalMaxCost = 0;
let isGlobalSortActive = false;

// 3. COLOR MAPPING
const cloudColorMap = { aws: '#D87900', azure: '#002D62', google: '#8AB4F8' };
const typeColorMap = { gpu: '#d6eaf8', cpu: '#fdebd0' };
const sizeColorPalette = [ '#EADFF2', '#D4E6F1', '#D1F2EB', '#D6DBDF', '#FDEDEC', '#D0ECE7', '#EAEDED' ];
const sizeColorMap = {};
const gradientColors = { start: { r: 46, g: 204, b: 113 }, mid: { r: 241, g: 196, b: 15 }, end: { r: 231, g: 76, b: 60 } };

// 4. HELPER FUNCTIONS
function darkenColor(hex, percent) {
    hex = hex.replace('#', '');
    let r = parseInt(hex.substring(0, 2), 16);
    let g = parseInt(hex.substring(2, 4), 16);
    let b = parseInt(hex.substring(4, 6), 16);
    r = Math.floor(r * (1 - percent / 100));
    g = Math.floor(g * (1 - percent / 100));
    b = Math.floor(b * (1 - percent / 100));
    return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).padStart(6, '0')}`;
}
function getColorForValue(value, min, max) {
    const position = (max === min) ? 0 : (value - min) / (max - min);
    let r, g, b;
    if (position < 0.5) {
        const localPos = position * 2;
        r = Math.round(gradientColors.start.r + localPos * (gradientColors.mid.r - gradientColors.start.r));
        g = Math.round(gradientColors.start.g + localPos * (gradientColors.mid.g - gradientColors.start.g));
        b = Math.round(gradientColors.start.b + localPos * (gradientColors.mid.b - gradientColors.start.b));
    } else {
        const localPos = (position - 0.5) * 2;
        r = Math.round(gradientColors.mid.r + localPos * (gradientColors.end.r - gradientColors.mid.r));
        g = Math.round(gradientColors.mid.g + localPos * (gradientColors.end.g - gradientColors.mid.g));
        b = Math.round(gradientColors.mid.b + localPos * (gradientColors.end.b - gradientColors.mid.b));
    }
    return `rgb(${r}, ${g}, ${b})`;
}
function getContrastTextColor(rgbColor) {
    let colorString = rgbColor.startsWith('rgb') ? rgbColor : `${rgbColor}`;
    const hex = colorString.startsWith('#') ? colorString.substring(1, 7) : colorString;
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    return ((0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.5) ? '#000000' : '#ffffff';
}

// 5. RENDER AND DATA PROCESSING FUNCTIONS
function createGroupedData(data) {
    const groups = new Map();
    const flatData = data.map(item => { const [cloud, environment, type] = item.experiment.split('/'); return { cloud, environment, type, ...item }; });
    flatData.forEach(item => {
        const groupKey = `${item.cloud}/${item.environment}/${item.type}`;
        if (!groups.has(groupKey)) {
            groups.set(groupKey, { groupKey, isExpanded: false, summary: { ...item, duration: 0, cost: 0, childCount: 0 }, children: [] });
        }
        const group = groups.get(groupKey);
        group.summary.duration += item.duration;
        group.summary.cost += item.cost;
        group.summary.childCount++;
        group.children.push(item);
    });
    return Array.from(groups.values());
}
function renderTable() {
    if (isGlobalSortActive) {
        renderFlatTable();
    } else {
        renderGroupedTable();
    }
}
function renderGroupedTable() {
    const tableBody = document.getElementById('table-body');
    tableBody.innerHTML = '';
    const summaryCosts = groupedData.map(g => g.summary.cost);
    const summaryMinCost = Math.min(...summaryCosts); const summaryMaxCost = Math.max(...summaryCosts);

    groupedData.forEach(group => {
        const summary = group.summary;
        const costColor = getColorForValue(summary.cost, summaryMinCost, summaryMaxCost);
        const headerRow = document.createElement('tr');
        headerRow.className = 'group-header';
        headerRow.dataset.groupKey = group.groupKey;
        headerRow.innerHTML = `
            <td class="cloud-cell" style="background-color: ${cloudColorMap[summary.cloud]}; color: ${getContrastTextColor(cloudColorMap[summary.cloud])};"><span class="expand-icon">►</span>${summary.cloud}</td>
            <td>${summary.environment.replace(/-/g, ' ')} <span class="item-count">(${summary.childCount})</span></td>
            <td class="type-cell" style="background-color: ${typeColorMap[summary.type]};">${summary.type}</td>
            <td>-</td><td>${summary.iterations}</td><td>${summary.duration.toFixed(2)}</td>
            <td class="cost-cell" style="background-color: ${costColor}; color: ${getContrastTextColor(costColor)};">${summary.cost.toFixed(4)}</td>
        `;
        tableBody.appendChild(headerRow);
    });
}
function renderFlatTable() {
    const tableBody = document.getElementById('table-body');
    tableBody.innerHTML = '';

    flatData.forEach(item => {
        const costColor = getColorForValue(item.cost, globalMinCost, globalMaxCost);
        const row = document.createElement('tr');
        row.className = 'child-row';
        row.innerHTML = `
            <td class="cloud-cell" style="background-color: ${cloudColorMap[item.cloud]}; color: ${getContrastTextColor(cloudColorMap[item.cloud])};">${item.cloud}</td>
            <td>${item.environment.replace(/-/g, ' ')}</td>
            <td class="type-cell" style="background-color: ${typeColorMap[item.type]};">${item.type}</td>
            <td class="size-cell" style="background-color: ${sizeColorMap[item.size] || '#ffffff'};">${item.size}</td>
            <td>${item.iterations}</td>
            <td>${item.duration.toFixed(2)}</td>
            <td class="cost-cell" style="background-color: ${costColor}; color: ${getContrastTextColor(costColor)};">${item.cost.toFixed(4)}</td>
        `;
        tableBody.appendChild(row);
    });
}
function sortData() {
    const { column, direction } = sortState;
    const dataToSort = isGlobalSortActive ? flatData : groupedData;
    const key = isGlobalSortActive ? null : 'summary';

    dataToSort.sort((a, b) => {
        const valA = key ? a[key][column] : a[column];
        const valB = key ? b[key][column] : b[column];
        let comparison = 0;
        if (typeof valA === 'number') { comparison = valA - valB; } else { comparison = (valA || '').localeCompare(valB || ''); }
        return direction === 'asc' ? comparison : -comparison;
    });
    updateHeaderIndicators();
    renderTable();
}
function updateHeaderIndicators() {
    document.querySelectorAll('#experiment-table th').forEach(header => {
        const columnKey = header.dataset.column;
        header.classList.remove('sort-asc', 'sort-desc');
        if (columnKey === sortState.column) { header.classList.add(`sort-${sortState.direction}`); }
    });
}

// 6. MAIN APP INITIALIZATION AND UI LOGIC
function initializeApp(appName) {
    isGlobalSortActive = false;
    document.getElementById('app-subtitle').textContent = `${appName} Application`;
    document.getElementById('app-select').value = appName;
    const currentData = allApplicationsData[appName] || [];
    
    flatData = currentData.map(item => { const [cloud, environment, type] = item.experiment.split('/'); return { cloud, environment, type, ...item }; });
    groupedData = createGroupedData(currentData);
    
    const allCosts = currentData.map(item => item.cost);
    globalMinCost = Math.min(...allCosts);
    globalMaxCost = Math.max(...allCosts);
    
    sortState = { column: 'cost', direction: 'asc' };
    sortData();
    updateToggleButton();
}
function updateToggleButton() {
    const btn = document.getElementById('toggle-all-btn');
    btn.textContent = isGlobalSortActive ? 'Group View' : 'Expand All';
}
function injectDescriptionStyles() {
    const styleSheet = document.createElement('style');
    let cssRules = '';
    for (const [key, value] of Object.entries(cloudColorMap)) {
        cssRules += `.cloud-${key}-text { color: ${value}; }\n`;
    }
    for (const [key, value] of Object.entries(typeColorMap)) {
        cssRules += `.type-${key}-text { color: ${darkenColor(value, 40)}; }\n`;
    }
    const uniqueSizes = [...new Set(Object.values(allApplicationsData).flat().map(item => item.size))];
    uniqueSizes.forEach((size, index) => {
        const color = sizeColorPalette[index % sizeColorPalette.length];
        sizeColorMap[size] = color;
        cssRules += `.size-${size}-text { color: ${darkenColor(color, 40)}; }\n`;
    });
    styleSheet.innerHTML = cssRules;
    document.head.appendChild(styleSheet);
}

// 7. EVENT LISTENERS
function setupEventListeners() {
    const appSelect = document.getElementById('app-select');
    const toggleBtn = document.getElementById('toggle-all-btn');
    const tableBody = document.getElementById('table-body');

    Object.keys(allApplicationsData).forEach(appName => {
        const option = document.createElement('option');
        option.value = appName;
        option.textContent = appName;
        appSelect.appendChild(option);
    });
    
    appSelect.addEventListener('change', (e) => initializeApp(e.target.value));
    toggleBtn.addEventListener('click', () => {
        isGlobalSortActive = !isGlobalSortActive;
        sortState = { column: 'cost', direction: 'asc' };
        sortData();
        updateToggleButton();
    });
    document.querySelectorAll('#experiment-table th').forEach(header => {
        header.addEventListener('click', () => {
            const clickedColumn = header.dataset.column;
            if (sortState.column === clickedColumn) {
                sortState.direction = sortState.direction === 'asc' ? 'desc' : 'asc';
            } else {
                sortState.column = clickedColumn;
                sortState.direction = 'asc';
            }
            sortData();
        });
    });
    tableBody.addEventListener('click', (e) => {
        if (isGlobalSortActive) return;
        const row = e.target.closest('tr.group-header');
        if (row && row.dataset.groupKey) {
            isGlobalSortActive = true;
            updateToggleButton();
            sortData();
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    injectDescriptionStyles();
    setupEventListeners();
    initializeApp(Object.keys(allApplicationsData)[0]);
});
