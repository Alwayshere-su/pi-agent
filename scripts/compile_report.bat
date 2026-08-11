@echo off
REM ============================================================
REM compile_report.bat - Build LaTeX report pipeline for a theme
REM
REM Usage: compile_report.bat [theme]
REM   theme defaults to "literature_survey"
REM
REM Pipeline:
REM   build_bib.py -> references.bib
REM   md2latex.py  -> report.tex
REM   tectonic     -> report.pdf
REM ============================================================
setlocal

set THEME=%1
if "%THEME%"=="" set THEME=literature_survey

set ROOT=%~dp0..
set TEC=%ROOT%\vendor\tectonic\tectonic.exe

REM Resolve OUT path: main theme has no subdir, others at {theme}/literature_survey/
if "%THEME%"=="literature_survey" (
  set OUT=%ROOT%\workspace\outputs\literature_survey\latex
) else (
  set OUT=%ROOT%\workspace\outputs\%THEME%\literature_survey\latex
)

if not exist "%TEC%" (
  echo [ERROR] tectonic not found: %TEC%
  echo Download tectonic 0.17.0 to vendor\tectonic\ first.
  exit /b 1
)

echo ============================================================
echo Compiling LaTeX report for theme: %THEME%
echo Output: %OUT%
echo ============================================================

echo [1/3] build references.bib ...
python "%ROOT%\scripts\build_bib.py" --theme "%THEME%" --out "%OUT%\references.bib"
if errorlevel 1 exit /b 1

echo [2/3] generate report.tex ...
python "%ROOT%\scripts\md2latex.py" --theme "%THEME%" --out "%OUT%\report.tex"
if errorlevel 1 exit /b 1

echo [3/3] compile report.pdf with tectonic ...
pushd "%OUT%"
"%TEC%" report.tex --keep-logs
set RC=%ERRORLEVEL%
popd

if %RC% neq 0 (
  echo [ERROR] tectonic failed. See %OUT%\report.log
  exit /b %RC%
)

echo.
echo ============================================================
echo Done. Artifacts for theme "%THEME%":
echo   %OUT%\report.tex
echo   %OUT%\references.bib
echo   %OUT%\report.pdf
echo ============================================================
endlocal
