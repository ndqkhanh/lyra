"""
Content fetching and parsing for research sources.

Handles PDF extraction, README parsing, and web scraping.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import requests
import tempfile


@dataclass
class ParsedContent:
    """Parsed content from a research source."""
    title: str
    content: str
    metadata: dict


class PDFExtractor:
    """Extract text from PDF files."""

    def extract_from_url(self, pdf_url: str) -> Optional[ParsedContent]:
        """
        Extract text from PDF URL.

        Args:
            pdf_url: URL to PDF file

        Returns:
            Parsed content or None if extraction fails
        """
        try:
            # Download PDF
            response = requests.get(pdf_url, timeout=60)
            if response.status_code != 200:
                return None

            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            # Extract text
            content = self.extract_from_file(Path(tmp_path))

            # Cleanup
            Path(tmp_path).unlink()

            return content

        except Exception as e:
            print(f"PDF extraction error: {e}")
            return None

    def extract_from_file(self, pdf_path: Path) -> Optional[ParsedContent]:
        """
        Extract text from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Parsed content or None if extraction fails
        """
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(pdf_path)

            # Extract title from first page
            first_page = doc[0]
            title = first_page.get_text().split('\n')[0][:200]

            # Extract all text
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())

            content = "\n\n".join(text_parts)

            doc.close()

            return ParsedContent(
                title=title,
                content=content,
                metadata={"pages": len(doc), "format": "pdf"},
            )

        except Exception as e:
            print(f"PDF file extraction error: {e}")
            return None


class READMEParser:
    """Parse README files from repositories."""

    def fetch_readme(self, repo_url: str, github_token: Optional[str] = None) -> Optional[ParsedContent]:
        """
        Fetch and parse README from GitHub repository.

        Args:
            repo_url: GitHub repository URL
            github_token: Optional GitHub API token

        Returns:
            Parsed README content
        """
        try:
            # Extract owner and repo from URL
            parts = repo_url.rstrip('/').split('/')
            owner, repo = parts[-2], parts[-1]

            # Fetch README via API
            api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
            headers = {"Accept": "application/vnd.github.v3.raw"}
            if github_token:
                headers["Authorization"] = f"token {github_token}"

            response = requests.get(api_url, headers=headers, timeout=30)

            if response.status_code != 200:
                return None

            content = response.text

            return ParsedContent(
                title=f"{owner}/{repo} README",
                content=content,
                metadata={"repo": f"{owner}/{repo}", "format": "markdown"},
            )

        except Exception as e:
            print(f"README fetch error: {e}")
            return None


class WebScraper:
    """Scrape content from web pages."""

    def scrape(self, url: str) -> Optional[ParsedContent]:
        """
        Scrape content from web page.

        Args:
            url: Web page URL

        Returns:
            Parsed content
        """
        try:
            from bs4 import BeautifulSoup

            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title = soup.find('title')
            title_text = title.get_text() if title else url

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return ParsedContent(
                title=title_text,
                content=text,
                metadata={"url": url, "format": "html"},
            )

        except Exception as e:
            print(f"Web scraping error: {e}")
            return None


class ContentFetcher:
    """
    Unified content fetcher for all source types.

    Handles PDFs, READMEs, and web pages.
    """

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize content fetcher.

        Args:
            github_token: Optional GitHub API token
        """
        self.pdf_extractor = PDFExtractor()
        self.readme_parser = READMEParser()
        self.web_scraper = WebScraper()
        self.github_token = github_token

    def fetch(self, url: str, content_type: str = "auto") -> Optional[ParsedContent]:
        """
        Fetch and parse content from URL.

        Args:
            url: Content URL
            content_type: Type of content (auto, pdf, readme, web)

        Returns:
            Parsed content
        """
        # Auto-detect content type
        if content_type == "auto":
            if url.endswith('.pdf') or 'arxiv.org/pdf' in url:
                content_type = "pdf"
            elif 'github.com' in url and not url.endswith('.pdf'):
                content_type = "readme"
            else:
                content_type = "web"

        # Fetch based on type
        if content_type == "pdf":
            return self.pdf_extractor.extract_from_url(url)
        elif content_type == "readme":
            return self.readme_parser.fetch_readme(url, self.github_token)
        elif content_type == "web":
            return self.web_scraper.scrape(url)
        else:
            return None
