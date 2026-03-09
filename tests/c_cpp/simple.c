int foo(int a) {
    for (int i = 0; i < 10; i++) {
        a += 1;
    }

    return a;
}

void main(int* a) {
    while (1) {
        while (1) {
            int** b = &a;
            *b = foo(1);
        }

        *a = foo(2);
    }
}

/*OUTPUT
[ 0] define function(foo) { 
[ 1]     lb0: 
[ 2]     loop untill { 
[ 3]         declaration(operation(int)) 
[ 4]         if, true: lb1, else: lb2) { 
[ 5]             lb1: 
[ 6]             some operation 
[ 7]             jump to lb0 
[ 8]             lb2: 
             }
[ 9]         stop 
         }
[10]     function_end 
[11]     define function(main) { 
[12]         lb3: 
[13]         loop untill { 
[14]             if, true: lb4, else: lb5) { 
[15]                 lb4: 
[16]                 lb6: 
[17]                 loop untill { 
[18]                     if, true: lb7, else: lb8) { 
[19]                         lb7: 
[20]                         declaration(operation(int**)) 
[21]                         reference of something 
[22]                         dereference of something 
[23]                         call function(foo)() 
[24]                         some operation 
[25]                         jump to lb6 
[26]                         lb8: 
[27]                         dereference of something 
[28]                         call function(foo)() 
[29]                         some operation 
[30]                         jump to lb3 
[31]                         lb5: 
                         }
[32]                     function_end 
                     }
                 }
             }
         }
     }
{'owner': 'main', 'block_id': 6, 'action': 'fcall', 'called_function': 'foo', 'instruction_info': {'is_dom': False, 'same_inst_after': 0, 'same_inst_before': 0, 'near_break': -1}, 'loop_info': {'loop_size_bb': 2, 'loop_size_ir': 12, 'loop_nested': 1}}
{'owner': 'main', 'block_id': 7, 'action': 'fcall', 'called_function': 'foo', 'instruction_info': {'is_dom': False, 'same_inst_after': 0, 'same_inst_before': 0, 'near_break': -1}, 'loop_info': {'loop_size_bb': 5, 'loop_size_ir': 24, 'loop_nested': 0}}
function=foo, info={'name': 'foo', 'info': {'bb_count': 3, 'ir_count': 13, 'is_start': False, 'funccalls': 0, 'syscalls': 0}}
function=main, info={'name': 'main', 'info': {'bb_count': 6, 'ir_count': 27, 'is_start': True, 'funccalls': 2, 'syscalls': 0}}
*/