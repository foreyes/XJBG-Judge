# mount tmpfs
mkdir -p /data
mkdir -p /projects/student
mount -t tmpfs -o size=500m tmpfs /data
mount -t tmpfs -o size=500m tmpfs /projects/student

# clear data directory and fetch testdata
cd /data
rm -rf *
cp /home/testdata/1004812/test_data.txt ./

# clear result directory
cd /projects/student
rm -rf *

# enter root directory and clear result files
cd /
rm -f a.out compile_result.txt program_stdout.txt time_result.txt answer_result.txt output_check.txt

# compile and remove source code file
g++ main.cpp -O3 -lpthread 2> compile_result.txt
rm -f main.cpp

# test
timeout -s HUP 120 perf stat ./a.out 1> program_stdout.txt 2> time_result.txt
cmp /projects/student/result.txt /home/testdata/1004812/answer.txt 1> answer_result.txt 2> output_check.txt
