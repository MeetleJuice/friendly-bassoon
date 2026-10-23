"""Render the owned SVG into a Windows multi-resolution PNG-compressed ICO."""

import os
from pathlib import Path
import struct
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    assert app
    root = Path(__file__).resolve().parents[1] / "aigentics" / "assets"
    renderer = QSvgRenderer(str(root / "icon.svg"))
    if not renderer.isValid():
        raise RuntimeError("Icon SVG failed to render")
    sizes, images = (16, 24, 32, 48, 64, 128, 256), []
    for size in sizes:
        image = QImage(size, size, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.WriteOnly)
        if not image.save(buffer, "PNG"):
            raise RuntimeError("Icon PNG failed to encode")
        images.append(bytes(data))
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset, entries = 6 + 16 * len(sizes), []
    for size, payload in zip(sizes, images):
        entries.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(payload), offset))
        offset += len(payload)
    (root / "icon.ico").write_bytes(header + b"".join(entries) + b"".join(images))
    print("Generated icon.ico with", len(sizes), "resolutions")


if __name__ == "__main__":
    main()
