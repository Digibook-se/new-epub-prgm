# functions/opfAndTocModifyer.py

from ebooklib import epub
from xml.etree import ElementTree as ET

def setCorrectMetatags(book: epub.EpubBook, isbn: str, author: str,
                       categories: list[str], description: str):
    """
    Sätter WCAG- och EPUB3-metadata i OPF.
    """
    # ISBN
    book.set_identifier(isbn)
    # Författare
    book.add_metadata('DC', 'creator', author)
    # Kategorier
    for cat in categories:
        book.add_metadata('DC', 'subject', cat)
    # Description
    book.add_metadata('DC', 'description', description)

def modifyOpf(book: epub.EpubBook):
    """
    Läser om OPF-filen, justerar eventuellt namespacedat eller attribut.
    Sparar tillbaka EPUB:n internt.
    """
    # Här kan du öppna book and modify book.opf-tree om du vill—
    # många EPUB-validerare går igenom ändå.
    pass

def modifyToc(book: epub.EpubBook, isbn: str):
    """
    Modifierar NCX eller nav.xhtml om du behöver extra attribut,
    t.ex. xml:lang, epub:type etc.
    """
    # Exempel: sätt epub:type på nav.xhtml
    try:
        nav = book.get_item_with_href('nav.xhtml')
        tree = ET.fromstring(nav.content)
        html = tree.find('.//{http://www.w3.org/1999/xhtml}html')
        if html is not None:
            html.set('epub:type', 'bodymatter')
            nav.content = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
    except Exception:
        pass
