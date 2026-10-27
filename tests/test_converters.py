from pathlib import Path
import tempfile
import threading
import unittest

import pymupdf
from PIL import Image
from docx import Document
from office_tools.converters import convert, pages_from_text, Cancelled


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pdf = self.root / 'sample.pdf'
        with pymupdf.open() as doc:
            for text in ['First page', 'Second page']:
                page = doc.new_page(width=300, height=400)
                page.insert_text((30, 50), text)
            doc.save(self.pdf)
        self.img = self.root / 'transparent.png'
        Image.new('RGBA', (100, 150), (255, 0, 0, 0)).save(self.img)

    def tearDown(self):
        self.temp.cleanup()

    def run_tool(self, name, files, **options):
        return convert(name, files, self.root / 'out', options, threading.Event(), lambda *_: None)

    def test_page_ranges(self):
        self.assertEqual(pages_from_text('1,2-3,2', 3), [0, 1, 2])
        for value in ['0', '4', '2-1', 'abc', '1,,2']:
            with self.assertRaises(ValueError):
                pages_from_text(value, 3)

    def test_pdf_images_and_unique_output(self):
        first = self.run_tool('pdf_images', [self.pdf], pages='2', dpi=96, format='PNG')
        second = self.run_tool('pdf_images', [self.pdf], pages='2', dpi=96, format='JPG')
        self.assertNotEqual(first, second)
        self.assertEqual(len(list(first.glob('*.png'))), 1)
        with Image.open(next(first.glob('*.png'))) as image:
            self.assertEqual(image.width, 400)
        self.assertTrue(self.pdf.exists())

    def test_images_to_pdf_and_merge_order(self):
        output = self.run_tool('images_pdf', [self.img, self.img], paper='A4')
        with pymupdf.open(output / '合并结果.pdf') as doc:
            self.assertEqual(len(doc), 2)
            self.assertEqual(doc[0].rect.width, 595)
        output = self.run_tool('merge_pdf', [self.pdf, self.pdf])
        with pymupdf.open(output / '合并结果.pdf') as doc:
            self.assertEqual(len(doc), 4)
            self.assertIn('Second page', doc[3].get_text())

    def test_word_content(self):
        output = self.run_tool('pdf_word', [self.pdf], pages='2')
        doc = Document(next(output.glob('*.docx')))
        text = '\n'.join(p.text for p in doc.paragraphs)
        self.assertIn('Second page', text)
        self.assertNotIn('First page', text)

    def test_transparency_and_webp(self):
        output = self.run_tool('image_format', [self.img], format='JPG')
        with Image.open(next(output.glob('*.jpg'))) as image:
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
        output = self.run_tool('image_format', [self.img], format='WEBP')
        with Image.open(next(output.glob('*.webp'))) as image:
            self.assertEqual(image.size, (100, 150))

    def test_cancel_and_bad_input(self):
        stop = threading.Event()
        stop.set()
        with self.assertRaises(Cancelled):
            convert('pdf_images', [self.pdf], self.root, {}, stop, lambda *_: None)
        corrupt = self.root / 'broken.pdf'
        corrupt.write_text('invalid')
        with self.assertRaises(Exception):
            self.run_tool('pdf_images', [corrupt])
        with self.assertRaises(ValueError):
            self.run_tool('pdf_images', [])

    def test_encrypted_and_scanned(self):
        encrypted = self.root / 'locked.pdf'
        with pymupdf.open(self.pdf) as doc:
            doc.save(encrypted, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw='secret', owner_pw='owner')
        with self.assertRaisesRegex(ValueError, '加密'):
            self.run_tool('pdf_images', [encrypted])
        output = self.run_tool('images_pdf', [self.img])
        with self.assertRaisesRegex(ValueError, 'OCR'):
            self.run_tool('pdf_word', [output / '合并结果.pdf'])


if __name__ == '__main__':
    unittest.main()
