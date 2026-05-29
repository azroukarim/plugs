import os
import tarfile
import time
import io

PLUGIN_NAME = "starplay"
VERSION = "1.0"
AUTHOR = "MARKETTV1"
DESCRIPTION = "StarPlay Enigma2 Plugin"
PACKAGE = "enigma2-plugin-extensions-starplay"

def make_control_tar_gz():
    control_content = f"""Package: {PACKAGE}
Version: {VERSION}
Description: {DESCRIPTION}
Architecture: all
Section: extra
Priority: optional
Maintainer: {AUTHOR}
Source: {AUTHOR}
"""
    mem = io.BytesIO()
    with tarfile.open(fileobj=mem, mode="w:gz") as tar:
        info = tarfile.TarInfo("control")
        info.size = len(control_content.encode('utf-8'))
        info.mtime = int(time.time())
        info.mode = 0o644
        tar.addfile(info, io.BytesIO(control_content.encode('utf-8')))
    return mem.getvalue()

def make_data_tar_gz(src_dir):
    mem = io.BytesIO()
    with tarfile.open(fileobj=mem, mode="w:gz") as tar:
        base_path = "usr/lib/enigma2/python/Plugins/Extensions/StarPlay"
        
        # Add directories
        parts = base_path.split('/')
        for i in range(1, len(parts) + 1):
            dinfo = tarfile.TarInfo('/'.join(parts[:i]))
            dinfo.type = tarfile.DIRTYPE
            dinfo.mode = 0o755
            dinfo.mtime = int(time.time())
            tar.addfile(dinfo)

        # Add files
        for root, _, files in os.walk(src_dir):
            if '.git' in root or '__pycache__' in root:
                continue
            for file in files:
                if file.endswith('.py') or file.endswith('.png') or file.endswith('.xml'):
                    filepath = os.path.join(root, file)
                    relpath = os.path.relpath(filepath, src_dir)
                    # Convert to linux slashes
                    relpath = relpath.replace("\\", "/")
                    arcname = f"{base_path}/{relpath}"
                    
                    finfo = tarfile.TarInfo(arcname)
                    with open(filepath, 'rb') as f:
                        data = f.read()
                    finfo.size = len(data)
                    finfo.mode = 0o644
                    finfo.mtime = int(time.time())
                    tar.addfile(finfo, io.BytesIO(data))
    return mem.getvalue()

def build_ipk(src_dir, out_file):
    debian_binary = b"2.0\n"
    control_tar_gz = make_control_tar_gz()
    data_tar_gz = make_data_tar_gz(src_dir)

    with open(out_file, "wb") as ar:
        ar.write(b"!<arch>\n")
        
        for name, data in [("debian-binary", debian_binary), 
                           ("control.tar.gz", control_tar_gz), 
                           ("data.tar.gz", data_tar_gz)]:
            header_name = name.encode('ascii').ljust(16)
            timestamp = str(int(time.time())).encode('ascii').ljust(12)
            owner = b"0     "
            group = b"0     "
            mode = b"100644  "
            size = str(len(data)).encode('ascii').ljust(10)
            magic = b"\x60\n"
            
            ar.write(header_name + timestamp + owner + group + mode + size + magic)
            ar.write(data)
            if len(data) % 2 != 0:
                ar.write(b"\n")
                
if __name__ == "__main__":
    src = os.path.join(os.path.dirname(__file__), "starplay")
    out = os.path.join(os.path.dirname(__file__), f"{PACKAGE}_{VERSION}_all.ipk")
    build_ipk(src, out)
    print(f"Successfully built {out}")
