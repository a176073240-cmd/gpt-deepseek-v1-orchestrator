@echo off
setlocal

set "HARNESS_ROOT=%DEEPSEEK_HARNESS_ROOT%"
if defined HARNESS_ROOT goto run

for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"
set "HARNESS_ROOT=%REPO_ROOT%\work\upstream\deepseek-harness"

:run
if not exist "%HARNESS_ROOT%\package.json" (
  >&2 echo DeepSeek Harness source tree not found: "%HARNESS_ROOT%"
  exit /b 1
)

pushd "%HARNESS_ROOT%" || exit /b 1
node --import tsx/esm apps/cli/src/bin.ts %*
set "EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %EXIT_CODE%
