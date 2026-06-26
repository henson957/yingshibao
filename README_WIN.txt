盈时宝计时计费系统 - Windows 打包说明
========================================

一、打包方法（在一台 Windows 电脑上操作）
  1. 安装 Python 3.8+（安装时勾选 "Add Python to PATH"）
     https://www.python.org/downloads/

  2. 双击 build_win.bat，等待自动完成即可（第一次运行会安装依赖，稍慢）

  3. 打包好的程序在 dist\盈时宝计时计费系统\ 文件夹中

  4. 整个 dist\盈时宝计时计费系统\ 文件夹复制到任何 Windows 电脑都能用

二、版本历史
  v1.0.0 - 初始版本
  v1.0.1 - 优化分类系统，更换图标
  v1.0.2 - 新增 Word 表格导出，后台声音提醒（系统通知），60秒自动隐藏清理按钮

三、文件说明
  app.py             - 后端服务（Flask + SQLite）
  main.py            - 程序入口（pywebview 窗口）
  templates\         - 前端页面
  盈时宝.ico         - 程序图标
  build_win.bat      - 打包脚本（双击运行）
  requirements.txt   - Python 依赖
  盈时宝.spec        - macOS 打包配置（无需理会）

四、使用方法（给别人用）
  把 dist\盈时宝计时计费系统\ 整个文件夹发给对方
  双击 盈时宝计时计费系统.exe 即可启动
  底部显示手机访问地址，同一WiFi下可用

五、注意事项
  - 数据文件 data.db 在 dist\盈时宝计时计费系统\ 目录下
  - 导出报表自动保存到桌面（Word .docx 格式）
  - 后台运行时到点会弹出系统通知
