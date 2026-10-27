# OfficeTools 办公工具箱

Windows 中文桌面程序，文件在本地处理，无需上传。第一版使用 Python + PySide6；界面与转换服务分离，后续可以继续增加 Excel、文本处理等工具。

## 使用

如果已有打包版本，直接双击 `dist/OfficeTools/OfficeTools.exe` 启动，无需另行安装 Python。移动或分发时请保留整个 `dist/OfficeTools` 文件夹。Git 仓库只包含源码，不包含虚拟环境和 EXE；从 GitHub 下载源码后请按下述步骤安装，或运行 `build.bat` 自行打包。

源码启动：已安装环境时，双击 `start.bat`。新电脑需要 Python 3.12，先运行 `setup.bat` 安装依赖，再运行 `start.bat`。

选择工具 → 添加文件 → 按需拖动调整顺序 → 设置参数和输出目录 → 开始转换。每次任务生成独立文件夹，不覆盖原文件或历史结果。失败或取消后，已完成文件保留，可从日志或“打开结果目录”找到。

| 工具 | 功能 |
| --- | --- |
| PDF 转图片 | PNG/JPG、96–300 DPI、指定页码 |
| 图片转 PDF | 按顺序合并、原图尺寸或 A4、自动校正 EXIF 方向 |
| PDF 转 Word | 输出可编辑 DOCX、指定页码 |
| PDF 合并 | 按列表顺序合并页面内容 |
| 图片格式转换 | PNG/JPG/WebP，支持常见图片输入 |

## 当前边界

- PDF 转 Word 适合文字型 PDF，不支持 OCR；所选页包含没有文字层的页面时会明确报错。复杂表格、字体和排版可能需要手动调整。
- 加密 PDF 需先解密。页码范围应用到每一个输入 PDF；任一文件失败会停止当前批次。
- 图片仅处理第一帧；透明图片转 JPG 使用白底。PDF 合并只合并页面，不保留交互表单、书签或数字签名语义。
- 取消是协作式的，需等待当前页面或当前 Word 文件处理完成。处理时关闭窗口会先请求取消，任务停止后可关闭。
- 大文件耗时与内存占用取决于文件内容。超大页面栅格化有像素数限制。

## 开发与验证

```powershell
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

`office_tools/converters.py` 提供工具注册表和无界面的转换服务；`office_tools/app.py` 提供桌面布局和后台任务线程。增加工具时，在注册表中添加描述，并接入服务与必要参数。

运行 `build.bat` 生成 `dist/OfficeTools/OfficeTools.exe`，发布时需分发整个 OfficeTools 文件夹。

打包脚本 `scripts/build.py` 使用受控的 PATH，防止收集其他软件提供的同名 DLL（例如 Poppler 的 ICU 库）。打包完成后会运行实际 EXE 的 `--self-test`，创建 Qt 窗口并执行五项转换，验证报告保存在 `build/packaged-self-test.json`。只有自检成功才报告打包完成。

转换 API 参考：[PyMuPDF](https://pymupdf.readthedocs.io/en/latest/recipes-images.html)、[pdf2docx](https://pdf2docx.readthedocs.io/en/stable/)。发布商业闭源版本前需检查 PyMuPDF 等依赖的许可证条件。

下一阶段可按需求增加 OCR、Word 转 PDF、PDF 拆分压缩、Excel 批处理，并逐步加入任务历史和安装包。
