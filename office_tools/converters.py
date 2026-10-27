"""Conversion services independent of the desktop UI."""
from dataclasses import dataclass
from pathlib import Path
import io
import threading
import tempfile

import pymupdf
from PIL import Image, ImageOps


@dataclass(frozen=True)
class Tool:
    key: str
    title: str
    description: str
    extensions: tuple[str, ...]


IMAGES = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff')
TOOLS = [
    Tool('pdf_images', 'PDF 转图片', '每页导出一张图片，可选择 PNG 或 JPG 及清晰度。', ('.pdf',)),
    Tool('images_pdf', '图片转 PDF', '按列表顺序合成一个 PDF，自动处理照片方向。多帧图片使用第一帧。', IMAGES),
    Tool('pdf_word', 'PDF 转 Word', '转换为可编辑 DOCX。适合文字型 PDF；扫描件暂不支持 OCR，复杂排版可能需要调整。', ('.pdf',)),
    Tool('merge_pdf', 'PDF 合并', '按列表顺序合并 PDF 的页面内容。', ('.pdf',)),
    Tool('image_format', '图片格式转换', '批量转换 PNG、JPG、WebP。透明图片转 JPG 时使用白色背景；多帧图片使用第一帧。', IMAGES),
]


class Cancelled(Exception):
    pass


def pages_from_text(value: str, total: int) -> list[int]:
    if not value.strip():
        return list(range(total))
    pages = set()
    try:
        for part in value.replace('，', ',').split(','):
            limits = part.strip().split('-')
            if len(limits) > 2:
                raise ValueError()
            start, end = int(limits[0]), int(limits[-1])
            if not 1 <= start <= end <= total:
                raise ValueError()
            pages.update(range(start - 1, end))
    except ValueError:
        raise ValueError(f'页码应为 1-{total} 内的数字或范围，例如 1,3-5。') from None
    return sorted(pages)


def open_pdf(path: Path):
    doc = pymupdf.open(path)
    if doc.needs_pass or not doc.page_count:
        doc.close()
        raise ValueError('PDF 已加密或没有页面，请先解密并检查文件。')
    return doc


def image_bytes(path: Path, fmt='PNG'):
    with Image.open(path) as source:
        img = ImageOps.exif_transpose(source).convert('RGBA')
        if fmt == 'JPEG':
            background = Image.new('RGB', img.size, 'white')
            background.paste(img, mask=img.getchannel('A'))
            img = background
        buffer = io.BytesIO()
        img.save(buffer, format=fmt, quality=95)
        return buffer.getvalue(), img.size


def convert(tool: str, files: list[Path], output: Path, options: dict,
            cancel: threading.Event, report):
    if not files:
        raise ValueError('请先添加文件。')
    output.mkdir(parents=True, exist_ok=True)
    # A unique run folder avoids overwriting both source files and prior output.
    run = Path(tempfile.mkdtemp(prefix='OfficeTools_', dir=output))
    report(0, f'输出目录：{run}')

    def check():
        if cancel.is_set():
            raise Cancelled('已取消；已完成的文件保留在输出目录。')

    try:
        if tool in ('images_pdf', 'merge_pdf'):
            with pymupdf.open() as result:
                for index, path in enumerate(files):
                    check()
                    if tool == 'merge_pdf':
                        with open_pdf(path) as source:
                            result.insert_pdf(source)
                    else:
                        data, (w, h) = image_bytes(path)
                        if options.get('paper') == 'A4':
                            page = result.new_page(width=595, height=842)
                            rect = pymupdf.Rect(24, 24, 571, 818)
                        else:
                            page = result.new_page(width=w * .75, height=h * .75)
                            rect = page.rect
                        page.insert_image(rect, stream=data, keep_proportion=True)
                    report(int((index + 1) / len(files) * 95), f'已处理：{path.name}')
                check()
                result.save(run / '合并结果.pdf', garbage=4, deflate=True)
        else:
            for index, path in enumerate(files):
                check()
                prefix = f'{index + 1:03d}_{path.stem}'
                if tool == 'image_format':
                    fmt = options.get('format', 'PNG')
                    data, _ = image_bytes(path, 'JPEG' if fmt == 'JPG' else fmt)
                    (run / f'{prefix}.{fmt.lower()}').write_bytes(data)
                elif tool in ('pdf_images', 'pdf_word'):
                    with open_pdf(path) as doc:
                        pages = pages_from_text(options.get('pages', ''), len(doc))
                        if tool == 'pdf_images':
                            for step, p in enumerate(pages):
                                check()
                                page = doc[p]
                                dpi = options.get('dpi', 150)
                                if page.rect.width * page.rect.height * (dpi / 72) ** 2 > 80_000_000:
                                    raise ValueError('页面尺寸过大，请降低 DPI 后重试。')
                                pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
                                pix.save(run / f'{prefix}_p{p + 1:04d}.{options.get("format", "PNG").lower()}')
                                report(int((index + (step + 1) / len(pages)) / len(files) * 100), f'{path.name} · 第 {p + 1} 页')
                        elif any(not doc[p].get_text().strip() for p in pages):
                            raise ValueError('所选页面包含无文字层页面；当前版本不支持扫描件 OCR，请选择文字页面后重试。')
                    if tool == 'pdf_word':
                        from pdf2docx import Converter
                        target = run / f'{prefix}.docx'
                        engine = Converter(str(path))
                        try:
                            engine.convert(str(target), pages=pages, ignore_page_error=False)
                        except Exception:
                            target.unlink(missing_ok=True)
                            raise
                        finally:
                            engine.close()
                else:
                    raise ValueError('未知工具。')
                report(int((index + 1) / len(files) * 100), f'已完成：{path.name}')
        check()
        return run
    except Exception:
        report(0, '任务未全部完成，已生成的文件保留在上述输出目录。')
        raise
