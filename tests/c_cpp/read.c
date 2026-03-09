int read() {
    return 0;
}

int main() {
    read();
    return 1;
}

/* OUTPUT
[0] define function(read) { 
    }
[1] stop 
[2] function_end 
[3] define function(main) { 
[4]     syscall 
    }
[5] stop 
[6] function_end 
function=read, info={'name': 'read', 'info': {'bb_count': 1, 'ir_count': 3, 'is_start': False, 'funccalls': 0, 'syscalls': 0}}
function=main, info={'name': 'main', 'info': {'bb_count': 1, 'ir_count': 4, 'is_start': True, 'funccalls': 1, 'syscalls': 1}}
*/