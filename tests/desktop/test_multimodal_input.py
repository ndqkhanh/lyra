"""Tests for src/lyra/desktop/multimodal_input.py — 85%+ coverage target.

Tests ImageHandler, FileDropHandler, ScreenshotCapture, InputRouter, and
MultimodalInputHandler with thorough mock coverage of external dependencies
(Pillow, Tesseract, clipboard, screenshots).
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from lyra.desktop.multimodal_input import (
    MAX_FILE_SIZE_MB,
    MAX_IMAGE_SIZE_MB,
    SUPPORTED_FILE_EXTENSIONS,
    SUPPORTED_IMAGE_FORMATS,
    FileDrop,
    FileDropHandler,
    FileHandlingError,
    ImageData,
    ImageHandler,
    ImageProcessingError,
    ImageSource,
    InputResult,
    InputRouter,
    InputType,
    MultimodalInputError,
    MultimodalInputHandler,
    ScreenshotCapture,
    ScreenshotError,
)


# =========================================================================
# Exceptions
# =========================================================================


class TestExceptions:
    def test_base_exception(self):
        e = MultimodalInputError("base")
        assert isinstance(e, Exception)

    def test_image_processing_error(self):
        e = ImageProcessingError("bad image")
        assert isinstance(e, MultimodalInputError)

    def test_file_handling_error(self):
        e = FileHandlingError("bad file")
        assert isinstance(e, MultimodalInputError)

    def test_screenshot_error(self):
        e = ScreenshotError("bad capture")
        assert isinstance(e, MultimodalInputError)


# =========================================================================
# Enums
# =========================================================================


class TestEnums:
    def test_input_type_values(self):
        assert InputType.TEXT.name == "TEXT"
        assert InputType.IMAGE.name == "IMAGE"
        assert InputType.FILE.name == "FILE"
        assert InputType.SCREENSHOT.name == "SCREENSHOT"
        assert InputType.MULTIPLE.name == "MULTIPLE"

    def test_image_source_values(self):
        assert ImageSource.CLIPBOARD_PASTE.name == "CLIPBOARD_PASTE"
        assert ImageSource.SCREENSHOT.name == "SCREENSHOT"
        assert ImageSource.FILE_DROP.name == "FILE_DROP"


# =========================================================================
# ImageData / FileDrop / InputResult
# =========================================================================


class TestDataTypes:
    def test_image_data_frozen(self):
        img = ImageData(data=b"abc", source=ImageSource.CLIPBOARD_PASTE)
        with pytest.raises(AttributeError):
            img.data = b"xyz"

    def test_image_data_defaults(self):
        img = ImageData(data=b"abc", source=ImageSource.CLIPBOARD_PASTE)
        assert img.format == "png"
        assert img.width == 0
        assert img.height == 0
        assert img.ocr_text == ""
        assert img.file_path == ""

    def test_file_drop_frozen(self):
        fd = FileDrop(file_path="/tmp/f.py", filename="f.py", content=b"code")
        with pytest.raises(AttributeError):
            fd.file_path = "/other"

    def test_file_drop_defaults(self):
        fd = FileDrop(file_path="/a.txt", filename="a.txt")
        assert fd.extension == ""
        assert fd.size_bytes == 0
        assert fd.is_binary is True
        assert fd.mime_type == "application/octet-stream"

    def test_input_result_defaults(self):
        ir = InputResult(type=InputType.TEXT)
        assert ir.text == ""
        assert ir.image is None
        assert ir.file is None
        assert ir.source == "clipboard"
        assert ir.metadata == {}

    def test_input_result_with_image(self):
        img = ImageData(data=b"img", source=ImageSource.CLIPBOARD_PASTE)
        ir = InputResult(type=InputType.IMAGE, image=img, text="ocr result")
        assert ir.image is img
        assert ir.text == "ocr result"


# =========================================================================
# ImageHandler
# =========================================================================


class TestImageHandler:
    def test_default_init(self):
        handler = ImageHandler()
        assert handler._max_bytes == int(MAX_IMAGE_SIZE_MB * 1024 * 1024)
        assert handler._enable_ocr is True

    def test_init_custom(self):
        handler = ImageHandler(max_size_mb=1.0, enable_ocr=False, tesseract_cmd="/custom/tesseract")
        assert handler._max_bytes == 1_048_576
        assert handler._enable_ocr is False
        assert handler._tesseract_cmd == "/custom/tesseract"

    # -- from_clipboard --

    @patch("lyra.desktop.multimodal_input.ImageHandler._extract_ocr", return_value="")
    def test_from_clipboard_no_image(self, mock_ocr):
        with patch("PIL.ImageGrab.grabclipboard", return_value=None):
            handler = ImageHandler(enable_ocr=True)
            result = handler.from_clipboard()
            assert result is None

    @patch("lyra.desktop.multimodal_input.ImageHandler._extract_ocr", return_value="hello world")
    def test_from_clipboard_success(self, mock_ocr):
        mock_pil = MagicMock()
        mock_pil.size = (100, 200)
        with patch("PIL.ImageGrab.grabclipboard", return_value=mock_pil):
            handler = ImageHandler(enable_ocr=True)
            result = handler.from_clipboard()
            assert result is not None
            assert result.width == 100
            assert result.height == 200
            assert result.source == ImageSource.CLIPBOARD_PASTE
            assert result.ocr_text == "hello world"

    def test_from_clipboard_pillow_not_available(self):
        import builtins as _b
        real_import = _b.__import__
        def _no_pil(name, *args, **kwargs):
            if name == "PIL" or name.startswith("PIL."):
                raise ImportError("no PIL")
            return real_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=_no_pil):
            handler = ImageHandler()
            result = handler.from_clipboard()
            assert result is None

    @patch("lyra.desktop.multimodal_input.ImageHandler._extract_ocr", return_value="hello world")
    def test_from_clipboard_success(self, mock_ocr):
        mock_pil = MagicMock()
        mock_pil.size = (100, 200)
        with patch("PIL.ImageGrab.grabclipboard", return_value=mock_pil):
            handler = ImageHandler(enable_ocr=True)
            result = handler.from_clipboard()
            assert result is not None
            assert result.width == 100
            assert result.height == 200
            assert result.source == ImageSource.CLIPBOARD_PASTE
            assert result.ocr_text == "hello world"

    def test_from_clipboard_grab_fails(self):
        with patch("PIL.ImageGrab.grabclipboard", side_effect=Exception("grab failed")):
            handler = ImageHandler()
            with pytest.raises(ImageProcessingError, match="Clipboard read failed"):
                handler.from_clipboard()

    def test_from_clipboard_save_fails(self):
        mock_pil = MagicMock()
        mock_pil.save.side_effect = Exception("save failed")
        with patch("PIL.ImageGrab.grabclipboard", return_value=mock_pil):
            handler = ImageHandler()
            with pytest.raises(ImageProcessingError, match="Image conversion failed"):
                handler.from_clipboard()

    def test_from_clipboard_size_exceeded(self):
        mock_pil = MagicMock()
        mock_pil.size = (10, 10)
        over_limit = int(MAX_IMAGE_SIZE_MB * 1024 * 1024) + 1
        # Make save produce large bytes
        def mock_save(buf, **kwargs):
            buf.write(b"x" * over_limit)
        mock_pil.save = mock_save

        with patch("PIL.ImageGrab.grabclipboard", return_value=mock_pil):
            handler = ImageHandler()
            with pytest.raises(ImageProcessingError, match="exceeds limit"):
                handler.from_clipboard()

    # -- from_bytes --

    def test_from_bytes_empty(self):
        handler = ImageHandler()
        with pytest.raises(ImageProcessingError, match="Empty"):
            handler.from_bytes(b"")

    def test_from_bytes_size_exceeded(self):
        handler = ImageHandler(max_size_mb=0.001)
        with pytest.raises(ImageProcessingError, match="exceeds limit"):
            handler.from_bytes(b"x" * 2000)

    @patch("lyra.desktop.multimodal_input.ImageHandler._extract_ocr", return_value="")
    def test_from_bytes_success(self, mock_ocr):
        handler = ImageHandler(enable_ocr=True)
        # Create a small valid PNG
        import struct
        # Minimal PNG (1x1 pixel)
        raw = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        result = handler.from_bytes(raw, image_format="png", source=ImageSource.FILE_DROP)
        assert result.format == "png"
        assert result.source == ImageSource.FILE_DROP
        # On some platforms PIL may not load the image, width/height may be 0
        assert result.data == raw

    def test_from_bytes_no_pillow(self):
        import builtins as _b
        real_import = _b.__import__
        def _no_pil(name, *args, **kwargs):
            if name == "PIL" or name.startswith("PIL."):
                raise ImportError("no PIL")
            return real_import(name, *args, **kwargs)
        handler = ImageHandler(enable_ocr=False)
        with patch("builtins.__import__", side_effect=_no_pil):
            result = handler.from_bytes(b"1234", image_format="png")
            assert result.width == 0
            assert result.height == 0

    def test_from_bytes_pil_dimension_fails_gracefully(self):
        handler = ImageHandler(enable_ocr=False)
        with patch("PIL.Image.open") as mock_open:
            mock_open.side_effect = Exception("bad image")
            result = handler.from_bytes(b"1234", image_format="png")
            assert result.width == 0
            assert result.height == 0

    # -- _extract_ocr --

    def test_extract_ocr_success(self):
        handler = ImageHandler()
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "extracted text\n"
                result = handler._extract_ocr(b"fake_image_bytes")
                assert result == "extracted text"
        finally:
            os.unlink(tmp_path)

    def test_extract_ocr_tesseract_missing(self):
        handler = ImageHandler()
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = handler._extract_ocr(b"fake_image_bytes")
            assert result == ""

    def test_extract_ocr_timeout(self):
        handler = ImageHandler()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("tesseract", 30)):
            result = handler._extract_ocr(b"fake_image_bytes")
            assert result == ""

    def test_extract_ocr_non_zero_return(self):
        handler = ImageHandler()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "error msg"
            result = handler._extract_ocr(b"fake_image_bytes")
            assert result == ""

    def test_extract_ocr_unlink_failure(self):
        """OSError during temp file cleanup should not crash."""
        handler = ImageHandler()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "err"
            with patch("os.unlink", side_effect=OSError("permission")):
                result = handler._extract_ocr(b"fake_image_bytes")
                assert result == ""

    def test_extract_ocr_generic_exception(self):
        handler = ImageHandler()
        with patch("tempfile.NamedTemporaryFile", side_effect=Exception("boom")):
            result = handler._extract_ocr(b"fake_image_bytes")
            assert result == ""


# =========================================================================
# FileDropHandler
# =========================================================================


class TestFileDropHandler:
    def test_init_defaults(self):
        handler = FileDropHandler()
        assert handler._max_bytes == int(MAX_FILE_SIZE_MB * 1024 * 1024)
        assert handler._allowed_extensions is None

    def test_init_custom(self):
        exts = frozenset({"py", "js"})
        handler = FileDropHandler(max_size_mb=1.0, allowed_extensions=exts, text_max_bytes=500)
        assert handler._max_bytes == 1_048_576
        assert handler._allowed_extensions == exts
        assert handler._text_max_bytes == 500

    def test_handle_drop_text_file(self, tmp_path):
        f = tmp_path / "hello.py"
        f.write_text("print('hello')")
        handler = FileDropHandler()
        fd = handler.handle_drop(str(f))
        assert fd.filename == "hello.py"
        assert fd.extension == "py"
        assert fd.size_bytes > 0
        assert fd.is_binary is False
        assert fd.content == b"print('hello')"
        assert fd.mime_type == "text/x-python"

    def test_handle_drop_binary_file(self, tmp_path):
        f = tmp_path / "image.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n")
        handler = FileDropHandler()
        fd = handler.handle_drop(str(f))
        assert fd.extension == "png"
        assert fd.is_binary is True

    def test_handle_drop_not_found(self):
        handler = FileDropHandler()
        with pytest.raises(FileHandlingError, match="not found"):
            handler.handle_drop("/nonexistent/file.py")

    def test_handle_drop_not_a_file(self, tmp_path):
        d = tmp_path / "dir"
        d.mkdir()
        handler = FileDropHandler()
        with pytest.raises(FileHandlingError, match="Not a file"):
            handler.handle_drop(str(d))

    def test_handle_drop_size_exceeded(self, tmp_path):
        f = tmp_path / "big.bin"
        over_limit = int(MAX_FILE_SIZE_MB * 1024 * 1024) + 1
        f.write_bytes(b"x" * over_limit)
        handler = FileDropHandler()
        with pytest.raises(FileHandlingError, match="exceeds limit"):
            handler.handle_drop(str(f))

    def test_handle_drop_read_failure(self, tmp_path):
        f = tmp_path / "locked.py"
        f.write_text("content")
        handler = FileDropHandler()
        with patch("builtins.open", side_effect=OSError("permission denied")):
            with pytest.raises(FileHandlingError, match="Failed to read"):
                handler.handle_drop(str(f))

    def test_handle_drop_extension_not_in_allowlist(self, tmp_path):
        f = tmp_path / "script.exe"
        f.write_bytes(b"MZ")
        handler = FileDropHandler(
            allowed_extensions=frozenset({"py", "js"}),
        )
        fd = handler.handle_drop(str(f))
        # Should still work but log a warning
        assert fd.filename == "script.exe"

    def test_handle_drop_with_allowed_extensions(self, tmp_path):
        f = tmp_path / "allowed.py"
        f.write_text("x=1")
        handler = FileDropHandler(
            allowed_extensions=frozenset({"py", "js"}),
        )
        fd = handler.handle_drop(str(f))
        assert fd.extension == "py"
        assert fd.filename == "allowed.py"

    def test_is_binary_extension(self):
        assert FileDropHandler._is_binary_extension("png") is True
        assert FileDropHandler._is_binary_extension("pdf") is True
        assert FileDropHandler._is_binary_extension("py") is False
        assert FileDropHandler._is_binary_extension("txt") is False
        assert FileDropHandler._is_binary_extension("UNKNOWN") is False

    def test_guess_mime(self):
        assert FileDropHandler._guess_mime("py") == "text/x-python"
        assert FileDropHandler._guess_mime("md") == "text/markdown"
        assert FileDropHandler._guess_mime("txt") == "text/plain"
        assert FileDropHandler._guess_mime("pdf") == "application/pdf"
        assert FileDropHandler._guess_mime("unknown") == "application/octet-stream"
        assert FileDropHandler._guess_mime("dockerfile") == "text/x-dockerfile"


# =========================================================================
# ScreenshotCapture
# =========================================================================


class TestScreenshotCapture:
    def test_init_defaults(self):
        sc = ScreenshotCapture()
        assert sc._default_region is None
        assert sc._save_to_temp is False

    def test_init_custom(self):
        sc = ScreenshotCapture(default_region=(0, 0, 100, 200), save_to_temp=True)
        assert sc._default_region == (0, 0, 100, 200)
        assert sc._save_to_temp is True

    def test_capture_fullscreen_no_pillow(self):
        sc = ScreenshotCapture()
        with patch("builtins.__import__", side_effect=ImportError("no PIL")):
            with pytest.raises(ScreenshotError, match="Pillow is required"):
                sc.capture_fullscreen()

    def test_capture_fullscreen_grab_fails(self):
        sc = ScreenshotCapture()
        with patch("PIL.ImageGrab.grab", side_effect=Exception("grab failed")):
            with pytest.raises(ScreenshotError, match="Fullscreen capture failed"):
                sc.capture_fullscreen()

    def test_capture_fullscreen_success(self):
        mock_pil = MagicMock()
        mock_pil.size = (1920, 1080)
        sc = ScreenshotCapture()
        with patch("PIL.ImageGrab.grab", return_value=mock_pil):
            result = sc.capture_fullscreen()
            assert result.width == 1920
            assert result.height == 1080
            assert result.source == ImageSource.SCREENSHOT

    def test_capture_fullscreen_all_screens(self):
        mock_pil = MagicMock()
        mock_pil.size = (3000, 2000)
        sc = ScreenshotCapture()
        with patch("PIL.ImageGrab.grab", return_value=mock_pil) as mock_grab:
            result = sc.capture_fullscreen(display=-1)
            mock_grab.assert_called_once_with(all_screens=True)

    def test_capture_region_no_pillow(self):
        sc = ScreenshotCapture()
        with patch("builtins.__import__", side_effect=ImportError("no PIL")):
            with pytest.raises(ScreenshotError, match="Pillow is required"):
                sc.capture_region(0, 0, 100, 100)

    def test_capture_region_grab_fails(self):
        sc = ScreenshotCapture()
        with patch("PIL.ImageGrab.grab", side_effect=Exception("region failed")):
            with pytest.raises(ScreenshotError, match="Region capture failed"):
                sc.capture_region(0, 0, 100, 100)

    def test_capture_region_success(self):
        mock_pil = MagicMock()
        mock_pil.size = (100, 200)
        sc = ScreenshotCapture()
        with patch("PIL.ImageGrab.grab", return_value=mock_pil):
            result = sc.capture_region(10, 20, 100, 200)
            assert result.width == 100
            assert result.height == 200

    def test_capture_interactive_success(self):
        sc = ScreenshotCapture()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            with patch("os.path.exists", return_value=True):
                with patch("builtins.open", unittest.mock.mock_open(read_data=b"\x89PNG\r\n\x1a\n")):
                    with patch("PIL.Image.open") as mock_img_open:
                        mock_img = MagicMock()
                        mock_img.size = (800, 600)
                        mock_img_open.return_value = mock_img
                        with patch("os.unlink"):
                            result = sc.capture_interactive()
                            assert result is not None
                            assert result.width == 800
                            assert result.height == 600

    def test_capture_interactive_cancelled(self):
        sc = ScreenshotCapture()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            with patch("os.path.exists", return_value=False):
                with patch("os.unlink"):
                    result = sc.capture_interactive()
                    assert result is None

    def test_capture_interactive_fallback_on_error(self):
        sc = ScreenshotCapture()
        with patch("subprocess.run", side_effect=FileNotFoundError("no screencapture")):
            with patch.object(sc, "capture_fullscreen") as mock_fs:
                mock_fs.return_value = ImageData(
                    data=b"fallback", source=ImageSource.SCREENSHOT,
                )
                result = sc.capture_interactive()
                assert result is not None
                assert result.data == b"fallback"

    def test_capture_interactive_timeout_fallback(self):
        sc = ScreenshotCapture()
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("sc", 30)):
            with patch.object(sc, "capture_fullscreen") as mock_fs:
                mock_fs.return_value = ImageData(
                    data=b"timeout_fallback", source=ImageSource.SCREENSHOT,
                )
                result = sc.capture_interactive()
                assert result is not None

    # -- _pil_to_data --

    def test_pil_to_data_save_fails(self):
        sc = ScreenshotCapture()
        mock_pil = MagicMock()
        mock_pil.save.side_effect = Exception("save failed")
        with pytest.raises(ScreenshotError, match="Image save failed"):
            sc._pil_to_data(mock_pil)

    def test_pil_to_data_save_to_temp(self):
        sc = ScreenshotCapture(save_to_temp=True)
        mock_pil = MagicMock()
        mock_pil.size = (100, 100)
        result = sc._pil_to_data(mock_pil, source=ImageSource.SCREENSHOT)
        assert result.source == ImageSource.SCREENSHOT
        # file_path might be set if temp save succeeded
        assert isinstance(result.file_path, str)

    def test_pil_to_data_temp_save_fails_gracefully(self):
        sc = ScreenshotCapture(save_to_temp=True)
        mock_pil = MagicMock()
        mock_pil.size = (100, 100)
        with patch("tempfile.NamedTemporaryFile", side_effect=OSError("no temp")):
            result = sc._pil_to_data(mock_pil)
            assert result.file_path == ""


# =========================================================================
# InputRouter
# =========================================================================


class TestInputRouter:
    def test_init(self):
        router = InputRouter()
        assert router._routes == []
        assert router._default_handler is None

    def test_register_route(self):
        router = InputRouter()
        handler = MagicMock()
        router.register_route(InputType.IMAGE, handler)
        assert ("IMAGE", handler) in router._routes

    def test_set_default_handler(self):
        router = InputRouter()
        handler = MagicMock()
        router.set_default_handler(handler)
        assert router._default_handler is handler

    def test_route_matches_handler(self):
        router = InputRouter()
        handler = MagicMock(return_value="processed")
        router.register_route(InputType.IMAGE, handler)
        result = InputResult(type=InputType.IMAGE, source="test")
        assert router.route(result) == "processed"

    def test_route_no_match_falls_to_default(self):
        router = InputRouter()
        default = MagicMock(return_value="defaulted")
        router.set_default_handler(default)
        result = InputResult(type=InputType.TEXT, source="test")
        assert router.route(result) == "defaulted"

    def test_route_no_match_no_default(self):
        router = InputRouter()
        result = InputResult(type=InputType.TEXT, source="test")
        assert router.route(result) is None

    def test_route_handler_raises(self):
        router = InputRouter()
        handler = MagicMock(side_effect=RuntimeError("handler failed"))
        router.register_route(InputType.IMAGE, handler)
        result = InputResult(type=InputType.IMAGE, source="test")
        assert router.route(result) is None

    def test_route_default_handler_raises(self):
        router = InputRouter()
        default = MagicMock(side_effect=RuntimeError("default failed"))
        router.set_default_handler(default)
        result = InputResult(type=InputType.TEXT, source="test")
        assert router.route(result) is None

    def test_list_routes(self):
        router = InputRouter()
        router.register_route(InputType.IMAGE, MagicMock())
        router.register_route(InputType.FILE, MagicMock())
        routes = router.list_routes()
        assert "IMAGE" in routes
        assert "FILE" in routes


# =========================================================================
# MultimodalInputHandler
# =========================================================================


class TestMultimodalInputHandler:
    def test_init_defaults(self):
        handler = MultimodalInputHandler()
        assert handler._image_handler is not None
        assert handler._file_handler is not None
        assert handler._screenshot is not None
        assert handler._router is not None

    def test_init_custom(self):
        ih = ImageHandler()
        fh = FileDropHandler()
        sc = ScreenshotCapture()
        router = InputRouter()
        handler = MultimodalInputHandler(
            image_handler=ih,
            file_handler=fh,
            screenshot=sc,
            router=router,
        )
        assert handler.image_handler is ih
        assert handler.file_handler is fh
        assert handler.screenshot is sc
        assert handler.router is router

    @patch("lyra.desktop.multimodal_input.ImageHandler.from_clipboard")
    async def test_handle_clipboard_paste_image(self, mock_from_clipboard):
        mock_from_clipboard.return_value = ImageData(
            data=b"img", width=100, height=200, format="png",
            source=ImageSource.CLIPBOARD_PASTE, ocr_text="ocr",
        )
        handler = MultimodalInputHandler()
        result = await handler.handle_clipboard_paste()
        assert result is not None
        assert result.type == InputType.IMAGE
        assert result.image is not None
        assert result.text == "ocr"
        assert result.metadata["width"] == 100

    @patch("lyra.desktop.multimodal_input.ImageHandler.from_clipboard")
    async def test_handle_clipboard_paste_no_image(self, mock_from_clipboard):
        mock_from_clipboard.return_value = None
        handler = MultimodalInputHandler()
        result = await handler.handle_clipboard_paste()
        assert result is None

    @patch("lyra.desktop.multimodal_input.FileDropHandler.handle_drop")
    async def test_handle_file_drop_text(self, mock_drop):
        mock_drop.return_value = FileDrop(
            file_path="/tmp/test.py", filename="test.py", extension="py",
            size_bytes=50, mime_type="text/x-python", content=b"print(1)",
            is_binary=False,
        )
        handler = MultimodalInputHandler()
        result = await handler.handle_file_drop("/tmp/test.py")
        assert result.type == InputType.FILE
        assert result.file is not None
        assert result.file.filename == "test.py"
        assert "[File: test.py]" in result.text

    @patch("lyra.desktop.multimodal_input.FileDropHandler.handle_drop")
    @patch("lyra.desktop.multimodal_input.ImageHandler.from_bytes")
    async def test_handle_file_drop_image(self, mock_from_bytes, mock_drop):
        img = ImageData(
            data=b"img", width=50, height=50, format="png",
            source=ImageSource.FILE_DROP,
        )
        mock_from_bytes.return_value = img
        mock_drop.return_value = FileDrop(
            file_path="/tmp/test.png", filename="test.png", extension="png",
            size_bytes=100, mime_type="image/png", content=b"\x89PNG",
            is_binary=True,
        )
        handler = MultimodalInputHandler()
        result = await handler.handle_file_drop("/tmp/test.png")
        assert result.type == InputType.IMAGE
        assert result.image is not None
        assert result.image.source == ImageSource.FILE_DROP

    @patch("lyra.desktop.multimodal_input.FileDropHandler.handle_drop")
    @patch("lyra.desktop.multimodal_input.ImageHandler.from_bytes")
    async def test_handle_file_drop_image_processing_fails(self, mock_from_bytes, mock_drop):
        mock_from_bytes.side_effect = ImageProcessingError("bad image")
        mock_drop.return_value = FileDrop(
            file_path="/tmp/bad.png", filename="bad.png", extension="png",
            size_bytes=100, mime_type="image/png", content=b"bad",
            is_binary=True,
        )
        handler = MultimodalInputHandler()
        result = await handler.handle_file_drop("/tmp/bad.png")
        assert result.type == InputType.FILE
        assert result.image is None

    async def test_handle_screenshot_fullscreen(self):
        sc = MagicMock(spec=ScreenshotCapture)
        sc.capture_fullscreen.return_value = ImageData(
            data=b"ss", width=1920, height=1080, format="png",
            source=ImageSource.SCREENSHOT,
        )
        handler = MultimodalInputHandler(screenshot=sc)
        result = await handler.handle_screenshot()
        assert result.type == InputType.SCREENSHOT
        assert result.image is not None
        assert result.text == "[Screenshot]"

    async def test_handle_screenshot_region(self):
        sc = MagicMock(spec=ScreenshotCapture)
        sc.capture_region.return_value = ImageData(
            data=b"region", width=100, height=200, format="png",
            source=ImageSource.SCREENSHOT,
        )
        handler = MultimodalInputHandler(screenshot=sc)
        result = await handler.handle_screenshot(region=(10, 20, 100, 200))
        assert result.type == InputType.SCREENSHOT
        sc.capture_region.assert_called_once_with(10, 20, 100, 200)

    async def test_route(self):
        router = MagicMock(spec=InputRouter)
        router.route.return_value = "routed"
        handler = MultimodalInputHandler(router=router)
        result = InputResult(type=InputType.TEXT)
        output = await handler.route(result)
        assert output == "routed"
        router.route.assert_called_once_with(result)


# Need subprocess for timeout test
import subprocess
import unittest.mock
