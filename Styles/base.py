# Styles/base.py

# Grundläggande CSS som alla sidor i EPUB:en använder.
# OBS: EpubItem.content förväntar sig bytes, så vi kodar ner till UTF-8.
base = b"""
body {
  font-family: serif;
  line-height: 1.4;
  margin: 0 1em;
}
h1, h2, h3 {
  text-align: center;
  margin-top: 1em;
  margin-bottom: 0.5em;
}
p {
  text-indent: 1em;
  margin-bottom: 1em;
}
.cover img {
  display: block;
  margin: 0 auto;
  max-width: 100%;
}
ul, ol {
  margin-left: 2em;
  margin-bottom: 1em;
}
li {
  margin-bottom: 0.5em;
}
"""
