"""Exercise the frozen program, including Qt and conversion dependencies."""
import json
from pathlib import Path
import tempfile
import threading
import traceback


def run(report_path):
    report = Path(report_path)
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QTimer
        from PIL import Image
        import pymupdf
        from docx import Document
        from .app import Window, STYLE
        from .converters import convert

        app = QApplication([])
        app.setStyleSheet(STYLE)
        window = Window()
        window.show()
        assert window.isVisible()
        app.processEvents()
        window.grab().save(str(report.with_suffix('.png')))
        QTimer.singleShot(250, app.quit)
        app.exec()
        window.close()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'input.pdf'
            with pymupdf.open() as doc:
                doc.new_page().insert_text((72, 72), 'Packaged conversion works')
                doc.save(source)
            picture = root / 'input.png'
            Image.new('RGB', (60, 80), 'white').save(picture)
            for key, files in [('pdf_images', [source]), ('pdf_word', [source]),
                               ('images_pdf', [picture]), ('merge_pdf', [source, source]),
                               ('image_format', [picture])]:
                output = convert(key, files, root, {}, threading.Event(), lambda *_: None)
                assert list(output.iterdir()), key
                if key == 'pdf_word':
                    doc = Document(next(output.glob('*.docx')))
                    assert 'Packaged conversion works' in '\n'.join(p.text for p in doc.paragraphs)
        report.write_text(json.dumps({'status': 'passed', 'checks': ['Qt window', 'all five converters']}, indent=2), encoding='utf-8')
    except Exception:
        report.write_text(traceback.format_exc(), encoding='utf-8')
        raise SystemExit(1)
