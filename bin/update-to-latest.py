import subprocess
import os

# Git repo (packages assumed in dist subdir)
gitdir = 'c:\\git\\machination'

# where should they go to pretend to be bundles
bdir = 'c:\\workspace\\bundles'

# get version
gitver = subprocess.check_output(
    ['git', '--git-dir', os.path.join(gitdir, '.git'),
     'describe', '--tags', '--long' ],
    shell=True
    ).strip().decode()

vlist = gitver.split('-')
vlist.pop()
commits = vlist.pop()
version = '{}.{}'.format('-'.join(vlist), commits)

