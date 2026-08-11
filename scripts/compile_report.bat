@echo off
REM ============================================================
REM compile_report.bat - Build main-case LaTeX report pipeline
REM
REM Pipeline:
REM   paper_register evidence pool -> scripts/build_bib.py -> references.bib
REM   survey_report.md + gap_report.md
REM     -> pandoc + scripts/md2latex.py -> report.tex
REM     -> tectonic -> report.pdf
REM
REM Prereqs:
REM   vendor\tectonic\tectonic.exe (tectonic 0.17.0, download from
REM     https://github.com/tectonic-typesetting/tectonic/releases)
REM   vendor\pandoc\pandoc-3.10.1\pandoc.exe (pandoc 3.10.1)
REM ============================================================
setlocal

set ROOT=%~dp0..
set TEC=%ROOT%\vendor\tectonic\tectonic.exe
set OUT=%ROOT%\workspace\outputs\literature_survey\latex

if not exist "%TEC%" (
  echo [ERROR] tectonic not found: %TEC%
  echo Download tectonic 0.17.0 to vendor\tectonic\ first.
  exit /b 1
)

echo [1/3] build references.bib via Crossref (about 2 min) ...
python "%ROOT%\scripts\build_bib.py" --out "%OUT%\references.bib"
if errorlevel 1 exit /b 1

echo [2/3] generate report.tex ...
python "%ROOT%\scripts\md2latex.py" --out "%OUT%\report.tex"
if errorlevel 1 exit /b 1

echo [3/3] compile report.pdf with tectonic (first run downloads packages) ...
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
echo Done. Artifacts:
echo   %OUT%\report.tex
echo   %OUT%\references.bib
echo   %OUT%\report.pdf
echo ============================================================
endlocal
