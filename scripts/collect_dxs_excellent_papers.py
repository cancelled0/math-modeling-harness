#!/usr/bin/env python3
"""Collect 2023-2025 CUMCM excellent papers from dxs.moe.gov.cn.

The recent exhibition pages publish papers as one image per page.  This script
discovers the official article URLs, downloads the original page images, merges
them into lossless-image PDFs, validates page counts, and writes an auditable
manifest.  If an article exposes an original PDF link, that PDF is preferred.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlsplit

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader
from reportlab.pdfgen import canvas


BASE_URL = "https://dxs.moe.gov.cn"
YEAR_INDEXES = {
    2023: "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2023qgdxssxjmjslwzs/2023gjsbqgdxssxjmjslwzs.shtml",
    2024: "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2024qgdxssxjmjslwzs/",
    2025: "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2025qgdxssxjmjslwzs/",
}
EXPECTED_COUNTS = {2023: 12, 2024: 16, 2025: 7}
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140 Safari/537.36"
)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.title_parts: list[str] = []
        self._in_title = False
        self._current_href: str | None = None
        self._current_link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k.lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        elif tag == "a" and values.get("href"):
            self._current_href = values["href"]
            self._current_link_text = []
        elif tag == "img":
            self.images.append(values)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        elif tag == "a" and self._current_href is not None:
            text = " ".join("".join(self._current_link_text).split())
            self.links.append((self._current_href, text))
            self._current_href = None
            self._current_link_text = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)
        if self._current_href is not None:
            self._current_link_text.append(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())


@dataclass
class Paper:
    year: int
    code: str
    title: str
    article_url: str
    image_urls: list[str]
    direct_pdf_urls: list[str]


@dataclass
class Result:
    year: int
    code: str
    title: str
    article_url: str
    output_pdf: str
    page_count: int
    size_bytes: int
    sha256: str
    source_kind: str
    status: str
    issue: str = ""


def run_curl(url: str, output: Path | None = None, max_time: int = 300) -> bytes:
    command = [
        "curl.exe",
        "--http1.1",
        "--tlsv1.2",
        "-sS",
        "-L",
        "--retry",
        "10",
        "--retry-all-errors",
        "--retry-delay",
        "1",
        "--connect-timeout",
        "30",
        "--max-time",
        str(max_time),
        "-A",
        USER_AGENT,
    ]
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        part = output.with_suffix(output.suffix + ".part")
        command.extend(["--output", str(part), url])
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if completed.returncode != 0:
            part.unlink(missing_ok=True)
            raise RuntimeError(completed.stderr.decode("utf-8", "replace").strip())
        part.replace(output)
        return b""
    command.append(url)
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", "replace").strip())
    return completed.stdout


def parse_html(raw: bytes) -> PageParser:
    parser = PageParser()
    parser.feed(raw.decode("utf-8", "replace"))
    return parser


def discover_article_urls(year: int, index_url: str) -> list[str]:
    parser = parse_html(run_curl(index_url))
    pattern = re.compile(
        rf"^/zx/a/hd_sxjm_sxjmlw_{year}qgdxssxjmjslwzs_[^/]+/\d+/\d+\.shtml(?:\?.*)?$",
        re.I,
    )
    seen: set[str] = set()
    urls: list[str] = []
    for href, _text in parser.links:
        absolute = urljoin(BASE_URL, href)
        path_with_query = urlsplit(absolute).path
        if urlsplit(absolute).query:
            path_with_query += "?" + urlsplit(absolute).query
        if pattern.match(path_with_query) and absolute not in seen:
            seen.add(absolute)
            urls.append(absolute)
    return urls


def page_number(attrs: dict[str, str], fallback: int) -> int:
    text = " ".join([attrs.get("alt", ""), attrs.get("title", ""), attrs.get("src", "")])
    matches = re.findall(r"(?:页面|頁面|page|[_-])(\d{1,4})(?=\D*$)", text, re.I)
    return int(matches[-1]) if matches else fallback


def discover_paper(year: int, article_url: str) -> Paper:
    parser = parse_html(run_curl(article_url))
    title = parser.title.split(" - ", 1)[0].strip()
    code_match = re.search(r"[（(]([A-E]\d{2,4})[）)]", title, re.I)
    if not code_match:
        # The article directory often carries a reliable problem-family marker;
        # use visible link/image text only as a fallback for the entry number.
        searchable = " ".join(
            [title]
            + [text for _href, text in parser.links]
            + [image.get("alt", "") for image in parser.images]
        )
        code_match = re.search(r"\b([A-E]\d{2,4})\b", searchable, re.I)
    if not code_match:
        raise RuntimeError(f"无法从文章标题识别论文编号：{title or article_url}")
    code = code_match.group(1).upper()

    candidates: list[tuple[int, str, dict[str, str]]] = []
    for position, attrs in enumerate(parser.images, start=1):
        src = attrs.get("src") or attrs.get("data-src") or attrs.get("data-original")
        if not src:
            continue
        absolute = urljoin(article_url, src)
        parts = urlsplit(absolute)
        if "file.myqcloud.com" not in parts.netloc or "/upload/resources/image/" not in parts.path:
            continue
        alt = attrs.get("alt", "")
        is_page_image = code.lower() in alt.lower() or "页面" in alt or "頁面" in alt
        if is_page_image:
            candidates.append((page_number(attrs, position), absolute, attrs))

    # Pages are frequently duplicated later in the HTML for a gallery.  Retain
    # the first occurrence of each original URL and restore numeric page order.
    unique: dict[str, tuple[int, int]] = {}
    for position, (number, url, _attrs) in enumerate(candidates):
        clean = url.split("?", 1)[0]
        unique.setdefault(clean, (number, position))
    image_urls = [
        url for url, _meta in sorted(unique.items(), key=lambda item: (item[1][0], item[1][1]))
    ]

    direct_pdf_urls: list[str] = []
    seen_pdf: set[str] = set()
    for href, _text in parser.links:
        absolute = urljoin(article_url, href)
        if urlsplit(absolute).path.lower().endswith(".pdf") and absolute not in seen_pdf:
            seen_pdf.add(absolute)
            direct_pdf_urls.append(absolute)

    if not image_urls and not direct_pdf_urls:
        raise RuntimeError(f"文章未发现逐页图片或 PDF 下载链接：{article_url}")
    return Paper(year, code, title, article_url, image_urls, direct_pdf_urls)


def discover_all() -> tuple[list[Paper], list[dict[str, str]]]:
    papers: list[Paper] = []
    failures: list[dict[str, str]] = []
    for year, index_url in YEAR_INDEXES.items():
        try:
            article_urls = discover_article_urls(year, index_url)
        except Exception as exc:  # noqa: BLE001 - preserve every network failure
            failures.append({"year": str(year), "stage": "index", "url": index_url, "issue": str(exc)})
            continue
        print(f"[{year}] 官方索引发现 {len(article_urls)} 篇", flush=True)
        if len(article_urls) != EXPECTED_COUNTS[year]:
            failures.append(
                {
                    "year": str(year),
                    "stage": "index_count",
                    "url": index_url,
                    "issue": f"预期 {EXPECTED_COUNTS[year]} 篇，实际发现 {len(article_urls)} 篇",
                }
            )
        for number, article_url in enumerate(article_urls, start=1):
            try:
                paper = discover_paper(year, article_url)
                papers.append(paper)
                print(
                    f"  {number:02d}/{len(article_urls):02d} {paper.code}: "
                    f"{len(paper.image_urls)} 张原页图, {len(paper.direct_pdf_urls)} 个 PDF 链接",
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001
                failures.append(
                    {"year": str(year), "stage": "article", "url": article_url, "issue": str(exc)}
                )
                print(f"  {number:02d}/{len(article_urls):02d} 失败: {exc}", flush=True)
    papers.sort(key=lambda p: (p.year, p.code[0], int(p.code[1:])))
    return papers, failures


def verify_image(path: Path) -> None:
    if not path.exists() or path.stat().st_size < 1024:
        raise RuntimeError("下载内容为空或过小")
    with Image.open(path) as image:
        image.verify()


def download_image(url: str, destination: Path) -> tuple[Path, str | None]:
    try:
        if destination.exists():
            verify_image(destination)
            return destination, None
        run_curl(url, destination, max_time=300)
        verify_image(destination)
        return destination, None
    except Exception as exc:  # noqa: BLE001
        destination.unlink(missing_ok=True)
        return destination, str(exc)


def create_pdf_from_images(images: list[Path], output_pdf: Path, title: str, source_url: str) -> None:
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    part = output_pdf.with_suffix(".pdf.part")
    pdf = canvas.Canvas(str(part), pageCompression=1)
    pdf.setTitle(title)
    pdf.setAuthor("全国大学生数学建模竞赛组委会")
    pdf.setSubject("全国大学生数学建模竞赛优秀论文展示；由官网逐页图片合成为 PDF")
    pdf.setKeywords(f"数学建模, 优秀论文, {source_url}")
    for image_path in images:
        with Image.open(image_path) as image:
            width_px, height_px = image.size
        if width_px <= 0 or height_px <= 0:
            raise RuntimeError(f"无效图片尺寸：{image_path}")
        long_side = 842.0
        if height_px >= width_px:
            page_height = long_side
            page_width = long_side * width_px / height_px
        else:
            page_width = long_side
            page_height = long_side * height_px / width_px
        pdf.setPageSize((page_width, page_height))
        pdf.drawImage(
            str(image_path),
            0,
            0,
            width=page_width,
            height=page_height,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
        pdf.showPage()
    pdf.save()
    part.replace(output_pdf)


def verify_pdf(path: Path, expected_pages: int | None = None) -> int:
    if not path.exists() or path.stat().st_size < 4096:
        raise RuntimeError("PDF 不存在或文件过小")
    reader = PdfReader(str(path))
    count = len(reader.pages)
    if count < 1:
        raise RuntimeError("PDF 没有页面")
    if expected_pages is not None and count != expected_pages:
        raise RuntimeError(f"PDF 页数 {count} 与原页图数量 {expected_pages} 不一致")
    for index in {0, count - 1}:
        page = reader.pages[index]
        resources = page.get("/Resources")
        if resources is None or resources.get("/XObject") is None:
            raise RuntimeError(f"第 {index + 1} 页未发现图像对象")
    return count


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def process_paper(paper: Paper, output_root: Path, temp_root: Path, workers: int) -> Result:
    output_pdf = output_root / str(paper.year) / f"{paper.year}_{paper.code}_优秀论文.pdf"
    if output_pdf.exists():
        try:
            pages = verify_pdf(output_pdf, len(paper.image_urls) if paper.image_urls else None)
            return Result(
                paper.year,
                paper.code,
                paper.title,
                paper.article_url,
                str(output_pdf.resolve()),
                pages,
                output_pdf.stat().st_size,
                sha256_file(output_pdf),
                "existing",
                "ok",
            )
        except Exception:
            output_pdf.unlink(missing_ok=True)

    if paper.direct_pdf_urls:
        issues: list[str] = []
        for pdf_url in paper.direct_pdf_urls:
            try:
                run_curl(pdf_url, output_pdf, max_time=600)
                pages = verify_pdf(output_pdf)
                return Result(
                    paper.year,
                    paper.code,
                    paper.title,
                    paper.article_url,
                    str(output_pdf.resolve()),
                    pages,
                    output_pdf.stat().st_size,
                    sha256_file(output_pdf),
                    "official_pdf",
                    "ok",
                )
            except Exception as exc:  # noqa: BLE001
                output_pdf.unlink(missing_ok=True)
                issues.append(f"{pdf_url}: {exc}")
        if not paper.image_urls:
            raise RuntimeError("；".join(issues))

    paper_temp = temp_root / str(paper.year) / paper.code
    paper_temp.mkdir(parents=True, exist_ok=True)
    destinations = [paper_temp / f"page_{index:04d}.jpg" for index in range(1, len(paper.image_urls) + 1)]
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(download_image, url, destination): (index, url)
            for index, (url, destination) in enumerate(zip(paper.image_urls, destinations), start=1)
        }
        completed_count = 0
        for future in as_completed(futures):
            index, url = futures[future]
            _destination, issue = future.result()
            completed_count += 1
            if issue:
                failed.append(f"第 {index} 页 {url}: {issue}")
            if completed_count % 20 == 0 or completed_count == len(futures):
                print(f"    {paper.code} 下载 {completed_count}/{len(futures)}", flush=True)
    if failed:
        raise RuntimeError("；".join(failed))

    create_pdf_from_images(destinations, output_pdf, paper.title, paper.article_url)
    pages = verify_pdf(output_pdf, len(destinations))
    shutil.rmtree(paper_temp)
    return Result(
        paper.year,
        paper.code,
        paper.title,
        paper.article_url,
        str(output_pdf.resolve()),
        pages,
        output_pdf.stat().st_size,
        sha256_file(output_pdf),
        "page_images",
        "ok",
    )


def render_pdf_samples(results: Iterable[Result], qa_root: Path) -> list[Path]:
    qa_root.mkdir(parents=True, exist_ok=True)
    rendered: list[Path] = []
    for result in results:
        if result.status != "ok":
            continue
        pdf_path = Path(result.output_pdf)
        for label, page in [("first", 1), ("last", result.page_count)]:
            prefix = qa_root / f"{result.year}_{result.code}_{label}"
            command = [
                "pdftoppm",
                "-png",
                "-r",
                "72",
                "-f",
                str(page),
                "-l",
                str(page),
                "-singlefile",
                str(pdf_path),
                str(prefix),
            ]
            completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if completed.returncode != 0:
                raise RuntimeError(
                    f"渲染失败 {pdf_path.name} 第 {page} 页："
                    + completed.stderr.decode("utf-8", "replace")
                )
            png = prefix.with_suffix(".png")
            with Image.open(png) as image:
                image.verify()
            rendered.append(png)
    return rendered


def build_contact_sheets(rendered: list[Path], qa_root: Path) -> list[Path]:
    sheets: list[Path] = []
    cell_width, cell_height = 230, 330
    columns, rows = 5, 4
    per_sheet = columns * rows
    font = ImageFont.load_default()
    for sheet_index in range(0, len(rendered), per_sheet):
        batch = rendered[sheet_index : sheet_index + per_sheet]
        sheet = Image.new("RGB", (cell_width * columns, cell_height * rows), "white")
        draw = ImageDraw.Draw(sheet)
        for position, path in enumerate(batch):
            with Image.open(path) as source:
                preview = source.convert("RGB")
                preview.thumbnail((cell_width - 10, cell_height - 32))
            col, row = position % columns, position // columns
            x = col * cell_width + (cell_width - preview.width) // 2
            y = row * cell_height + 4
            sheet.paste(preview, (x, y))
            label = path.stem
            draw.text((col * cell_width + 5, row * cell_height + cell_height - 22), label, fill="black", font=font)
        output = qa_root / f"contact_sheet_{sheet_index // per_sheet + 1:02d}.png"
        sheet.save(output)
        sheets.append(output)
    return sheets


def write_reports(output_root: Path, papers: list[Paper], results: list[Result], failures: list[dict[str, str]]) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source_index": "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/qkt_sxjm_lw_lwzs.shtml",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "expected_counts": EXPECTED_COUNTS,
        "discovered_counts": {year: sum(1 for paper in papers if paper.year == year) for year in YEAR_INDEXES},
        "results": [asdict(result) for result in results],
        "failures": failures,
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with (output_root / "论文清单.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["年份", "论文编号", "题目", "页数", "PDF文件", "官网文章", "来源形式", "状态", "问题", "SHA-256"]
        )
        for result in sorted(results, key=lambda r: (r.year, r.code[0], int(r.code[1:]))):
            writer.writerow(
                [
                    result.year,
                    result.code,
                    result.title,
                    result.page_count,
                    result.output_pdf,
                    result.article_url,
                    result.source_kind,
                    result.status,
                    result.issue,
                    result.sha256,
                ]
            )

    lines = [
        "# 2023-2025 全国大学生数学建模竞赛优秀论文整理",
        "",
        "来源：中国大学生在线“全国大学生数学建模竞赛论文展示”。",
        "近年官网主要以逐页图片展示论文；本目录中的 PDF 按官网原页顺序无损合成。",
        "官网页面声明未经竞赛组委会书面许可请勿转载，请将本地文件用于个人学习并遵守原站说明。",
        "",
    ]
    by_key = {(result.year, result.code): result for result in results}
    for year in YEAR_INDEXES:
        lines.extend([f"## {year} 年", ""])
        for paper in [p for p in papers if p.year == year]:
            result = by_key.get((paper.year, paper.code))
            if result and result.status == "ok":
                relative = Path(result.output_pdf).relative_to(output_root.resolve()).as_posix()
                lines.append(f"- {paper.code}：[{paper.title}]({relative})（{result.page_count} 页）")
            else:
                issue = result.issue if result else "未生成"
                lines.append(f"- {paper.code}：失败 - {issue}")
        lines.append("")
    lines.extend(["## 异常记录", ""])
    if failures:
        for failure in failures:
            lines.append(
                f"- {failure.get('year', '')} / {failure.get('stage', '')} / "
                f"{failure.get('url', '')}：{failure.get('issue', '')}"
            )
    else:
        lines.append("- 无。")
    (output_root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover-only", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output-root", type=Path, default=Path("output/pdf/优秀论文展示_2023-2025"))
    parser.add_argument("--temp-root", type=Path, default=Path("tmp/pdfs/dxs_excellent_papers"))
    args = parser.parse_args()

    output_root = args.output_root.resolve()
    temp_root = args.temp_root.resolve()
    papers, failures = discover_all()
    discovery_path = output_root / "discovery.json"
    discovery_path.parent.mkdir(parents=True, exist_ok=True)
    discovery_path.write_text(
        json.dumps({"papers": [asdict(paper) for paper in papers], "failures": failures}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if args.discover_only:
        print(f"发现 {len(papers)} 篇；详情已写入 {discovery_path}")
        return 0 if len(papers) == sum(EXPECTED_COUNTS.values()) and not failures else 2

    results: list[Result] = []
    for number, paper in enumerate(papers, start=1):
        print(f"[{number:02d}/{len(papers):02d}] 处理 {paper.year} {paper.code}", flush=True)
        try:
            result = process_paper(paper, output_root, temp_root, args.workers)
            results.append(result)
            print(
                f"    完成：{result.page_count} 页，{result.size_bytes / 1024 / 1024:.1f} MiB",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            issue = str(exc)
            results.append(
                Result(paper.year, paper.code, paper.title, paper.article_url, "", 0, 0, "", "", "failed", issue)
            )
            failures.append(
                {"year": str(paper.year), "stage": "download_or_convert", "url": paper.article_url, "issue": issue}
            )
            print(f"    失败：{issue}", flush=True)

    successful = [result for result in results if result.status == "ok"]
    if successful:
        rendered = render_pdf_samples(successful, temp_root / "qa_rendered")
        sheets = build_contact_sheets(rendered, temp_root / "qa_rendered")
        print("QA_CONTACT_SHEETS=" + json.dumps([str(path.resolve()) for path in sheets], ensure_ascii=False))
    write_reports(output_root, papers, results, failures)
    print(f"成功 {len(successful)}/{len(papers)} 篇；输出目录：{output_root}")
    return 0 if len(successful) == sum(EXPECTED_COUNTS.values()) and not failures else 2


if __name__ == "__main__":
    sys.exit(main())
