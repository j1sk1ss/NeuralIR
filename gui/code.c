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