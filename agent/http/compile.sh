#!/bin/bash

echo "=== Compilation MinGW ==="

# Compiler la DLL
echo "Compilation DLL..."
x86_64-w64-mingw32-g++ -shared -o agent.dll \
  main_dll.cpp \
  base64.cpp \
  crypt.cpp \
  system_utils.cpp \
  file_utils.cpp \
  http_client.cpp \
  task.cpp \
  pe-exec.cpp \
  vm_detection.cpp \
  -lwininet -lpsapi -static-libstdc++ -static-libgcc -lws2_32
# Compiler l'exécutable
echo "Compilation EXE..."
x86_64-w64-mingw32-g++ -o agent.exe \
  main_exe.cpp \
  vm_detection.cpp \
  base64.cpp \
  crypt.cpp \
  system_utils.cpp \
  file_utils.cpp \
  http_client.cpp \
  task.cpp \
  pe-exec.cpp \
  -lwininet -lpsapi -static-libstdc++ -static-libgcc -lws2_32

echo "=== Vérification ==="
file agent.dll agent.exe

echo "=== Taille des fichiers ==="
ls -lh agent.dll agent.exe