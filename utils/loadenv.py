import os.path

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
parent_dir = os.path.dirname(parent_dir)
path = os.path.join(parent_dir, 'bin', 'activate_this.py')
execfile(path, {'__file__': path})
