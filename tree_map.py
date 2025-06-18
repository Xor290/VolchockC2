import os

def print_tree(startpath, prefix=""):
    entries = sorted(os.listdir(startpath))
    entries_count = len(entries)
    for i, entry in enumerate(entries):
        path = os.path.join(startpath, entry)
        connector = "├── " if i < entries_count - 1 else "└── "
        print(prefix + connector + entry)
        if os.path.isdir(path):
            extension = "│   " if i < entries_count - 1 else "    "
            print_tree(path, prefix + extension)

if __name__ == "__main__":
    # root = "." ou le chemin voulu
    root = "."
    print_tree(root)
