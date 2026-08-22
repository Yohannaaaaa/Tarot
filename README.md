# Tarot Mystique

Site de tarot en ligne, bilingue **français / türkçe**, avec bibliothèque des 78 cartes
et tirages interactifs (3 cartes, 7 cartes, oui/non, amour, carrière, général).

Construit à partir des cartes et contenus du projet MONTENOIR-VIP.

## Lancer en local

```bash
pip install -r requirements.txt
python app.py
```

Puis ouvrir http://localhost:5000

## Structure

- `app.py` — application Flask (routes, tirages, i18n FR/TR)
- `data/cards.json` — base des 78 cartes (nom, image, sens à l'endroit/à l'envers, en FR et TR)
- `scripts/build_cards.py` — script de génération de `data/cards.json`
- `static/img/cards/` — illustrations des cartes
- `templates/` — pages Jinja (accueil, cartes, détail de carte, tirage)
