import os

def tree(dir_path, prefix=""):
    files = sorted(os.listdir(dir_path))
    pointers = ['├── '] * (len(files) - 1) + ['└── ']
    for pointer, f in zip(pointers, files):
        path = os.path.join(dir_path, f)
        print(prefix + pointer + f)
        if os.path.isdir(path):
            extension = '│   ' if pointer == '├── ' else '    '
            tree(path, prefix + extension)

if __name__ == "__main__":
    print("Projet")
    tree(".", "")
