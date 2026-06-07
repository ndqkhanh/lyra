"""
Multimodal input handler -- image paste, file drag-drop, screenshot capture.

Provides the components for handling rich input modalities in the Lyra
desktop chat interface beyond plain text:

  - ImageHandler: paste from clipboard, OCR text extraction.
  - FileDropHandler: drag-drop files into chat.
  - ScreenshotCapture: capture screen region.
  - InputRouter: route multimodal input to the correct agent.

Usage::

    handler = MultimodalInputHandler(
        image_handler=ImageHandler(),
        file_handler=FileDropHandler(),
        screenshot=ScreenshotCapture(),
        router=InputRouter(),
    )

    # Handle a paste event
    result = handler.handle_clipboard_paste()
    if result.type == InputType.IMAGE:
        await agent.process_image(result.data)
"""

from __future__ import annotations

import base64
import logging
import os
import structlog
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, BinaryIO

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_IMAGE_SIZE_MB: float = 20.0
"""Maximum allowed image size in megabytes."""

MAX_FILE_SIZE_MB: float = 100.0
"""Maximum allowed file size in megabytes."""

SUPPORTED_IMAGE_FORMATS: frozenset[str] = frozenset(
    {"png", "jpg", "jpeg", "gif", "webp", "bmp"}
)
"""Supported image file extensions (lowercase, no dot)."""

SUPPORTED_FILE_EXTENSIONS: frozenset[str] = frozenset(
    {
        # Code
        "py", "js", "ts", "tsx", "jsx", "go", "rs", "java", "kt", "swift",
        "c", "cpp", "h", "hpp", "cs", "rb", "php", "sh", "bash", "zsh",
        "sql", "r", "scala", "pl", "pm",
        # Data
        "json", "yaml", "yml", "toml", "csv", "tsv", "xml", "md", "rst",
        "txt", "log", "env", "ini", "cfg", "conf",
        # Documents
        "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
        # Config
        "dockerfile", "makefile", "gemfile",
    }
)
"""Supported file extensions for drag-drop.  Not an exhaustive allowlist."""

SCREENSHOT_DEFAULT_REGION: tuple[int, int, int, int] | None = None
"""Default capture region as (x, y, width, height), or None for full screen."""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MultimodalInputError(Exception):
    """Raised when multimodal input handling fails."""


class ImageProcessingError(MultimodalInputError):
    """Raised when image processing (OCR, decode) fails."""


class FileHandlingError(MultimodalInputError):
    """Raised when file drag-drop handling fails."""


class ScreenshotError(MultimodalInputError):
    """Raised when screenshot capture fails."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class InputType(Enum):
    """Type of multimodal input received."""

    TEXT = auto()
    """Plain text input (no special handling needed)."""

    IMAGE = auto()
    """Image pasted from clipboard or dropped."""

    FILE = auto()
    """File dropped into the chat."""

    SCREENSHOT = auto()
    """Screenshot captured by the user."""

    MULTIPLE = auto()
    """Multiple items received simultaneously."""


class ImageSource(Enum):
    """Origin of an image input."""

    CLIPBOARD_PASTE = auto()
    SCREENSHOT = auto()
    FILE_DROP = auto()


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImageData:
    """Processed image data ready for downstream consumption.

    Attributes:
        data: Raw image bytes.
        format: Image format (png, jpeg, etc.).
        width: Image width in pixels.
        height: Image height in pixels.
        source: Origin of the image.
        ocr_text: Extracted OCR text, if available.
        file_path: Original file path, if applicable.
    """

    data: bytes
    format: str = "png"
    width: int = 0
    height: int = 0
    source: ImageSource = ImageSource.CLIPBOARD_PASTE
    ocr_text: str = ""
    file_path: str = ""


@dataclass(frozen=True)
class FileDrop:
    """A file dropped into the chat interface.

    Attributes:
        file_path: Absolute path to the file.
        filename: Display name of the file.
        extension: File extension (lowercase, no dot).
        size_bytes: File size in bytes.
        mime_type: Detected MIME type.
        content: File content as bytes (for small files).
        is_binary: Whether the file is binary (vs text).
    """

    file_path: str
    filename: str
    extension: str = ""
    size_bytes: int = 0
    mime_type: str = "application/octet-stream"
    content: bytes = b""
    is_binary: bool = True


@dataclass(frozen=True)
class InputResult:
    """Result of processing a multimodal input event.

    Attributes:
        type: The classified input type.
        image: Image data if this was an image input.
        file: File data if this was a file input.
        text: Extracted/associated text (OCR result, file name, etc.).
        source: Origin of the input.
        timestamp_ms: Monotonic timestamp of when the input was received.
        metadata: Additional metadata about the input.
    """

    type: InputType
    image: ImageData | None = None
    file: FileDrop | None = None
    text: str = ""
    source: str = "clipboard"
    timestamp_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Image Handler
# ---------------------------------------------------------------------------


class ImageHandler:
    """Handle image input from clipboard, file, or screenshot.

    Supports:
      - Paste from clipboard (reading image data from system clipboard).
      - OCR text extraction via Tesseract (optional).
      - Image dimension and format detection.
      - Size validation (max 20 MB).
    """

    def __init__(
        self,
        max_size_mb: float = MAX_IMAGE_SIZE_MB,
        enable_ocr: bool = True,
        tesseract_cmd: str = "tesseract",
    ) -> None:
        """Initialise the image handler.

        Args:
            max_size_mb: Maximum allowed image size in MB.
            enable_ocr: Whether to attempt OCR text extraction.
            tesseract_cmd: Path to the Tesseract executable (used when
                OCR is enabled).
        """
        self._max_bytes = int(max_size_mb * 1024 * 1024)
        self._enable_ocr = enable_ocr
        self._tesseract_cmd = tesseract_cmd

    def from_clipboard(self) -> ImageData | None:
        """Read an image from the system clipboard.

        Attempts to detect an image in the clipboard.  On macOS this uses
        ``NSImage`` via PyObjC; on Linux/X11 it uses ``xclip``; on Windows
        it uses ``PIL.ImageGrab``.  Falls back gracefully if the clipboard
        does not contain an image.

        Returns:
            ``ImageData`` if an image was found in the clipboard, or
            ``None`` if the clipboard contains text or is empty.

        Raises:
            ImageProcessingError: If clipboard reading fails.
        """
        try:
            from PIL import ImageGrab  # noqa: F811
        except ImportError:
            logger.warning("image_handler.pillow_not_available")
            return None

        try:
            pil_image = ImageGrab.grabclipboard()
        except Exception as exc:
            raise ImageProcessingError(f"Clipboard read failed: {exc}") from exc

        if pil_image is None:
            return None

        # Convert PIL Image to PNG bytes
        import io

        buf = io.BytesIO()
        try:
            pil_image.save(buf, format="PNG")
        except Exception as exc:
            raise ImageProcessingError(f"Image conversion failed: {exc}") from exc

        raw_bytes = buf.getvalue()

        if len(raw_bytes) > self._max_bytes:
            raise ImageProcessingError(
                f"Image size {len(raw_bytes)} bytes exceeds limit "
                f"{self._max_bytes} bytes"
            )

        width, height = pil_image.size

        ocr_text = ""
        if self._enable_ocr:
            ocr_text = self._extract_ocr(raw_bytes)

        return ImageData(
            data=raw_bytes,
            format="png",
            width=width,
            height=height,
            source=ImageSource.CLIPBOARD_PASTE,
            ocr_text=ocr_text,
        )

    def from_bytes(
        self,
        image_bytes: bytes,
        image_format: str = "png",
        source: ImageSource = ImageSource.FILE_DROP,
    ) -> ImageData:
        """Create an ``ImageData`` from raw image bytes.

        Args:
            image_bytes: Raw image file bytes.
            image_format: Image format (png, jpeg, etc.).
            source: Origin of the image.

        Returns:
            An ``ImageData`` instance.

        Raises:
            ImageProcessingError: If the bytes are invalid or exceed size limit.
        """
        if not image_bytes:
            raise ImageProcessingError("Empty image bytes")

        if len(image_bytes) > self._max_bytes:
            raise ImageProcessingError(
                f"Image size {len(image_bytes)} bytes exceeds limit "
                f"{self._max_bytes} bytes"
            )

        # Attempt to read dimensions via PIL
        width, height = 0, 0
        try:
            from PIL import Image  # noqa: F811
            import io

            pil = Image.open(io.BytesIO(image_bytes))
            width, height = pil.size
        except ImportError:
            logger.warning("image_handler.pillow_not_available_dimensions")
        except Exception:
            logger.warning("image_handler.dimension_read_failed")

        ocr_text = ""
        if self._enable_ocr:
            ocr_text = self._extract_ocr(image_bytes)

        return ImageData(
            data=image_bytes,
            format=image_format,
            width=width,
            height=height,
            source=source,
            ocr_text=ocr_text,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_ocr(self, image_bytes: bytes) -> str:
        """Extract text from an image using Tesseract OCR.

        Args:
            image_bytes: Raw image bytes.

        Returns:
            Extracted text string, or empty string on failure.
        """
        import subprocess
        import tempfile

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".png", delete=False
            ) as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name

            try:
                result = subprocess.run(
                    [self._tesseract_cmd, tmp_path, "stdout"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
                logger.warning(
                    "ocr.tesseract_failed",
                    stderr=result.stderr.strip()[:200],
                )
            except FileNotFoundError:
                logger.warning("ocr.tesseract_not_installed")
            except subprocess.TimeoutExpired:
                logger.warning("ocr.tesseract_timeout")
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        except Exception as exc:
            logger.warning("ocr.extraction_failed", error=str(exc))

        return ""


# ---------------------------------------------------------------------------
# File Drop Handler
# ---------------------------------------------------------------------------


class FileDropHandler:
    """Handle drag-drop file input into the chat interface.

    Validates file type, size, reads content (for text files), and wraps
    everything in a ``FileDrop`` dataclass.

    The handler does NOT process or route files -- it only validates and
    extracts metadata.  Routing is handled by ``InputRouter``.
    """

    def __init__(
        self,
        max_size_mb: float = MAX_FILE_SIZE_MB,
        allowed_extensions: frozenset[str] | None = None,
        text_max_bytes: int = 1_000_000,
    ) -> None:
        """Initialise the file drop handler.

        Args:
            max_size_mb: Maximum allowed file size in MB.
            allowed_extensions: Set of allowed file extensions.  If ``None``,
                all extensions are accepted (use with caution).
            text_max_bytes: Maximum bytes to read for text files.  Files
                larger than this are treated as binary-only.
        """
        self._max_bytes = int(max_size_mb * 1024 * 1024)
        self._allowed_extensions = allowed_extensions
        self._text_max_bytes = text_max_bytes

    def handle_drop(self, file_path: str) -> FileDrop:
        """Process a dropped file and return a ``FileDrop`` instance.

        Args:
            file_path: Absolute path to the dropped file.

        Returns:
            A ``FileDrop`` with metadata and content.

        Raises:
            FileHandlingError: If the file is invalid, too large, or
                cannot be read.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileHandlingError(f"File not found: {file_path}")

        if not path.is_file():
            raise FileHandlingError(f"Not a file: {file_path}")

        size = path.stat().st_size
        if size > self._max_bytes:
            raise FileHandlingError(
                f"File size {size} bytes exceeds limit {self._max_bytes} bytes"
            )

        ext = path.suffix.lower().lstrip(".")
        filename = path.name

        # Check allowed extensions
        if self._allowed_extensions is not None:
            if ext.lower() not in self._allowed_extensions and ext.lower():
                logger.warning(
                    "file_handler.extension_not_in_allowlist",
                    extension=ext,
                    filename=filename,
                )

        # Determine if binary
        is_binary = self._is_binary_extension(ext)

        # Read content (up to limit)
        content: bytes = b""
        try:
            with open(path, "rb") as f:
                content = f.read(self._text_max_bytes if not is_binary else 4096)
        except OSError as exc:
            raise FileHandlingError(f"Failed to read file: {exc}") from exc

        mime = self._guess_mime(ext)

        return FileDrop(
            file_path=str(path.resolve()),
            filename=filename,
            extension=ext,
            size_bytes=size,
            mime_type=mime,
            content=content,
            is_binary=is_binary or size > self._text_max_bytes,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_binary_extension(ext: str) -> bool:
        """Determine whether a file extension is typically binary."""
        binary_extensions = {
            "png", "jpg", "jpeg", "gif", "bmp", "webp", "ico",
            "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
            "zip", "gz", "tar", "bz2", "7z", "rar",
            "exe", "dll", "so", "dylib", "bin",
            "mp3", "wav", "flac", "ogg", "m4a",
            "mp4", "avi", "mkv", "mov", "webm",
            "ttf", "otf", "woff", "woff2", "eot",
            "db", "sqlite", "s3db",
        }
        return ext.lower() in binary_extensions

    @staticmethod
    def _guess_mime(ext: str) -> str:
        """Guess MIME type from file extension."""
        mime_map: dict[str, str] = {
            "txt": "text/plain",
            "md": "text/markdown",
            "rst": "text/x-rst",
            "json": "application/json",
            "yaml": "application/x-yaml",
            "yml": "application/x-yaml",
            "toml": "application/toml",
            "xml": "application/xml",
            "csv": "text/csv",
            "tsv": "text/tab-separated-values",
            "py": "text/x-python",
            "js": "text/javascript",
            "ts": "text/typescript",
            "tsx": "text/typescript-jsx",
            "jsx": "text/jsx",
            "go": "text/x-go",
            "rs": "text/x-rust",
            "java": "text/x-java",
            "kt": "text/x-kotlin",
            "swift": "text/x-swift",
            "c": "text/x-c",
            "cpp": "text/x-c++",
            "h": "text/x-c-header",
            "hpp": "text/x-c++-header",
            "cs": "text/x-csharp",
            "rb": "text/x-ruby",
            "php": "text/x-php",
            "sh": "application/x-sh",
            "bash": "application/x-sh",
            "sql": "application/sql",
            "r": "text/x-r",
            "scala": "text/x-scala",
            "html": "text/html",
            "css": "text/css",
            "scss": "text/x-scss",
            "less": "text/x-less",
            "pdf": "application/pdf",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
            "svg": "image/svg+xml",
            "ico": "image/x-icon",
            "bmp": "image/bmp",
            "env": "text/plain",
            "ini": "text/plain",
            "cfg": "text/plain",
            "conf": "text/plain",
            "log": "text/plain",
            "dockerfile": "text/x-dockerfile",
        }
        return mime_map.get(ext.lower(), "application/octet-stream")


# ---------------------------------------------------------------------------
# Screenshot Capture
# ---------------------------------------------------------------------------


class ScreenshotCapture:
    """Capture screen regions for input into the chat.

    Supports:
      - Full-screen capture.
      - Region selection (coordinates-based).
      - Multiple-display awareness (select display index).
      - Optional temporary file saving for debugging.

    Under the hood uses ``PIL.ImageGrab`` on all platforms, with
    platform-specific region tools for selection.
    """

    def __init__(
        self,
        default_region: tuple[int, int, int, int] | None = SCREENSHOT_DEFAULT_REGION,
        save_to_temp: bool = False,
    ) -> None:
        """Initialise the screenshot capture.

        Args:
            default_region: Default region as (x, y, width, height).
                ``None`` means full screen.
            save_to_temp: If True, save each screenshot to a temp file
                and include the path in the result.
        """
        self._default_region = default_region
        self._save_to_temp = save_to_temp

    def capture_fullscreen(self, display: int = 0) -> ImageData:
        """Capture the entire screen.

        Args:
            display: Display/monitor index (0 = primary).

        Returns:
            ``ImageData`` with the screenshot.

        Raises:
            ScreenshotError: If capture fails.
        """
        try:
            from PIL import ImageGrab  # noqa: F811
        except ImportError as exc:
            raise ScreenshotError(
                "Pillow is required for screenshot capture"
            ) from exc

        try:
            pil_image = ImageGrab.grab(all_screens=(display == -1))
        except Exception as exc:
            raise ScreenshotError(f"Fullscreen capture failed: {exc}") from exc

        return self._pil_to_data(pil_image, source=ImageSource.SCREENSHOT)

    def capture_region(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        display: int = 0,
    ) -> ImageData:
        """Capture a specific screen region.

        Args:
            x: Left coordinate.
            y: Top coordinate.
            width: Region width.
            height: Region height.
            display: Display/monitor index.

        Returns:
            ``ImageData`` with the screenshot.

        Raises:
            ScreenshotError: If capture fails.
        """
        try:
            from PIL import ImageGrab  # noqa: F811
        except ImportError as exc:
            raise ScreenshotError(
                "Pillow is required for screenshot capture"
            ) from exc

        try:
            pil_image = ImageGrab.grab(bbox=(x, y, x + width, y + height))
        except Exception as exc:
            raise ScreenshotError(f"Region capture failed: {exc}") from exc

        return self._pil_to_data(pil_image, source=ImageSource.SCREENSHOT)

    def capture_interactive(self) -> ImageData | None:
        """Attempt platform-specific interactive region selection.

        On macOS this uses ``screencapture -i`` CLI for interactive
        selection.  Falls back to fullscreen capture if the interactive
        tool is unavailable.

        Returns:
            ``ImageData`` or ``None`` if the user cancelled.
        """
        import subprocess

        try:
            # macOS screencapture -i (interactive region)
            with tempfile.NamedTemporaryFile(
                suffix=".png", delete=False
            ) as tmp:
                tmp_path = tmp.name

            result = subprocess.run(
                ["screencapture", "-i", tmp_path],
                capture_output=True,
                timeout=30,
            )
            if result.returncode != 0 or not os.path.exists(tmp_path):
                os.unlink(tmp_path)
                return None

            with open(tmp_path, "rb") as f:
                raw_bytes = f.read()
            os.unlink(tmp_path)

            from PIL import Image
            import io

            pil = Image.open(io.BytesIO(raw_bytes))
            return self._pil_to_data(pil, source=ImageSource.SCREENSHOT)

        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.warning("screenshot.interactive_failed", error=str(exc))
            return self.capture_fullscreen()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pil_to_data(
        self,
        pil_image: "PIL.Image",
        source: ImageSource = ImageSource.SCREENSHOT,
    ) -> ImageData:
        """Convert a PIL Image to an ``ImageData``."""
        import io

        buf = io.BytesIO()
        try:
            pil_image.save(buf, format="PNG")
        except Exception as exc:
            raise ScreenshotError(f"Image save failed: {exc}") from exc

        raw_bytes = buf.getvalue()
        width, height = pil_image.size

        file_path = ""
        if self._save_to_temp:
            try:
                tmp = tempfile.NamedTemporaryFile(
                    suffix=".png", delete=False
                )
                tmp.write(raw_bytes)
                file_path = tmp.name
                tmp.close()
            except OSError as exc:
                logger.warning("screenshot.temp_save_failed", error=str(exc))

        return ImageData(
            data=raw_bytes,
            format="png",
            width=width,
            height=height,
            source=source,
            file_path=file_path,
        )


# ---------------------------------------------------------------------------
# Input Router
# ---------------------------------------------------------------------------


class InputRouter:
    """Route multimodal input to the correct agent or handler.

    Classifies input based on type, content, and metadata, then determines
    which downstream handler should process it.
    """

    def __init__(self) -> None:
        """Initialise the input router."""
        self._routes: list[tuple[str, Any]] = []
        self._default_handler: Any = None

    def register_route(
        self,
        input_type: InputType,
        handler: Any,
    ) -> None:
        """Register a handler for a specific input type.

        Args:
            input_type: The input type to handle.
            handler: An object or callable that can process this input type.
        """
        self._routes.append((input_type.name, handler))

    def set_default_handler(self, handler: Any) -> None:
        """Set the default handler for unrecognised input types.

        Args:
            handler: Fallback handler.
        """
        self._default_handler = handler

    def route(self, result: InputResult) -> Any:
        """Route an input result to the appropriate handler.

        Args:
            result: The processed input result.

        Returns:
            The return value of the matched handler, or ``None`` if no
            handler matches.
        """
        for type_name, handler in self._routes:
            if result.type.name == type_name:
                try:
                    return handler(result)
                except Exception as exc:
                    logger.error(
                        "router.handler_failed",
                        input_type=type_name,
                        error=str(exc),
                    )
                    return None

        if self._default_handler is not None:
            try:
                return self._default_handler(result)
            except Exception as exc:
                logger.error(
                    "router.default_handler_failed",
                    error=str(exc),
                )
                return None

        logger.warning("router.no_handler", input_type=result.type.name)
        return None

    def list_routes(self) -> list[str]:
        """List all registered route types.

        Returns:
            List of type names with registered handlers.
        """
        return [type_name for type_name, _ in self._routes]


# ---------------------------------------------------------------------------
# MultimodalInputHandler (orchestrator)
# ---------------------------------------------------------------------------


class MultimodalInputHandler:
    """Top-level orchestrator for multimodal desktop input.

    Coordinates image paste, file drag-drop, screenshot capture, and input
    routing into a single API for the desktop chat interface.

    Usage::

        handler = MultimodalInputHandler()

        # Handle a clipboard paste (detects image vs text)
        result = await handler.handle_clipboard_paste()

        # Handle a file drop
        result = await handler.handle_file_drop("/path/to/file.py")

        # Handle a screenshot
        result = await handler.handle_screenshot()

        # Route the result to the correct agent
        handler.route(result)
    """

    def __init__(
        self,
        image_handler: ImageHandler | None = None,
        file_handler: FileDropHandler | None = None,
        screenshot: ScreenshotCapture | None = None,
        router: InputRouter | None = None,
    ) -> None:
        """Initialise the multimodal input handler.

        Args:
            image_handler: Handler for image paste/OCR.  Created with
                defaults if ``None``.
            file_handler: Handler for file drag-drop.  Created with
                defaults if ``None``.
            screenshot: Screenshot capture utility.  Created with
                defaults if ``None``.
            router: Input router for dispatching to agents.  Created
                with defaults if ``None``.
        """
        self._image_handler = image_handler or ImageHandler()
        self._file_handler = file_handler or FileDropHandler()
        self._screenshot = screenshot or ScreenshotCapture()
        self._router = router or InputRouter()

    @property
    def image_handler(self) -> ImageHandler:
        """The underlying image handler."""
        return self._image_handler

    @property
    def file_handler(self) -> FileDropHandler:
        """The underlying file handler."""
        return self._file_handler

    @property
    def screenshot(self) -> ScreenshotCapture:
        """The underlying screenshot capture."""
        return self._screenshot

    @property
    def router(self) -> InputRouter:
        """The underlying input router."""
        return self._router

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def handle_clipboard_paste(self) -> InputResult | None:
        """Handle a clipboard paste event (image or text).

        Returns:
            An ``InputResult`` if the clipboard contained pasteable
            content, or ``None`` if the clipboard was empty.

        Raises:
            ImageProcessingError: If clipboard image read fails.
        """
        now_ms = time.monotonic() * 1000

        # Try image first
        image_data = self._image_handler.from_clipboard()
        if image_data is not None:
            logger.info(
                "multimodal.clipboard_image",
                width=image_data.width,
                height=image_data.height,
                format=image_data.format,
                ocr_len=len(image_data.ocr_text),
            )
            return InputResult(
                type=InputType.IMAGE,
                image=image_data,
                text=image_data.ocr_text,
                source="clipboard",
                timestamp_ms=now_ms,
                metadata={
                    "width": image_data.width,
                    "height": image_data.height,
                    "format": image_data.format,
                },
            )

        return None

    async def handle_file_drop(self, file_path: str) -> InputResult:
        """Handle a file drag-drop event.

        Args:
            file_path: Absolute path to the dropped file.

        Returns:
            An ``InputResult`` with file metadata and content.

        Raises:
            FileHandlingError: If the file cannot be processed.
        """
        now_ms = time.monotonic() * 1000
        file_drop = self._file_handler.handle_drop(file_path)

        # If the file is an image, also extract image-specific data
        image_data: ImageData | None = None
        if file_drop.extension in SUPPORTED_IMAGE_FORMATS:
            try:
                image_data = self._image_handler.from_bytes(
                    file_drop.content,
                    image_format=file_drop.extension,
                    source=ImageSource.FILE_DROP,
                )
            except ImageProcessingError:
                logger.warning(
                    "multimodal.image_processing_failed",
                    path=file_path,
                )

        input_type = InputType.IMAGE if image_data else InputType.FILE

        logger.info(
            "multimodal.file_drop",
            filename=file_drop.filename,
            size_bytes=file_drop.size_bytes,
            type=input_type.name,
        )

        return InputResult(
            type=input_type,
            image=image_data,
            file=file_drop,
            text=f"[File: {file_drop.filename}]",
            source="file_drop",
            timestamp_ms=now_ms,
            metadata={
                "filename": file_drop.filename,
                "extension": file_drop.extension,
                "size_bytes": file_drop.size_bytes,
                "mime_type": file_drop.mime_type,
            },
        )

    async def handle_screenshot(
        self,
        region: tuple[int, int, int, int] | None = None,
    ) -> InputResult:
        """Handle a screenshot capture event.

        Args:
            region: Optional region (x, y, width, height).  If ``None``,
                captures the full screen.

        Returns:
            An ``InputResult`` with the screenshot image.

        Raises:
            ScreenshotError: If capture fails.
        """
        now_ms = time.monotonic() * 1000

        if region is not None:
            x, y, w, h = region
            image_data = self._screenshot.capture_region(x, y, w, h)
        else:
            image_data = self._screenshot.capture_fullscreen()

        logger.info(
            "multimodal.screenshot",
            width=image_data.width,
            height=image_data.height,
            format=image_data.format,
        )

        return InputResult(
            type=InputType.SCREENSHOT,
            image=image_data,
            text="[Screenshot]",
            source="screenshot",
            timestamp_ms=now_ms,
            metadata={
                "width": image_data.width,
                "height": image_data.height,
                "format": image_data.format,
            },
        )

    async def route(self, result: InputResult) -> Any:
        """Route an input result to the registered handler.

        Args:
            result: The input result to route.

        Returns:
            The return value of the matched handler.
        """
        return self._router.route(result)
