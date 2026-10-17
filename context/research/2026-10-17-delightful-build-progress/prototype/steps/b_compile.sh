n=1; while [ $n -le 8 ]; do echo "[$n/8] Compiling C object lib/part$n.c.o"; n=$((n + 1)); sleep 0.25; done
printf 'a line with an escape \033[31mred\033[0m and an emoji \342\235\257 stripped\n'
echo "compile: 8 objects, 4096 bytes"
