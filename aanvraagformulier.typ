// ============================================
//  Gebruik in een loop:
//    .\typst compile .\test.typ .\2026-00123.pdf --input aanvraag="2026-00123" --input naam="TEST INFO" --input voornaam="TEST" --input geboortedatum="1985-04-12" --input INSZ="85041299999" --input aanvrager="Dr. Schiemsky" --input RIZIV="19919147860" --input aanvraagdatum="11/11/2026" --input analyses="testA, TestB" --input geslacht="M"
// ============================================
#set text(lang: "nl")
// --- Variabelen vanuit de CLI ---
#let aanvraagnummer     = sys.inputs.aanvraag
#let naam               = sys.inputs.naam
#let voornaam           = sys.inputs.voornaam
#let geboortedatum      = sys.inputs.geboortedatum
#let INSZ               = sys.inputs.INSZ
#let geslacht           = sys.inputs.geslacht
#let aanvrager          = sys.inputs.aanvrager
#let RIZIV              = sys.inputs.RIZIV
#let aanvraagdatum      = sys.inputs.aanvraagdatum
#let analyses           = sys.inputs.analyses

// --- Pagina-instellingen: één A4-pagina ---
#set page(paper: "a4", margin: (top: 2.5cm, bottom: 2cm, x: 2cm))
#set text(size: 10.5pt)
#set par(justify: true)

// --- CONTENT-BLOK BEGRENZEN TOT ÉÉN PAGINA ---
// place() neemt geen ruimte in de tekstflow in beslag,
// dus de logo-block hierboven duwt niets weg.
//#place(top + left)[
// #image("logo.webp", width: 4.5cm)
//]
#place(top + left, dy: 0cm)[
  #text(size: 9pt, weight: "bold")[
    Labo Klinische Biologie\
    Tel. 089 80 67 10 (Genk)\
    Tel. 089 80 67 70 (Maaseik)\
    secretariaat.klinischlabo\@zol.be
  ]
]
#place(top + right, dy: 0cm)[
  Handtekening aanvrager
  #rect(width: 120pt, height: 60pt,)
]
// Ruimte vrijmaken zodat content níet ónder het logo begint
#v(3.2cm)

// --- Titel ---
#align(center)[
  #text(size: 16pt, weight: "bold")[Aanvraagformulier POCT]
]
// --- Identificatietabel ---
#place(top + right, dy: 4cm)[
    #table(
    columns: (4cm, 4cm),
    stroke: 0.5pt + luma(200),
    inset: 8pt,
        [*Aanvraagnummer*], [#aanvraagnummer],
        [*Aanvragend arts*], [#aanvrager],
        [*Erkenningsnummer*], [#RIZIV],
        [*Datum Aanvraag*], [#aanvraagdatum],
    )
]
#place(top + left, dy: 4cm)[
  #table(
  columns: (4cm, 5cm),
  stroke: 0.5pt + luma(200),
  inset: 8pt,
  [*Naam*], [#naam],
  [*Voornaam*], [#voornaam],
  [*Geboortedatum*], [#geboortedatum],
  [*INSZ*], [#INSZ],
  [*Geslacht*], [#geslacht],
)
]
#v(4.3cm)
#text(size: 14pt, weight: "bold")[Aangevraagde testen:]

#for regel in analyses.split("|") [
  #regel \
]

#v(1fr)   // duwt het commentaar-blok naar de onderkant van de pagina

// --- Commentaar (blijft onderaan het verslag staan) ---
#block(
  fill: luma(248),
  stroke: (left: 2.5pt + gray),
  inset: 10pt,
  width: 100%
)[
  #text(size: 9.5pt)[
Labo ZOL Genk - T 089 80 67 10\
Labo ZOL Maas en Kempen - T 089 80 67 70\
https://www.zol.be/klinisch-laboratorium
  ]
]
