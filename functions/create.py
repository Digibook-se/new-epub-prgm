# from xml.dom import minidom
import os
import base64
import re
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
from Styles import base
from colorama import Fore  # type: ignore

def createEbook(newBook):
    # --- 0) Se till att Books-mappen finns ---
    os.makedirs('./Books', exist_ok=True)

    # --- 1) Initiera bok och hjälpar-objekt ---
    book = epub.EpubBook()
    bookToBuild = BookToBuild()

    # --- 2) Metadata ---
    book.set_identifier(newBook['title'])
    book.set_title(newBook['title'])
    book.set_language('se')
    book.add_author(newBook['author'])

    # --- 3) Lägg in användarens innehåll på rätt ställe! ---
    bookToBuild.Content = newBook['content']

    # --- 4) Omslagsbild utan default cover.xhtml ---
    coverImgPath = getCoverImg(newBook)
    data = open(f'./{coverImgPath}', 'rb').read()
    book.set_cover(coverImgPath, data, create_page=False)

    # --- 5) Skapa egen omslagssida ---
    coverPage = EpubHtml(title='Omslag', file_name='coverImg.xhtml', lang='en')
    coverPage.content = getCoverPageXml(coverImgPath)
    book.add_item(coverPage)

    # --- 6) CSS ---
    css = epub.EpubItem(
        uid="style_nav",
        file_name="style/styles.css",
        media_type="text/css",
        content=base.base
    )
    book.add_item(css)
    coverPage.add_item(css)

    # --- 7) Copyright ---
    copyrightPage = EpubHtml(
        title='Copyright',
        file_name='copyright.xhtml',
        lang='en'
    )
    copyrightPage.content = getCopyrightPage(
        book.title,
        newBook['author'],
        newBook.get('photographer', ''),
        newBook['ISBN']
    )
    copyrightPage.add_item(css)
    book.add_item(copyrightPage)

    # --- Steg 1: Läs in alla “raw” html-paragrafer, listor, bilder ---
    htmlParagraphs = []
    headingElementsForToc = []
    contentImages = []
    imgIterator = 1

    for section in bookToBuild.Content:
        runs = section.get('Paragraph', [])

        # Bild i texten?
        if section.get('Id', '').endswith('IMG') and runs:
            img_data = runs[0].get('base64DataUrl', '').split(',')[-1]
            binary = base64.b64decode(img_data)
            img_id = section['Id'].replace('-', '')[:-3]
            img_path = f'img/{img_id}.jpg'
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            with open(img_path, 'wb') as f:
                f.write(binary)
            img_item = epub.EpubItem(
                uid=f"img_{imgIterator}",
                file_name=img_path,
                media_type='image/jpeg',
                content=binary
            )
            book.add_item(img_item)
            htmlParagraphs.append(f"<img src='{img_path}' alt=''/>")
            contentImages.append(img_id)
            imgIterator += 1
            continue

        # Tom rad → <br/>
        if not runs:
            htmlParagraphs.append('<br/>')
            continue

        # Sida‐break
        if any(r.get('Type') == 'pagebreak' for r in runs):
            htmlParagraphs.append('¤PAGEBREAK¤')
            continue

        # Listor?
        firstType = runs[0].get('Type')
        if firstType == 'bulletListParagraph':
            htmlParagraphs.append('<ul>')
            for run in runs:
                text = run.get('Text', '')
                htmlParagraphs.append(f"<li>{text}</li>")
            htmlParagraphs.append('</ul>')
            continue
        if firstType == 'numberedListParagraph':
            htmlParagraphs.append('<ol>')
            for run in runs:
                text = run.get('Text', '')
                htmlParagraphs.append(f"<li>{text}</li>")
            htmlParagraphs.append('</ol>')
            continue

        # Heading eller vanlig paragraf
        first = runs[0]
        isHeading = first.get('Type') in ('Heading1', 'Rubrik1')
        if isHeading:
            full_heading = ''.join(r.get('Text', '') for r in runs).strip()
            headingElementsForToc.append(full_heading)

        html = getOpeningElementTag(first.get('Type'))
        # Gruppera runs med identiska attribut
        i = 0
        while i < len(runs):
            attrs = runs[i].get('Attributes', [])
            text_grp = runs[i].get('Text', '')
            j = i + 1
            while j < len(runs) and runs[j].get('Attributes', []) == attrs:
                text_grp += runs[j].get('Text', '')
                j += 1
            if attrs:
                span_style = ''.join(getStyle(a) for a in attrs)
                html += f"<span style='{span_style}'>{text_grp}</span>"
            else:
                html += text_grp
            i = j

        html += getClosingElementTag(first.get('Type'))
        htmlParagraphs.append(html)

    # --- Steg 2: Montera kapitel med indent‐logik ---
    chaptersToAdd = []
    chapter = None
    chapCount = 0
    pbIterator = 1
    firstPara = True

    for p in htmlParagraphs:
        # Radbrytning → ingen indentning på nästa
        if p == '<br/>':
            if chapter:
                chapter.content += p
            firstPara = True
            continue

        # Sida‐break
        if p == '¤PAGEBREAK¤':
            if chapter:
                chapter.content += create_pagebreak(pbIterator)
                pbIterator += 1
            continue

        # Nytt kapitel
        if p.startswith('<h1') or chapter is None:
            # Spara föregående kapitel om det inte är tomt
            if chapter:
                if chapter.content.strip():
                    chapter.add_item(css)
                    book.add_item(chapter)
                    chaptersToAdd.append(chapter)
                else:
                    print("DEBUG: Skippade tomt kapitel")

            chapCount += 1
            title = f'chapter{chapCount}'
            chapter = EpubHtml(title=title, file_name=f'{title}.xhtml')

            # Lägg in i TOC
            if chapCount - 1 < len(headingElementsForToc):
                nav_id = f'navPoint-h1-{chapCount}'
                chapter.structure = [
                    Link(f'{title}.xhtml',
                         headingElementsForToc[chapCount - 1],
                         nav_id)
                ]

            # Första paragrafen i kapitlet: undertryck indent om inte centrerad
            if p.startswith('<p'):
                if firstPara and 'text-align:center' not in p:
                    p = p.replace('<p', '<p style="text-indent:0;"', 1)

                # Slå ihop om enbart centrerad span
                m = re.match(
                    r"<p[^>]*>\s*<span style=['\"]text-align:center;?['\"]>(.*?)</span>\s*</p>",
                    p, flags=re.DOTALL)
                if m:
                    inner = m.group(1)
                    p = f"<p style=\"text-align:center;\">{inner}</p>"

            firstPara = False
            chapter.content = p

        else:
            # Fortsätt på samma kapitel
            if p.startswith('<p'):
                if firstPara and 'text-align:center' not in p:
                    p = p.replace('<p', '<p style="text-indent:0;"', 1)
                m = re.match(
                    r"<p[^>]*>\s*<span style=['\"]text-align:center;?['\"]>(.*?)</span>\s*</p>",
                    p, flags=re.DOTALL)
                if m:
                    inner = m.group(1)
                    p = f"<p style=\"text-align:center;\">{inner}</p>"
                firstPara = False
            chapter.content += p

    # Lägg till sista kapitlet
    if chapter:
        if chapter.content.strip():
            chapter.add_item(css)
            book.add_item(chapter)
            chaptersToAdd.append(chapter)
        else:
            print("DEBUG: Skippade tomt kapitel (sista)")

    # --- Steg 3: TOC, spine, NCX, skriv ut EPUB ---
    sections = []
    for chap in chaptersToAdd:
        sections.extend(getattr(chap, 'structure', []))

    book.toc = (
        epub.Link('copyright.xhtml', 'Copyright', 'copyright'),
        *sections
    )
    book.add_item(epub.EpubNcx())
    nav = book.add_item(epub.EpubNav())
    nav.add_item(css)

    spine = [coverPage, copyrightPage]
    if newBook.get('toc'):
        spine.append('nav')
    spine.extend(chaptersToAdd)
    book.spine = spine

    # WCAG-metadata
    cats = [c['value'] for c in newBook['categories']]
    setCorrectMetatags(
        book,
        newBook['ISBN'],
        newBook['author'],
        cats,
        newBook['description']
    )

    # Skriv ut
    out = f'./Books/first_{book.title}.epub'
    try:
        epub.write_epub(
            out, book,
            {"play_order": {"enabled": True, "start_from": 1}}
        )
    except Exception as e:
        raise RuntimeError(f"Misslyckades skriva EPUB (troligen tomt dokument): {e}")

    # Modifiera OPF & TOC
    saved = epub.read_epub(out)
    modifyOpf(saved)
    modifyToc(saved, newBook['ISBN'])

    print(Fore.GREEN + "Opf + toc korrigeringar klara." + Fore.RESET)

    # Rensa bilder
    for img in contentImages:
        removeFile(f'img/{img}.jpg')
