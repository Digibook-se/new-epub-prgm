# functions/createHelpers.py
import os
from ebooklib.utils import create_pagebreak as _pb

def create_pagebreak(page_number: int) -> bytes:
    """Wrapper runt ebooklib.utils.create_pagebreak."""
    return _pb(page_number)

def getCoverImg(newBook: dict) -> str:
    """Returnera sökväg till omslagsbild (om någon); annars standard."""
    path = newBook.get('cover_path') or ''
    if os.path.exists(path):
        return path
    return 'img/dummy.jpg'

def getOpeningElementTag(rtype: str) -> str:
    """Mappar run-typ till HTML-öppningstag."""
    return {
        'Heading1': '<h1>',
        'Rubrik1': '<h1>',
    }.get(rtype, '<p>')

def getClosingElementTag(rtype: str) -> str:
    """Mappar run-typ till HTML-stängningstag."""
    return {
        'Heading1': '</h1>',
        'Rubrik1': '</h1>',
    }.get(rtype, '</p>')

def getStyle(attr: str) -> str:
    """Mappar attribut till CSS-deklaration."""
    return {
        'bold': 'font-weight:600;',
        'italic': 'font-style:italic;',
        'underline': 'text-decoration:underline;',
        'center': 'text-align:center;',
        'right': 'text-align:right;',
    }.get(attr, '')

def removeFile(path: str):
    """Raderar fil om den finns."""
    try:
        os.remove(path)
    except OSError:
        pass
