# -*- mode: python ; coding: utf-8 -*-
"""Smaller Windows build while keeping the complete automation feature set.

The application only uses QtCore/QtGui/QtWidgets.  PySide6's hooks otherwise
include optional Qt add-ons (QML, Quick, PDF, SVG, WebEngine, ...), and the
OCR stack exposes optional training/test helpers that are not needed at
runtime.  These exclusions remove those unused modules without removing any
runtime dependency used by app.py.
"""

from PyInstaller.utils.hooks import collect_all
from pathlib import Path
import os


datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all("rapidocr_onnxruntime")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# Keep the bundled fallback font so Chinese labels still render on a clean
# Windows installation without relying on the host's font set.
spec_root = Path.cwd()
font_candidates = [
    spec_root / "assets/fonts/NotoSansSC-VF.ttf",
    Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
]
for font_path in font_candidates:
    if font_path.is_file():
        datas.append((str(font_path), "fonts"))
        break

excludes = [
    # Optional PySide6 bindings not imported by the application.
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtGraphs",
    "PySide6.QtGraphsWidgets",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetwork",
    "PySide6.QtNfc",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtPrintSupport",
    "PySide6.QtQml",
    "PySide6.QtQmlModels",
    "PySide6.QtQmlWorkerScript",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickTest",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialBus",
    "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "PySide6.QtWebView",
    "PySide6.QtXml",
    "PySide6.QtXmlPatterns",
    # Optional ONNX Runtime tooling; inference itself remains bundled.
    "onnxruntime.backend",
    "onnxruntime.datasets",
    "onnxruntime.quantization",
    "onnxruntime.test",
    "onnxruntime.tools",
    "onnxruntime.transformers",
    "onnxruntime.training",
    # Keep numpy.linalg/fft/random: NumPy imports linalg during initialization.
    # Only developer/test helpers can be removed safely.
    "numpy.distutils",
    "numpy.f2py",
    "numpy.testing",
    # Pillow plugins not needed for PNG/JPEG/BMP screenshots and templates.
    "PIL.AvifImagePlugin",
    "PIL.BlpImagePlugin",
    "PIL.BufrStubImagePlugin",
    "PIL.CurImagePlugin",
    "PIL.DcxImagePlugin",
    "PIL.DdsImagePlugin",
    "PIL.EpsImagePlugin",
    "PIL.FitsImagePlugin",
    "PIL.FliImagePlugin",
    "PIL.FpxImagePlugin",
    "PIL.GbrImagePlugin",
    "PIL.GribStubImagePlugin",
    "PIL.Hdf5StubImagePlugin",
    "PIL.IcnsImagePlugin",
    "PIL.ImImagePlugin",
    "PIL.McIdasImagePlugin",
    "PIL.MspImagePlugin",
    "PIL.PcdImagePlugin",
    "PIL.PcxImagePlugin",
    "PIL.PdfImagePlugin",
    "PIL.QoiImagePlugin",
    "PIL.SgiImagePlugin",
    "PIL.SpiderImagePlugin",
    "PIL.SunImagePlugin",
    "PIL.WmfImagePlugin",
    "PIL.XbmImagePlugin",
    "PIL.XpmImagePlugin",
    "PIL.XVThumbImagePlugin",
]


smoke_build = os.environ.get("AUTOMATION_BUILD_SMOKE") == "1"
a = Analysis(
    ["packaging_smoke.py" if smoke_build else "app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=1,
)


def _keep_binary(destination: str) -> bool:
    """Drop large optional native libraries that the app never loads."""
    name = str(destination).replace("\\", "/").lower()
    # PySide6 6.11 works with the Windows ICU/system fallback in this build;
    # an unrelated ICU 78 pair pulled in by optional packages can shadow Qt's
    # own lookup and make Qt6Core fail with WinError 127 at startup.
    if name in {"icuuc.dll", "icudt78.dll"}:
        return False
    exact = {
        "pyside6/qt6network.dll",
        "pyside6/qt6opengl.dll",
        "pyside6/qt6pdf.dll",
        "pyside6/qt6qml.dll",
        "pyside6/qt6qmlmeta.dll",
        "pyside6/qt6qmlmodels.dll",
        "pyside6/qt6qmlworkerscript.dll",
        "pyside6/qt6quick.dll",
        "pyside6/qt6svg.dll",
        "pyside6/qt6virtualkeyboard.dll",
        "pyside6/opengl32sw.dll",
        "pyside6/plugins/generic/qtuiotouchplugin.dll",
        "pyside6/plugins/iconengines/qsvgicon.dll",
        "pyside6/plugins/imageformats/qgif.dll",
        "pyside6/plugins/imageformats/qicns.dll",
        "pyside6/plugins/imageformats/qico.dll",
        "pyside6/plugins/imageformats/qjpeg.dll",
        "pyside6/plugins/imageformats/qpdf.dll",
        "pyside6/plugins/imageformats/qsvg.dll",
        "pyside6/plugins/imageformats/qtga.dll",
        "pyside6/plugins/imageformats/qtiff.dll",
        "pyside6/plugins/imageformats/qwbmp.dll",
        "pyside6/plugins/imageformats/qwebp.dll",
        "pyside6/plugins/platforminputcontexts/qtvirtualkeyboardplugin.dll",
        "pyside6/plugins/platforms/qdirect2d.dll",
        "pyside6/plugins/platforms/qminimal.dll",
        "pyside6/plugins/platforms/qoffscreen.dll",
        "cv2/opencv_videoio_ffmpeg500_64.dll",
        "pil/_avif.cp311-win_amd64.pyd",
        "pil/_imagingtk.cp311-win_amd64.pyd",
        "numpy/_core/_multiarray_tests.cp311-win_amd64.pyd",
    }
    if name in exact:
        return False
    if name.startswith("pyside6/translations/"):
        return False
    return True


a.binaries = [entry for entry in a.binaries if _keep_binary(entry[0])]
a.datas = [entry for entry in a.datas if not str(entry[0]).replace("\\", "/").lower().startswith("pyside6/translations/")]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AutomationTool-package-smoke" if smoke_build else "AutomationTool-small",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
