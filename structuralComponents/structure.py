# structuralComponents/structure.py

def getCoverPageXml(coverImgPath: str) -> str:
    """
    Returnerar XHTML för omslagssidan, där coverImgPath pekar på
    img-mappen i EPUB:ns rot.
    """
    return f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>Omslag</title>
  </head>
  <body>
    <div class="cover">
      <img src="{coverImgPath}" alt="Omslagsbild"/>
    </div>
  </body>
</html>'''
