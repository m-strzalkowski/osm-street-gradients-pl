

import re
import sys

#Extracts all parts of multpart response and saves as separate files
def extract_multipart(mime_file, out_dir='.'):
    print('Extracting parts of multipart from '+mime_file)
    with open(mime_file, "r", encoding="latin1") as f:  # use latin1 to preserve all bytes
        content = f.read()

    # Split on boundary --wcs
    parts = content.split("--wcs")

    for part in parts:
        part = part.strip()
        if not part or part == "--":
            continue

        # Extract filename from Content-Disposition
        m = re.search(r'filename="?([^"\r\n]+)"?', part, re.IGNORECASE)
        if m:
            filename = m.group(1)
        else:
            filename = "part.bin"

        # Find start of actual data (after empty line)
        data_start = part.find("\n\n")
        if data_start == -1:
            data_start = part.find("\r\n\r\n")
        if data_start == -1:
            print(f"Could not find data for {filename}, skipping")
            continue

        data = part[data_start:].lstrip()

        # Save as binary
        with open(out_dir+'/'+filename, "wb") as out:
            out.write(data.encode("latin1"))

        print(f"Saved: {out_dir+'/'+filename}, length={len(data)} bytes")
if __name__ == '__main__':
    mime_file = sys.argv[1]#"nmpt_even.asc"
    extract_multipart(mime_file)