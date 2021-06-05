import sys
import pathlib
import subprocess


def compile():
    """Use `pip-compile` on all the `requirements.txt` files in all test cases"""
    test_package = pathlib.Path("test_package")

    # Delete any existing/old envs so that we don't pick them up with `actions/upload-artifact`
    for old_env in test_package.glob("**/env/*.txt"):
        old_env.unlink()

    # Generate a new env file for each test case (folder in `test_package`)
    test_dirs = [p for p in test_package.iterdir() if (p / "requirements.txt").exists()]
    for d in test_dirs:
        requirements = str(d / "requirements.txt")
        out = str(d / f"env/{sys.platform}.txt")
        subprocess.run(["pip-compile", "--no-header", "-o", out, requirements])


def gather():
    """`actions/download-artifact` dumps files into a top-level `env-{os}` folder.
    We want to gather those up and put them into `test_package`. For example:
    `env-windows-latest/numpy/env/win32.txt` -> `test_package/numpy/env/win32.txt`
    `env-macos-latest/numpy/env/darwin.txt` -> `test_package/numpy/env/darwin.txt`
    """
    for f in pathlib.Path(".").glob("env-*/**/env/*.txt"):
        f.replace(pathlib.Path("test_package", *f.parts[-3:]))


if __name__ == "__main__":
    command = globals()[sys.argv[1]]
    command()
