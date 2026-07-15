# Dependency Locks

`requirements-desktop.txt` is the portable input file for the dashboard and compression runtime.

The lock files are platform-specific because `pywebview` resolves different GUI backends per operating system:

- `requirements-desktop-macos.lock` may include `pyobjc-*`.
- `requirements-desktop-linux.lock` should be generated on Linux/WSL.
- `requirements-desktop-windows.lock` should be generated on Windows.

`install_stack.py` chooses the lock for the current platform when present. If no platform lock exists, it falls back to `requirements-desktop.txt`.

Regenerate a lock from the target platform:

```bash
python -m pip install pip-tools
pip-compile --output-file=requirements-desktop-windows.lock requirements-desktop.txt
```

On macOS, use `requirements-desktop-macos.lock`; on Windows, use `requirements-desktop-windows.lock`.
