import sys
import pyi_iu

# Search all import directors for a PYZOwner one
for im in sys.importManager.metapath:
    if isinstance(im, pyi_iu.PathImportDirector):
        for arch in im.shadowpath.values():
            if isinstance(arch, pyi_archive.PYZOwner):
                # import all modules `*ImagePlugin`
                for name in arch.pyz.contents():
                    if name.endswith('ImagePlugin') and not '.' in name:
                        __import__(name)
