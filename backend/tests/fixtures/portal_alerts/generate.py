"""Writes the synthetic portal alert fixtures (no real listing, invented ids, addresses and prices)."""
import base64
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote

OUT = Path(__file__).parent
NOTE = '<!-- SYNTHETIC FIXTURE for Vedra tests: invented listings, ids, prices and addresses. Not a real portal email. -->'

def mail(sender, subject, mid, html=None, text=None, date='Mon, 28 Sep 2026 07:12:00 +0200'):
    m = EmailMessage()
    m['From'] = sender
    m['To'] = 'avvisi@vedra.example'
    m['Subject'] = subject
    m['Date'] = date
    m['Message-ID'] = mid
    m['X-Vedra-Fixture'] = 'synthetic'
    m.set_content(text or 'Versione testo non disponibile.')
    if html:
        m.add_alternative(html, subtype='html', cte='quoted-printable')
    return bytes(m)

enc = quote('https://www.immobiliare.it/annunci/118765432/?utm_source=alert&utm_medium=email', safe='')
b64 = base64.urlsafe_b64encode(b'https://www.immobiliare.it/annunci/118700002/').decode().rstrip('=')
immo = f'''<html><body>{NOTE}
<table width="600"><tr><td>
<p>La tua ricerca: <b>Milano, Porta Romana</b> · fino a 600.000 € · <a href="https://clicks.immobiliare.it/ls/click?upn=s3arch">Modifica ricerca</a></p>
<table class="card"><tr><td><a href="https://clicks.immobiliare.it/ls/click?upn=aa1&amp;u={enc}"><img src="https://pic.example-cdn.it/synthetic/1.jpg" width="560" alt="Foto"></a></td></tr>
<tr><td><a href="https://clicks.immobiliare.it/ls/click?upn=aa2&amp;u={enc}"><b>Trilocale via Crema 12, Porta Romana, Milano</b></a>
<p><b>€ 520.000</b></p><p>3 locali · 95 m² · 2 bagni · Piano 3</p>
<a href="https://clicks.immobiliare.it/ls/click?upn=aa3&amp;u={enc}">Vedi annuncio</a></td></tr></table>
<table class="card"><tr><td><span style="color:#c00">Prezzo ribassato</span>
<a href="https://www.immobiliare.it/annunci/118700001/?from=alert"><b>Bilocale corso Lodi 40, Lodi, Milano</b></a>
<p><s>€ 460.000</s> <b>€ 435.000</b> (-5%)</p><p>2 locali · 68 m²</p></td></tr></table>
<table class="card"><tr><td><a href="https://t.immobiliare.it/r/{b64}"><b>Quadrilocale viale Umbria 7, Milano</b></a>
<p>Prezzo su richiesta</p><p>4 locali · 140 m²</p></td></tr></table>
<table class="card"><tr><td><a href="https://clicks.immobiliare.it/ls/click?upn=opaqueXYZ123"><b>Bilocale via Ripamonti 88, Milano</b></a>
<p>€ 390.000</p><p>2 locali · 60 m²</p></td></tr></table>
<p>Non vuoi più ricevere questi avvisi? <a href="https://clicks.immobiliare.it/ls/click?upn=unsub">Disiscriviti</a> · © 2026</p>
</td></tr></table></body></html>'''
(OUT / 'immobiliare_alert.eml').write_bytes(mail('Immobiliare.it <noreply@notifiche.immobiliare.it>',
    '2 nuovi annunci e 1 ribasso per «Milano Porta Romana»', '<synthetic-immo-0001@notifiche.immobiliare.it>', html=immo))

double = quote(quote('https://www.idealista.it/immobile/31234567/', safe=''), safe='')
ideal = f'''<html><body>{NOTE}
<div style="max-width:600px"><h2>Nuovi annunci per la tua ricerca «Milano Tortona»</h2>
<div class="ad"><a href="https://email.idealista.it/c/eJx?redirect={double}"><img src="https://img.example-cdn.it/synthetic/a.jpg" alt="Appartamento"></a>
<a href="https://email.idealista.it/c/eJx?redirect={double}">Appartamento in via Tortona, 31, Tortona, Milano</a>
<div>680.000€</div><div>110 m² · 3 locali · 2° piano con ascensore</div></div>
<div class="ad"><a href="https://www.idealista.it/immobile/31234999/">Attico in vendita a Milano</a>
<div>1.250.000 €</div><div>180 m² · 5 locali</div></div>
<div class="ad"><a href="javascript:alert(1)">Loft via Savona 20, Milano</a><div>540.000 €</div><div>90 m²</div></div>
<div class="ad"><a href="data:text/html;base64,PGgxPng8L2gxPg==">Monolocale via Solari 3, Milano</a><div>210.000 €</div><div>35 m²</div></div>
<p><a href="https://www.idealista.it/utente/avvisi/">Gestisci i tuoi avvisi</a></p></div></body></html>'''
(OUT / 'idealista_alert.eml').write_bytes(mail('idealista <avvisi@idealista.it>', 'Nuovi annunci: Milano Tortona',
    '<synthetic-idealista-0001@idealista.it>', html=ideal, date='Sun, 27 Sep 2026 19:40:00 +0200'))

casa_text = '''Nuovi immobili per la tua ricerca "Milano"
(SYNTHETIC FIXTURE for Vedra tests: invented listings, ids, prices and addresses.)

Trilocale in vendita a Milano
Via Savona 45, Tortona
€ 430.000 · 85 m² · 3 locali
https://www.casa.it/immobili/47123456/?utm_source=alert&utm_campaign=search

Bilocale in vendita a Milano
Piazza Napoli 3
€ 315.000 · 58 m² · 2 locali
https://www.casa.it/immobili/47123999/

Gestisci le tue ricerche: https://www.casa.it/utente/ricerche/
'''
(OUT / 'casa_alert.eml').write_bytes(mail('Casa.it <alert@mail.casa.it>', 'Nuovi immobili per "Milano"',
    '<synthetic-casa-0001@mail.casa.it>', text=casa_text, date='Sat, 26 Sep 2026 08:00:00 +0200'))

items = [
    ('119000001', 'Trilocale via Tortona 5, Tortona, Milano', '€ 610.000', '3 locali', '98 m²', '2 bagni'),
    ('119000002', 'Bilocale viale Coni Zugna 12, Solari, Milano', '€ 385.000', '2 locali', '62 m²', '1 bagno'),
    ('119000003', 'Quadrilocale via Savona 70, Tortona, Milano', 'Prezzo su richiesta', '4 locali', '150 m²', '2 bagni'),
]
cards = ''.join(f'''<li class="nd-list__item in-searchLayoutListItem"><div class="in-listingCard">
<a href="https://www.immobiliare.it/annunci/{i}/" class="in-listingCardTitle" title="{t}">{t}</a>
<div class="in-listingCardPrice"><span>{p}</span></div>
<div class="in-listingCardFeatureList"><span>{r}</span><span>{s}</span><span>{b}</span></div>
<img src="https://pic.example-cdn.it/synthetic/{i}.jpg" alt="{t}"></div></li>''' for i, t, p, r, s, b in items)
(OUT / 'immobiliare_results.html').write_text(f'''<!doctype html><html><head><meta charset="utf-8"><title>Case in vendita Milano</title></head><body>{NOTE}
<header><a href="https://www.immobiliare.it/">Immobiliare.it</a><a href="https://www.immobiliare.it/mutui/">Mutui</a></header>
<h1>Case in vendita a Milano, Tortona</h1><ul class="nd-list">{cards}
<li class="nd-list__item"><div class="in-adv">Pubblicità <a href="https://ads.example.com/click?x=1">Scopri l'offerta</a></div></li></ul>
<a href="https://www.immobiliare.it/agenzie-immobiliari/12345/">Agenzia Synthetic</a>
<a href="https://www.immobiliare.it/vendita-case/milano/?pag=2">Successiva</a></body></html>''')

(OUT / 'idealista_results.html').write_text(f'''<!doctype html><html><head><meta charset="utf-8"><title>Case e appartamenti in vendita a Milano</title></head><body>{NOTE}
<main><section class="items-container">
<article class="item"><div class="item-info-container"><a href="/immobile/31300001/" class="item-link" title="Appartamento in via Tortona, 22, Milano">Appartamento in via Tortona, 22, Milano</a>
<div class="price-row"><span class="item-price">455.000<span>€</span></span></div>
<span class="item-detail">3 locali</span><span class="item-detail">88 m²</span><span class="item-detail">Piano 2</span></div></article>
<article class="item"><div class="item-info-container"><a href="/immobile/31300002/" class="item-link">Bilocale in via Savona, 15, Milano</a>
<div class="price-row"><span class="item-price">299.000<span>€</span></span><span class="pricedown">Prezzo ribassato del 5%</span></div>
<span class="item-detail">2 locali</span><span class="item-detail">55 m²</span></div></article>
<article class="adv">Consulenza mutui <a href="/mutui/">Scopri</a></article>
</section><a href="/vendita-case/milano-milano/pagina-2.htm">Successiva</a></main></body></html>''')
print('written', sorted(p.name for p in OUT.iterdir()))
