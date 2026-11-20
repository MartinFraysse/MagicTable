// Page de garde du PDF de la documentation (Typst) : style sombre, halos de couleur.
// Compilée par « genpdf » (ou « project pdf <nom> ») → docs/pdf/<nom>.pdf.
// Les données arrivent par --input (voir project.sh, cmd_pdf) : nom, resume, version, date.
// Valeurs par défaut ci-dessous pour un aperçu direct :
//   typst compile docs/pdf/page-de-garde.typ /tmp/apercu.pdf
// Propre à ce projet : couleurs, halos et textes se changent librement ici.

#let nom = sys.inputs.at("nom", default: "MagicTable")
#let resume = sys.inputs.at("resume", default: "") // vide : pas de résumé affiché
#let version = sys.inputs.at("version", default: "0.1") // version du projet (dernier tag git)
#let date = sys.inputs.at("date", default: datetime.today().display("[day]/[month]/[year]"))

// Couleurs
#let fond = rgb("#070A13")
#let violet = rgb("#6D28D9")
#let bleu = rgb("#0EA5E9")
#let rose = rgb("#EC4899")
#let cyan = rgb("#22D3EE")
#let lavande = rgb("#C4B5FD")

#set document(title: nom + " — Documentation")
#set page(paper: "a4", margin: 0pt, fill: fond)
#set text(font: "Inter", fill: white, lang: "fr")

// Grille très fine sur toute la page.
#place(top + left, rect(width: 100%, height: 100%, fill: tiling(size: (14mm, 14mm))[
  #place(line(start: (0pt, 0pt), end: (14mm, 0pt), stroke: 0.4pt + white.transparentize(94%)))
  #place(line(start: (0pt, 0pt), end: (0pt, 14mm), stroke: 0.4pt + white.transparentize(94%)))
]))

// Halos flous : couleur, position (x, y), rayon, transparence.
#let halo(couleur, x, y, r, t) = place(top + left, dx: x, dy: y,
  circle(radius: r, fill: gradient.radial(couleur.transparentize(t), fond.transparentize(100%), radius: 50%)))
#halo(violet, 60mm, -40mm, 110mm, 20%)
#halo(bleu, -50mm, 60mm, 90mm, 35%)
#halo(rose, 110mm, 150mm, 80mm, 55%)

// En-tête
#place(top + left, dx: 22mm, dy: 22mm, stack(dir: ltr, spacing: 3mm,
  circle(radius: 3pt, fill: cyan),
  text(size: 8.5pt, weight: "semibold", tracking: 0.18em, fill: white.transparentize(30%))[DOCUMENTATION · #version]))

// Nom du projet et résumé (le résumé n'apparaît que s'il existe)
#place(top + left, dx: 22mm, dy: 120mm, block(width: 166mm, stack(spacing: 0pt,
  par(leading: 0.1em, text(font: "Inter Display", size: 66pt, weight: "black", tracking: -0.045em,
    fill: gradient.linear(white, lavande, angle: 0deg))[#nom]),
  ..if resume != "" {(
    v(8mm),
    block(width: 130mm, par(leading: 0.6em, text(size: 14pt, fill: white.transparentize(35%))[#resume])),
  )},
)))

// Carte en verre : version du projet, date, sources
#let info(label, valeur) = [
  #text(size: 7pt, weight: "semibold", tracking: 0.14em, fill: white.transparentize(45%))[#upper(label)]
  #v(2mm)
  #text(size: 13pt, weight: "semibold")[#valeur]
]
#place(bottom + left, dx: 22mm, dy: -22mm, block(width: 166mm, radius: 10pt, inset: 7mm,
  fill: white.transparentize(93%), stroke: 0.6pt + white.transparentize(85%),
  grid(columns: (1fr, 1fr, 1fr),
    info("Version du projet", version), info("Date", date), info("Sources", "docs/"))))
