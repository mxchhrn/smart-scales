import datetime
import os
import subprocess


def call_subprocess(command: list) -> tuple[int, str]:
    result = ''
    try:
        cmd_out = subprocess.run(command, capture_output=True, text=True, check=True)
        if cmd_out.stdout:
            result = cmd_out.stdout.strip()
        return cmd_out.returncode, result
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute shell command: {e}")
        return e.returncode, '-1'


def delete_empty_files(d_path: str):
    for f in os.listdir(d_path):
        f_path = os.path.join(d_path, f)
        if os.path.isfile(f_path) and os.path.getsize(f_path) == 0:
            os.remove(f_path)


# check if given path exists and absolute
def check_path(in_path: str) -> bool:
    if not os.path.exists(in_path):
        print('path:', in_path, 'does not exist')
        return False
    if in_path != os.path.abspath(in_path):
        print('path:', in_path, 'is not absolute')
        return False
    return True


# get sorted list of files with absolute file path
def get_files_ext(in_path: str, extension: str):
    # init files list
    files = []
    # loop over directory to append files with absolute paths
    for f in os.listdir(in_path):
        tmp_f = os.path.join(in_path, f)
        # only append existing files with extension .txt
        if os.path.isfile(tmp_f) and os.path.splitext(tmp_f)[-1] == '.' + extension:
            files.append(tmp_f)
    # sort files regarding creation date
    files.sort(key=lambda tmp_file: os.path.getctime(tmp_file))

    return files
