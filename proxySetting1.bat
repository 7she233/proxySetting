@echo off

REM 指定Python解释器可执行文件路径
set PYTHON_EXE="F:\8hProject\PJ_series\PJ.proxySetting\.venv\Scripts\python.exe"

REM 指定Python脚本文件的路径
set SCRIPT_PATH="F:\8hProject\PJ_series\PJ.proxySetting\proxySettingNew.py"

REM 执行Python脚本
%PYTHON_EXE% %SCRIPT_PATH%

REM 暂停，脚本执行完毕后保持窗口打开以便查看执行状态和输出信息
pause