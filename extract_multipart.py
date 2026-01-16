

import re
import sys

#Extracts all parts of multpart response and saves as separate files
def extract_multipart(mime_file, out_dir='.', expected_parts=None):
    print('Extracting parts of multipart from '+mime_file)
    with open(mime_file, "r", encoding="latin1") as f:  # use latin1 to preserve all bytes
        content = f.read()

    # Split on boundary --wcs
    parts = content.split("--wcs")
    nonempty_parts = list()
    for i, part in enumerate(parts):
        part = part.strip()
        if not part or part == "--":
            print('empty part:',i,':', part)
            continue
        nonempty_parts.append(part)

    num_parts=len(nonempty_parts)
    if expected_parts is not None and num_parts != len(expected_parts):
        raise Exception(f'Expected {len(expected_parts)}, got {num_parts}')
    
    out_paths = list()
    for i, part in enumerate(nonempty_parts):
        # Extract filename from Content-Disposition
        m = re.search(r'filename="?([^"\r\n]+)"?', part, re.IGNORECASE)
        if m:
            filename = m.group(1)
        else:
            filename = f"part{i}.bin"

        if expected_parts is not None:
            if filename != expected_parts[i]:
                raise Exception(f'Expected part {i} to have filename={expected_parts[i]} but got {filename}')
            
        # Find start of actual data (after empty line)
        data_start = part.find("\n\n")
        if data_start == -1:
            data_start = part.find("\r\n\r\n")
        if data_start == -1:
            print(f"Could not find data for {filename}, skipping")
            continue

        data = part[data_start:].lstrip()
        out_path = out_dir+'/'+filename
        # Save as binary
        with open(out_path, "wb") as out:
            out.write(data.encode("latin1"))
        out_paths.append(out_path)
        print(f"Saved: {out_path}, length={len(data)} bytes")
    
    return out_paths
if __name__ == '__main__':
    mime_file = sys.argv[1]#"nmpt_even.asc"
    pths=extract_multipart(mime_file)
    print('files written:', pths)