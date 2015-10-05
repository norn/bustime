import os.path

#def xfile(afile, globalz=None, localz=None):
#    with open(afile, "r") as fh:
#        exec(fh.read(), globalz, localz)

parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
parent_dir = os.path.dirname(parent_dir)
path = os.path.join(parent_dir, 'bin', 'activate_this.py')
#execfile(path, {'__file__': path})
#xfile(path)
exec(open(path).read())
