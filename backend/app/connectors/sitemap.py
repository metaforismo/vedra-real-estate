from urllib.parse import urljoin
import xml.etree.ElementTree as ET


def sitemap_links(text: str,base: str,pattern: str='',limit: int=100) -> list[str]:
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('DTD ed entità XML non supportate.')
    try: root=ET.fromstring(text)
    except ET.ParseError as exc: raise ValueError('Sitemap XML non valida.') from exc
    if root.tag.rsplit('}',1)[-1]=='sitemapindex':
        raise ValueError('Configura una sitemap di URL specifica, non un indice di sitemap.')
    urls=[]
    for node in root.iter():
        if node.tag.rsplit('}',1)[-1]=='loc' and node.text:
            url=urljoin(base,node.text.strip())
            if (not pattern or pattern in url) and url not in urls:
                urls.append(url)
            if len(urls)>=limit: break
    return urls
