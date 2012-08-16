"Creates manifest files and hashes"

import hashlib
import os
import sys

def manifest(directory, nohash):
    "Writes Machination manifest files."

    dirsize = __size(directory)

    if nohash:
        return __manifest_nohash(directory, dirsize)
    else:
        return __manifest_hash(directory, dirsize)

def __size(start_path='.'):
        total = 0
        for root, dirs, files in os.walk(start_path):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
        return total

def __manifest_hash(directory, size):
    sha = hashlib.sha512()
    with open(os.path.join(directory, 'manifest'), 'w') as m:
        # First line is bundle size
        m.write(size + "\n")

        # Walk the directory, listing files and hashing.
        os.chdir(directory)
        for dirname, dirnames, filenames in os.walk('.'):
            for files in filenames:
                if files == 'manifest': continue
                fn = os.path.normpath(os.path.join(dirname, files))
                with open(fn, 'rb') as f:
                    sha.update(f.read())
                m.write(fn+'\n')
    with open(os.path.join(directory, 'hash'), 'w') as h:
        m.write(sha.hexdigest())

def __manifest_nohash(directory, size):
    with open(os.path.join(directory, 'manifest'), 'w') as m:
        # First line is bundle size
        m.write(size + "\n")

        # Walk the directory, listing files and hashing.
        os.chdir(directory)
        for dirname, dirnames, filenames in os.walk('.'):
            for files in filenames:
                if files == 'manifest': continue
                fn = os.path.normpath(os.path.join(dirname, files))
                m.write(fn+'\n')

if __name__ == '__main__':
    if (len(sys.argv) > 3) or (len(sys.argv) < 2):
        print("Usage: manifest.py directory [--nohash]")
        sys.exit()

    if sys.argv[3] == "--nohash"
        nohash = True
    else:
        nohash = False
    manifest(sys.argv[2], nohash)
