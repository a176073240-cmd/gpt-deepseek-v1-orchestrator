# Windows packaging

This directory contains the reproducible PyInstaller configuration for
GPT-DeepSeek v1.2.0.

## Build

Run from the repository root on Windows:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging/build-windows.ps1
~~~

The script locates `.venv`, `py -3`, or `python`, installs the `gui` and
`packaging` extras, isolates PyInstaller from unrelated DLL directories on the
machine `PATH`, and runs the checked-in spec file. To use dependencies that are
already installed:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging/build-windows.ps1 -SkipInstall
~~~

Output:

~~~text
dist/GPT-DeepSeek/
├── GPT-DeepSeek.exe
├── GPT-DeepSeek-CLI.exe
├── README-Windows.md
├── LICENSE
└── _internal/

dist/GPT-DeepSeek-v1.2.0-windows-x64.zip
~~~

Distribute `GPT-DeepSeek-v1.2.0-windows-x64.zip`. The helper CLI executable is
launched by the GUI and must remain beside `GPT-DeepSeek.exe` after extraction.

`build/` and `dist/` are ignored and must not be committed. Do not place API
keys, `.env`, or other credentials in the package.

## Verify

1. Check that `GPT-DeepSeek.exe` has Product Version `1.2.0` in Windows file
   properties.
2. Launch `dist/GPT-DeepSeek/GPT-DeepSeek.exe` and confirm the configuration
   panel is visible.
3. Select a Git workspace and confirm its status changes to valid.
4. Run `python -m pytest` from the source checkout.

The package embeds Python and PySide6. DeepSeek Harness remains an external
executor and `dsh` must be available on the user's `PATH`.
