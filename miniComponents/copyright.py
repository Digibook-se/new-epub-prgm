# miniComponents/copyright.py

def getCopyrightPage(
    book_title: str,
    author: str,
    photographer: str,
    isbn: str
) -> str:
    """
    Returnerar XHTML för en enkel copyright-sida.
    """
    return f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Copyright</title>
  </head>
  <body>
    <h1>Copyright</h1>
    <p>© {author}</p>
    <p>Boken: <em>{book_title}</em></p>
    <p>Fotograf: {photographer}</p>
    <p>ISBN: {isbn}</p>
  </body>
</html>'''
