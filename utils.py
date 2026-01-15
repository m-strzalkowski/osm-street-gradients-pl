import subprocess

def run_command(cmd: str, capture_output: bool = True, log=print) -> str | None:
    """
    Run an arbitrary shell command and pipe stdout to console.
    cmd: Command to execute (as a single string).
    capture_output: If True, returns full stdout as a string.
    """
    log('run_command:', cmd)
    output_lines = []

    # Start the process
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True  # text mode
    )

    # Stream stdout line by line
    for line in iter(process.stdout.readline, ''):
        print(line, end='')  # pipe to console
        if capture_output:
            output_lines.append(line)

    process.stdout.close()
    process.wait()

    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd)

    if capture_output:
        return ''.join(output_lines)
    return None