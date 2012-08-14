"Creates manifest files and hashes"

import hashlib
import os
import sys

def manifest(pack='.'):
    sha = hashlib.sha512()
    with open(os.path.join(pack, 'manifest'), 'w') as m:
        os.chdir(pack)
        for dirname, dirnames, filenames in os.walk('.'):
            for files in filenames:
                if files == 'manifest': continue
                fn = os.path.normpath(os.path.join(dirname, files))
                with open(fn, 'rb') as f:
                    sha.update(f.read())
                m.write(fn+'\n')
        m.write(sha.hexdigest())

if __name__ == '__main__':
    for directory in sys.argv[1:]:
        manifest(directory)
