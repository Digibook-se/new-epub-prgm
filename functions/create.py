# create.py
import os
import re
import base64

from ebooklib import epub
from ebooklib.epub import EpubHtml, EpubNav, EpubNcx, Link
from ebooklib.utils import create_pagebreak

from functions.createHelpers import (
    getCoverImg,
    getOpeningElementTag,
    getClosingElementTag,
    getStyle,
    removeFile
)
from functions.opfAndTocModifyer import setCorrectMetatags, modifyOpf, modifyToc
from structuralComponents.structure import getCoverPageXml
from miniComponents.copyright import getCopyrightPage
from classes.BookToBuild import BookToBuild

from colorama import Fore  # type: ignore


def createEbook(newBook: dict):
    """
    Build and write an EPUB3 file from newBook metadata and content.
    newBook must contain: title, author, ISBN, categories (list of dicts with 'value'), description,
    content (list of sections with 'Paragraph'), optional css (bytes), photographer.
    """
    # Ensure output directory
    os.makedirs('Books', exist_ok=True)

    # Initialize book and helper
    book = epub.EpubBook()
    builder = BookToBuild()
    builder.Content = newBook.get('content', [])

    # Metadata
    book.set_identifier(newBook['title'])
    book.set_title(newBook['title'])
    book.set_language('se')
    book.add_author(newBook['author'])

    # Cover image
    cover_path = getCoverImg(newBook)
    with open(cover_path, 'rb') as f:
        cover_data = f.read()
    book.set_cover(os.path.basename(cover_path), cover_data, create_page=False)

    # Custom cover page
    coverPage = EpubHtml(title='Omslag', file_name='cover.xhtml', lang='se')
    coverPage.content = getCoverPageXml(cover_path)
    book.add_item(coverPage)

    # CSS
    css_bytes = newBook.get('css', b'')
    css = epub.EpubItem(
        uid='style_nav',
        file_name='styles.css',
        media_type='text/css',
        content=css_bytes
    )
    book.add_item(css)
    coverPage.add_item(css)

    # Copyright page
    copyrightPage = EpubHtml(
        title='Copyright',
        file_name='copyright.xhtml',
        lang='se'
    )
    copyrightPage.content = getCopyrightPage(
        newBook['title'],
        newBook['author'],
        newBook.get('photographer', ''),
        newBook['ISBN']
    )
    copyrightPage.add_item(css)
    book.add_item(copyrightPage)

    # Collect raw HTML fragments
    htmlParagraphs = []
    headings = []

    for section in builder.Content:
        runs = section.get('Paragraph', [])
        # Empty -> line break
        if not runs:
            htmlParagraphs.append('<br/>')
            continue
        # Page-break marker
        if any(r.get('Type') == 'pagebreak' for r in runs):
            htmlParagraphs.append('¤PAGEBREAK¤')
            continue
        # Determine tag
        first = runs[0]
        if first.get('Type') in ('Heading1', 'Rubrik1'):
            full_text = ''.join(r.get('Text', '') for r in runs).strip()
            headings.append(full_text)
            tag_open, tag_close = '<h1>', '</h1>'
        else:
            tag_open, tag_close = '<p>', '</p>'

        html = tag_open
        i = 0
        while i < len(runs):
            attrs = runs[i].get('Attributes', [])
            text = runs[i].get('Text', '')
            j = i + 1
            while j < len(runs) and runs[j].get('Attributes', []) == attrs:
                text += runs[j].get('Text', '')
                j += 1
            if attrs:
                style = ''.join(getStyle(a) for a in attrs)
                html += f"<span style='{style}'>{text}</span>"
            else:
                html += text
            i = j
        html += tag_close
        htmlParagraphs.append(html)

    # Assemble chapters with indent logic
    chapters = []
    chapter = None
    chap_idx = 0
    pb_count = 1
    first_para = True

    for frag in htmlParagraphs:
        if frag == '<br/>' and chapter:
            chapter.content += frag
            first_para = True
            continue
        if frag == '¤PAGEBREAK¤' and chapter:
            chapter.content += create_pagebreak(pb_count)
            pb_count += 1
            continue

        # Start new chapter
        if frag.startswith('<h1') or chapter is None:
            if chapter:
                chapter.add_item(css)
                book.add_item(chapter)
                chapters.append(chapter)
            chap_idx += 1
            chapter = EpubHtml(
                title=f'chapter{chap_idx}',
                file_name=f'chapter{chap_idx}.xhtml',
                lang='se'
            )
            chapter.structure = []
            if chap_idx <= len(headings):
                chapter.structure.append(
                    Link(chapter.file_name, headings[chap_idx-1], f'navPoint-h1-{chap_idx}')
                )
            chapter.content = ''
            first_para = True

        # Indent first paragraph unless centered
        if frag.startswith('<p') and first_para and 'text-align:center' not in frag:
            frag = frag.replace('<p', '<p style="text-indent:0;"', 1)
        # Collapse single centered span
        m = re.match(r"<p[^>]*>\s*<span style=['\"]text-align:center;?['\"]>(.*?)</span>\s*</p>", frag, re.DOTALL)
        if m:
            inner = m.group(1)
            frag = f'<p style="text-align:center;">{inner}</p>'

        chapter.content += frag
        first_para = False

    # Finalize last chapter
    if chapter and getattr(chapter, 'content', '').strip():
        chapter.add_item(css)
        book.add_item(chapter)
        chapters.append(chapter)

    # Table of Contents & Navigation
    toc_items = [Link('copyright.xhtml', 'Copyright', 'copyright')]
    for ch in chapters:
        toc_items.extend(ch.structure)
    book.toc = tuple(toc_items)
    book.add_item(epub.EpubNcx())
    nav = book.add_item(epub.EpubNav()); nav.add_item(css)

    # Spine
    spine = [coverPage, copyrightPage]
    spine.extend(chapters)
    book.spine = spine

    # WCAG metadata
    setCorrectMetatags(
        book,
        newBook['ISBN'],
        newBook['author'],
        [c['value'] for c in newBook.get('categories', [])],
        newBook.get('description', '')
    )

    # Write EPUB to file
    out = os.path.join('Books', f"{book.title}.epub")
    try:
        epub.write_epub(
            out,
            book,
            {"play_order": {"enabled": True, "start_from": 1}}
        )
    except Exception as e:
        raise RuntimeError(f"Misslyckades skriva EPUB (troligen tomt dokument): {e}")

    # Post-process OPF & TOC
    saved = epub.read_epub(out)
    modifyOpf(saved)
    modifyToc(saved, newBook['ISBN'])

    print(Fore.GREEN + f'Wrote EPUB: {out}' + Fore.RESET)

    # Cleanup images
    for img in getattr(builder, 'images', []):
        removeFile(f'img/{img}.jpg')
