from pathlib import Path
import sys
import threading

from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QPushButton, QFileDialog,
    QComboBox, QLineEdit, QProgressBar, QPlainTextEdit, QMessageBox,
    QAbstractItemView, QFormLayout,
)
from .converters import TOOLS, convert, Cancelled


class Worker(QThread):
    progress = Signal(int, str)
    result = Signal(str, str)

    def __init__(self, tool, files, output, options):
        super().__init__()
        self.args = tool, files, output, options
        self.cancel = threading.Event()

    def run(self):
        try:
            path = convert(*self.args, self.cancel, self.progress.emit)
            self.result.emit('success', str(path))
        except Cancelled as exc:
            self.result.emit('cancelled', str(exc))
        except Exception as exc:
            self.result.emit('error', str(exc))


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.last_output = None
        self.setWindowTitle('OfficeTools · 办公工具箱')
        self.resize(1100, 800)
        self.setMinimumSize(900, 720)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(235)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(22, 30, 22, 24)
        brand = QLabel('◈  OfficeTools')
        brand.setObjectName('brand')
        side.addWidget(brand)
        side.addWidget(QLabel('你的日常办公工具箱'))
        side.addSpacing(35)
        side.addWidget(QLabel('格式转换'))
        self.nav = QListWidget()
        self.nav.addItems([t.title for t in TOOLS])
        side.addWidget(self.nav)
        side.addWidget(QLabel('本地处理 · 文件无需上传\nv0.1  /  桌面版'))
        layout.addWidget(sidebar)

        body = QWidget()
        content = QVBoxLayout(body)
        content.setContentsMargins(32, 26, 32, 24)
        content.setSpacing(12)
        label = QLabel('WORKSPACE  /  格式转换')
        label.setObjectName('eyebrow')
        content.addWidget(label)
        self.title = QLabel()
        self.title.setObjectName('title')
        content.addWidget(self.title)
        self.description = QLabel()
        self.description.setWordWrap(True)
        content.addWidget(self.description)

        self.editor = QWidget()
        edit = QVBoxLayout(self.editor)
        edit.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.add_button = QPushButton('＋ 添加文件')
        self.add_button.clicked.connect(self.add_files)
        bar.addWidget(self.add_button)
        remove = QPushButton('移除选中')
        remove.clicked.connect(self.remove_files)
        bar.addWidget(remove)
        clear = QPushButton('清空')
        clear.clicked.connect(lambda: self.files.clear())
        bar.addWidget(clear)
        bar.addStretch()
        edit.addLayout(bar)
        self.files = QListWidget()
        self.files.setMinimumHeight(150)
        self.files.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.files.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        edit.addWidget(self.files, 1)
        edit.addWidget(QLabel('可拖动列表条目调整合成顺序；支持一次选择多个文件。'))
        form = QFormLayout()
        self.format = QComboBox()
        self.dpi = QComboBox()
        self.dpi.addItems(['96', '150', '200', '300'])
        self.dpi.setCurrentText('150')
        self.pages = QLineEdit()
        self.pages.setPlaceholderText('留空表示全部页，例如 1,3-5（应用于每个 PDF）')
        self.paper = QComboBox()
        self.paper.addItems(['原图尺寸', 'A4'])
        self.option_rows = []
        for text, widget in [('输出格式', self.format), ('清晰度 DPI', self.dpi), ('页码范围', self.pages), ('页面尺寸', self.paper)]:
            caption = QLabel(text)
            form.addRow(caption, widget)
            self.option_rows.append((caption, widget))
        edit.addLayout(form)
        output_row = QHBoxLayout()
        self.output = QLineEdit(str(Path.home() / 'Documents' / 'OfficeTools输出'))
        output_row.addWidget(self.output)
        choose = QPushButton('选择输出目录')
        choose.clicked.connect(self.choose_output)
        output_row.addWidget(choose)
        edit.addLayout(output_row)
        content.addWidget(self.editor, 1)

        actions = QHBoxLayout()
        self.start_button = QPushButton('开始转换')
        self.start_button.setObjectName('primary')
        self.start_button.clicked.connect(self.start)
        actions.addWidget(self.start_button)
        self.cancel_button = QPushButton('取消任务')
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        self.open_button = QPushButton('打开结果目录 ↗')
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_output)
        actions.addWidget(self.open_button)
        content.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        content.addWidget(self.progress)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        self.log.setPlaceholderText('准备就绪，添加文件开始转换。')
        content.addWidget(self.log)
        layout.addWidget(body, 1)
        self.nav.currentRowChanged.connect(self.change_tool)
        self.nav.setCurrentRow(0)

    def change_tool(self, row):
        tool = TOOLS[row]
        self.title.setText(tool.title)
        self.description.setText(tool.description)
        self.files.clear()
        self.format.clear()
        self.format.addItems(['PNG', 'JPG', 'WEBP'] if tool.key == 'image_format' else ['PNG', 'JPG'])
        visible = [tool.key in ('pdf_images', 'image_format'), tool.key == 'pdf_images',
                   tool.key in ('pdf_images', 'pdf_word'), tool.key == 'images_pdf']
        for (label, widget), show in zip(self.option_rows, visible):
            label.setVisible(show)
            widget.setVisible(show)

    def add_files(self):
        tool = TOOLS[self.nav.currentRow()]
        pattern = ' '.join('*' + ext for ext in tool.extensions)
        paths, _ = QFileDialog.getOpenFileNames(self, '选择待处理文件', '', f'支持的文件 ({pattern})')
        existing = {self.files.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.files.count())}
        for path in paths:
            if path not in existing:
                item = QListWidgetItem(Path(path).name)
                item.setData(Qt.ItemDataRole.UserRole, path)
                item.setToolTip(path)
                self.files.addItem(item)
                existing.add(path)

    def remove_files(self):
        for item in self.files.selectedItems():
            self.files.takeItem(self.files.row(item))

    def choose_output(self):
        path = QFileDialog.getExistingDirectory(self, '选择输出目录', self.output.text())
        if path:
            self.output.setText(path)

    def start(self):
        files = [Path(self.files.item(i).data(Qt.ItemDataRole.UserRole)) for i in range(self.files.count())]
        if not files or not self.output.text().strip():
            QMessageBox.information(self, '还缺一步', '请添加文件并设置输出目录。')
            return
        options = dict(format=self.format.currentText(), dpi=int(self.dpi.currentText()),
                       pages=self.pages.text(), paper=self.paper.currentText())
        self.worker = Worker(TOOLS[self.nav.currentRow()].key, files, Path(self.output.text().strip()), options)
        self.worker.progress.connect(self.on_progress)
        self.worker.result.connect(self.on_result)
        self.worker.finished.connect(self.on_finished)
        self.log.clear()
        self.progress.setValue(0)
        self.last_output = None
        self.open_button.setEnabled(False)
        self.editor.setEnabled(False)
        self.nav.setEnabled(False)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.log.appendPlainText('正在转换… PDF 转 Word 的单个文件可能需要较长时间。')
        self.worker.start()

    def cancel(self):
        self.worker.cancel.set()
        self.cancel_button.setEnabled(False)
        self.log.appendPlainText('正在请求取消，将在当前处理步骤完成后停止。')

    def on_progress(self, value, message):
        self.progress.setValue(value)
        self.log.appendPlainText(message)
        if message.startswith('输出目录：'):
            self.last_output = message.removeprefix('输出目录：')
            self.open_button.setEnabled(True)

    def on_result(self, status, message):
        if status == 'success':
            self.progress.setValue(100)
            self.log.appendPlainText(f'转换完成！\n{message}')
        else:
            self.log.appendPlainText(('任务取消：' if status == 'cancelled' else '转换失败：') + message)

    def on_finished(self):
        self.editor.setEnabled(True)
        self.nav.setEnabled(True)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.worker.deleteLater()
        self.worker = None

    def open_output(self):
        if self.last_output:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_output))

    def closeEvent(self, event):
        if self.worker is not None:
            self.cancel()
            self.log.appendPlainText('请等待当前任务停止后再关闭窗口。')
            event.ignore()
        else:
            event.accept()


STYLE = '''
QWidget { font-family: "Microsoft YaHei UI"; font-size: 13px; color: #26334b; }
QMainWindow { background: #f4f6fa; }
QWidget#sidebar { background: #e8edf7; }
QLabel#brand { font-size: 23px; font-weight: 700; color: #304fbb; }
QLabel#title { font-size: 28px; font-weight: 700; }
QLabel#eyebrow { color: #72809b; font-size: 11px; }
QListWidget, QPlainTextEdit { background: white; border: 1px solid #dce2ed; border-radius: 8px; padding: 8px; }
QListWidget::item { padding: 12px 8px; border-radius: 5px; }
QListWidget::item:selected { background: #dce6ff; color: #2349b0; }
QPushButton { background: white; border: 1px solid #d2daea; border-radius: 6px; padding: 9px 15px; }
QPushButton:hover { background: #e7edff; }
QPushButton#primary { background: #365bd6; color: white; border: 0; font-weight: 600; }
QPushButton:disabled { background: #e9edf4; color: #949caf; }
QLineEdit, QComboBox { background: white; border: 1px solid #d2daea; border-radius: 5px; padding: 7px; }
QProgressBar { border: 0; background: #e4e9f2; border-radius: 5px; text-align: center; height: 16px; }
QProgressBar::chunk { background: #7e9bf3; border-radius: 5px; }
'''


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont('Microsoft YaHei UI', 10))
    app.setStyleSheet(STYLE)
    window = Window()
    window.show()
    sys.exit(app.exec())
