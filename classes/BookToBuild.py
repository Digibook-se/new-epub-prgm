# classes/BookToBuild.py

class BookToBuild:
    """
    Enkel behållare för det avkodade innehållet från Word/PDF,
    där varje element är en dict med nycklarna 'Id' och 'Paragraph'.
    """
    def __init__(self):
        # List of sections, each section är en dict { 'Id': str, 'Paragraph': [runs...] }
        self.Content = []
