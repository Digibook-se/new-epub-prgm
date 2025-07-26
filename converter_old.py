# converter.py
import os
import base64
import re
from ebooklib import epub
from ebooklib.epub import EpubHtml, EpubNav, EpubNcx, Link
from docx import Document
import PyPDF2
from ebooklib.utils import create_pagebreak

from functions.createHelpers import (
    getCoverImg, getOpeningElementTag, getClosingElementTag, getStyle, removeFile
)
from functions.opfAndTocModifyer import setCorrectMetatags, modifyOpf, modifyToc
from structuralComponents.structure import getCoverPageXml
from miniComponents.copyright import getCopyrightPage
from classes.BookToBuild import BookToBuild
from Styles import base
from colorama import Fore

def parse_word(path: str):
    doc = Document(path)
    content = []
    uid = 1
    for para in doc.paragraphs:
        runs = []
        for run in para.runs:
            attrs = []
            if run.bold: attrs.append('bold')
            if run.italic: attrs.append('italic')
            if run.underline: attrs.append('underline')
            runs.append({'Text': run.text, 'Type': '', 'Attributes': attrs})
        content.append({'Id': f'PAR_{uid}', 'Paragraph': runs})
        uid += 1
    return content

def parse_pdf(path: str):
    reader = PyPDF2.PdfReader(path)
    content = []
    uid = 1
    for page in reader.pages:
        text = page.extract_text() or ''
        for line in text.splitlines():
            content.append({'Id': f'PAR_{uid}',
                            'Paragraph': [{'Text': line, 'Type': '', 'Attributes': []}]})
            uid += 1
    return content

def convert_file(newBook: dict, include_toc: bool):
    """Huvudfunktion som kör en end-to-end EPUB-byggnad."""
    # Läs in Word/PDF
    path = newBook['path']
    ext = os.path.splitext(path)[1].lower()
    if ext == '.docx':
        newBook['content'] = parse_word(path)
    elif ext == '.pdf':
        newBook['content'] = parse_pdf(path)
    else:
        raise ValueError("Felaktig filtyp, välj .docx eller .pdf")

    newBook['toc'] = include_toc
    # --- Skapa EPUB ---
    book = epub.EpubBook()
    book.set_identifier(newBook['title'])
    book.set_title(newBook['title'])
    book.set_language('se')
    book.add_author(newBook['author'])

    # Omslag
    cover = getCoverImg(newBook)
    data = open(cover, 'rb').read()
    book.set_cover(cover, data, create_page=False)
    coverPage = EpubHtml(title='Omslag', file_name='coverImg.xhtml', lang='en')
    coverPage.content = getCoverPageXml(cover)
    book.add_item(coverPage)

    # CSS
    css = epub.EpubItem(uid="style_nav",
                        file_name="style/styles.css",
                        media_type="text/css",
                        content=base.base)
    book.add_item(css)
    coverPage.add_item(css)

    # Copyright
    cp = EpubHtml(title='Copyright',
                  file_name='copyright.xhtml',
                  lang='en')
    cp.content = getCopyrightPage(
        newBook['title'], newBook['author'],
        newBook.get('photographer',''),
        newBook['ISBN'])
    cp.add_item(css)
    book.add_item(cp)

    # Skapa HTML-”rader”
    htmlParagraphs = []
    toc_headings = []
    images = []
    img_id = 1

    for section in newBook['content']:
        runs = section.get('Paragraph', [])
        # Bild från Word
        if section['Id'].endswith('IMG') and runs:
            b64 = runs[0].get('base64DataUrl','').split(',')[-1]
            bin_data = base64.b64decode(b64)
            iid = section['Id'].replace('-','')[:-3]
            ipath = f'img/{iid}.jpg'
            os.makedirs('img', exist_ok=True)
            with open(ipath,'wb') as f: f.write(bin_data)
            item = epub.EpubItem(uid=f"img_{img_id}",
                                 file_name=ipath,
                                 media_type='image/jpeg',
                                 content=bin_data)
            book.add_item(item)
            htmlParagraphs.append(f"<img src='{ipath}' alt='' />")
            images.append(iid)
            img_id += 1
            continue
        # Tomt stycke → radbrytning
        if not runs:
            htmlParagraphs.append('<br/>')
            continue
        # Sidoavbrott
        if any(r['Type']=='pagebreak' for r in runs):
            htmlParagraphs.append('¤PAGEBREAK¤')
            continue
        # Listor
        t0 = runs[0]['Type']
        if t0 == 'bulletListParagraph':
            htmlParagraphs.append('<ul>')
            for r in runs:
                htmlParagraphs.append(f"<li>{r['Text']}</li>")
            htmlParagraphs.append('</ul>')
            continue
        if t0 == 'numberedListParagraph':
            htmlParagraphs.append('<ol>')
            for r in runs:
                htmlParagraphs.append(f"<li>{r['Text']}</li>")
            htmlParagraphs.append('</ol>')
            continue

        # Rubrik eller paragraf
        first = runs[0]
        if first['Type'] in ('Heading1','Rubrik1'):
            toc_headings.append(''.join(r['Text'] for r in runs).strip())
        html = getOpeningElementTag(first['Type'])
        i = 0
        while i < len(runs):
            attrs = runs[i]['Attributes']
            text = runs[i]['Text']
            j = i+1
            while j < len(runs) and runs[j]['Attributes']==attrs:
                text += runs[j]['Text']
                j += 1
            if attrs:
                style = ''.join(getStyle(a) for a in attrs)
                html += f"<span style='{style}'>{text}</span>"
            else:
                html += text
            i = j
        html += getClosingElementTag(first['Type'])
        htmlParagraphs.append(html)

    # Montera kapitel
    chapters = []
    chap = None
    count = 0
    pb = 1
    firstPara = True

    for line in htmlParagraphs:
        if line == '<br/>':
            firstPara = True
            if chap:
                chap.content += line
            continue
        if line == '¤PAGEBREAK¤':
            if chap:
                chap.content += create_pagebreak(pb)
                pb += 1
            continue
        if line.startswith('<h1') or chap is None:
            if chap:
                chap.add_item(css)
                book.add_item(chap)
                chapters.append(chap)
            count += 1
            chap = EpubHtml(title=f'chapter{count}',
                            file_name=f'chapter{count}.xhtml')
            if count-1 < len(toc_headings):
                nid = f'navPoint-h1-{count}'
                chap.structure = [Link(chap.file_name,
                                       toc_headings[count-1], nid)]
            # undertryck indrag första stycke
            if line.startswith('<p') and firstPara:
                line = line.replace('<p','<p style="text-indent:0;"',1)
            chap.content = line
            firstPara = False
        else:
            if line.startswith('<p') and firstPara:
                line = line.replace('<p','<p style="text-indent:0;"',1)
            chap.content += line
            firstPara = False

    if chap:
        chap.add_item(css)
        book.add_item(chap)
        chapters.append(chap)

    # TOC, NCX, spine
    sec = []
    for c in chapters:
        for h in getattr(c,'structure', []):
            sec.append(h)
    book.toc = (
        Link('copyright.xhtml','Copyright','copyright'),
        *sec
    )
    book.add_item(epub.EpubNcx())
    nav = book.add_item(epub.EpubNav())
    nav.add_item(css)
    spine = [coverPage, cp] + (['nav'] if include_toc else []) + chapters
    book.spine = spine

    # WCAG + skriv ut
    cats = [c['value'] for c in newBook['categories']]
    setCorrectMetatags(book, newBook['ISBN'],
                       newBook['author'], cats,
                       newBook['description'])
    os.makedirs('Books', exist_ok=True)
    out = f'Books/{newBook["title"]}.epub'
    epub.write_epub(out, book, {"play_order":{'enabled':True,'start_from':1}})
    tmp = epub.read_epub(out)
    modifyOpf(tmp); modifyToc(tmp, newBook['ISBN'])

    # Rensa bilder
    for iid in images:
        removeFile(f'img/{iid}.jpg')

    print(Fore.GREEN + "EPUB skapad: " + out + Fore.RESET)
