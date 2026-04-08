import os
import json
import base64
from flask import Flask, render_template, request, jsonify
import anthropic

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """Tu es Léon, expert en optimisation d'annonces Airbnb depuis 20 ans. Tu as analysé plus de 50 000 annonces en France. Tu connais l'algorithme Airbnb dans ses moindres détails, y compris les mises à jour 2025-2026 non-documentées.

Ta méthodologie repose sur 4 dimensions causales confirmées par l'Airbnb Professional Host Summit octobre 2025 :
- VISIBILITÉ (C1, ~30%) : badge Coup de Cœur/Guest Favorites, annulations hôte zéro, vitalité annonce, Superhôte, pricing dynamique actif
- PREMIER REGARD (C2, ~25%) : photo de couverture émotion vs information, titre différenciant, prix relatif concurrents locaux, promotions actives visibles
- POUVOIR DE CONVICTION (C3, ~20%) : cohérence photo/équipements cochés (Computer Vision Airbnb 2025), ratio storytelling/règlement description, Instant Book, positionnement cible clair
- SATISFACTION VOYAGEUR (C4, ~25%) : consistance sous-scores, recency avis positifs, keywords NLP 2026 dans avis, valeur perçue au prix du moment

TON STYLE :
- Tu vouvoies le propriétaire
- Tu es direct, précis, jamais générique
- Tu ancres chaque recommandation dans une logique algorithmique précise
- Tu adaptes ton analyse à la ville ET au profil exact de l'annonce (romantique, business, famille, atypique)
- Tu ne dis jamais "améliorez vos photos" — tu dis exactement QUELLE photo, POURQUOI, QUEL impact attendu
- Pour le wording : tu réécris concrètement — le propriétaire copie-colle directement dans Airbnb
- Format de réponse : JSON strict uniquement, aucun texte en dehors du JSON"""


def encode_image(image_file):
    return base64.standard_b64encode(image_file.read()).decode("utf-8")


def call_1_vision(images):
    content = []
    for img_data, media_type in images:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": img_data}
        })
    content.append({
        "type": "text",
        "text": """Analyse visuellement ces screenshots d'annonce Airbnb. Retourne UNIQUEMENT ce JSON sans aucun texte avant ou après :
{
  "photo_couverture": {
    "qualite": "excellent|bon|moyen|faible",
    "emotion": "description de l'émotion déclenchée en 10 mots",
    "probleme": "problème principal si existe, sinon null"
  },
  "eclairage": "naturel|artificiel|mixte",
  "identite_visuelle": {
    "coherence": "forte|moyenne|faible",
    "style": "description du style décoratif en 5 mots"
  },
  "incoherences_detectees": ["liste des incohérences photo/description visibles"],
  "elements_distinctifs": ["liste des éléments uniques différenciants"],
  "titre_visible": "titre si visible, sinon null",
  "description_visible": "premiers 50 mots si visible, sinon null",
  "impression_generale": "synthèse en 1 phrase percutante"
}"""
    })

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}]
    )
    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def call_2_scoring(vision_data, form_data):
    prompt = f"""Sur la base de cette analyse visuelle des screenshots :
{json.dumps(vision_data, ensure_ascii=False, indent=2)}

Déduis et score les 4 dimensions sur 100 en te basant uniquement sur ce que tu vois.
Si certaines informations ne sont pas visibles (note, prix, badge), indique-le dans le verdict et score en conséquence.
Sois précis et calibré — un score de 80+ doit être mérité.
Retourne UNIQUEMENT ce JSON :
{{
  "visibilite": {{
    "score": number,
    "verdict_court": "phrase 8 mots max expliquant le score",
    "points_forts": ["max 2 points forts concrets"],
    "points_faibles": ["max 3 points faibles concrets"],
    "nb_optimisations_cachees": number,
    "impact_potentiel": "+XX pts de score global estimés"
  }},
  "premier_regard": {{
    "score": number,
    "verdict_court": "phrase 8 mots max",
    "points_forts": ["max 2"],
    "points_faibles": ["max 3"],
    "nb_optimisations_cachees": number,
    "impact_potentiel": "+XX% CTR mobile estimé"
  }},
  "pouvoir_conviction": {{
    "score": number,
    "verdict_court": "phrase 8 mots max",
    "points_forts": ["max 2"],
    "points_faibles": ["max 3"],
    "nb_optimisations_cachees": number,
    "impact_potentiel": "+XX% taux de réservation estimé"
  }},
  "satisfaction_voyageur": {{
    "score": number,
    "verdict_court": "phrase 8 mots max",
    "points_forts": ["max 2"],
    "points_faibles": ["max 3"],
    "nb_optimisations_cachees": number,
    "impact_potentiel": "-XX% risque avis négatif estimé"
  }},
  "score_global": number,
  "profil_annonce": "ex: Studio design · Lyon 3e · Couple/Solo · Milieu de gamme sous-exploité",
  "ville_detectee": "ville détectée depuis les screenshots ou null",
  "prix_detecte": "prix détecté ou null",
  "note_detectee": "note détectée ou null",
  "badge_detecte": "Coup de Cœur|Superhôte|Aucun"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def call_3_recommendations(vision_data, scoring_data, form_data):
    prompt = f"""Sur la base du scoring :
{json.dumps(scoring_data, ensure_ascii=False, indent=2)}

Et de l'analyse visuelle :
{json.dumps(vision_data, ensure_ascii=False, indent=2)}

Ville : {scoring_data.get('ville_detectee', 'N/A')} · Prix : {scoring_data.get('prix_detecte', 'N/A')}€/nuit

RÈGLE ABSOLUE : génère MINIMUM 8 actions, idéalement 10 à 12. Tu dois couvrir OBLIGATOIREMENT chacune de ces 8 catégories — au moins 1 action par catégorie :
1. PHOTOS — couverture, angles, lumière, ordre, photos manquantes
2. TITRE — mots-clés NLP, différenciation vs concurrents locaux
3. DESCRIPTION — structure, storytelling, ratio règles/bénéfices, keywords Airbnb 2026
4. ÉQUIPEMENTS — équipements non cochés impactant les filtres (Espace de travail, Parking, Clim, Wifi fibre, etc.)
5. PARAMÈTRES AIRBNB — Instant Book, politique annulation, durée min séjour, fenêtre réservation
6. TARIFICATION — prix vs marché local, pricing dynamique, promotions, événements locaux
7. PROFIL HÔTE — photo profil, biographie, taux de réponse, temps de réponse affiché
8. VISIBILITÉ ALGO — badge manquant, signaux qualité, vitalité annonce, cohérence globale

Chaque action doit être ULTRA SPÉCIFIQUE à cette annonce. Cite des éléments précis vus dans les screenshots. JAMAIS de conseil générique comme "améliorez vos photos" — toujours "la photo 3 montre X, faites Y car Z".

Retourne UNIQUEMENT ce JSON :
{{
  "actions": [
    {{
      "rang": 1,
      "dimension": "Visibilité|Premier regard|Pouvoir de conviction|Satisfaction voyageur",
      "categorie": "Photos|Titre|Description|Équipements|Paramètres|Tarification|Profil hôte|Visibilité algo",
      "titre_court": "Action en 6 mots max — spécifique, pas générique",
      "ce_que_vous_faites": "Instruction ultra précise — cite un élément spécifique vu dans les screenshots ou déduit du contexte",
      "pourquoi": "Logique algorithmique en 2 phrases — impact direct sur ranking ou conversion",
      "impact_chiffre": "+XX% CTR ou +XX€/mois ou +XX pts score",
      "delai": "48h|7 jours|30 jours"
    }}
  ],
  "wording": {{
    "titre_actuel": "titre actuel si détecté sinon null",
    "description_reecrite": "Description complète réécrite en 150 mots. Structure : Promesse (30 mots) → Expérience concrète (60 mots) → Pratique (40 mots) → Appel léger (20 mots). S'adresse aux voyageurs. Intègre les keywords NLP Airbnb 2026 pertinents.",
    "equipements_a_cocher": ["liste des équipements Airbnb à cocher ou vérifier"]
  }},
  "ab_titres": [
    {{
      "rang": 1,
      "titre": "titre optimisé — variante 1",
      "angle": "Émotionnel|Localisation|Différenciant|Bénéfice|NLP",
      "logique": "Pourquoi ce titre en 1 phrase",
      "ctr_estime": "+XX% vs titre actuel"
    }},
    {{
      "rang": 2,
      "titre": "titre optimisé — variante 2",
      "angle": "Émotionnel|Localisation|Différenciant|Bénéfice|NLP",
      "logique": "Pourquoi ce titre en 1 phrase",
      "ctr_estime": "+XX% vs titre actuel"
    }},
    {{
      "rang": 3,
      "titre": "titre optimisé — variante 3",
      "angle": "Émotionnel|Localisation|Différenciant|Bénéfice|NLP",
      "logique": "Pourquoi ce titre en 1 phrase",
      "ctr_estime": "+XX% vs titre actuel"
    }},
    {{
      "rang": 4,
      "titre": "titre optimisé — variante 4",
      "angle": "Émotionnel|Localisation|Différenciant|Bénéfice|NLP",
      "logique": "Pourquoi ce titre en 1 phrase",
      "ctr_estime": "+XX% vs titre actuel"
    }},
    {{
      "rang": 5,
      "titre": "titre optimisé — variante 5",
      "angle": "Émotionnel|Localisation|Différenciant|Bénéfice|NLP",
      "logique": "Pourquoi ce titre en 1 phrase",
      "ctr_estime": "+XX% vs titre actuel"
    }}
  ],
  "concurrents": [
    {{
      "rang": 1,
      "profil": "Description du type d'annonce qui vous devance — ex: Studio design nordique avec fresque murale · Lyon 1er",
      "avantages": ["Ce qu'ils ont que vous n'avez pas — concret"],
      "score_estime": number,
      "comment_les_contrer": "Action précise pour reprendre l'avantage en 2 phrases"
    }},
    {{
      "rang": 2,
      "profil": "...",
      "avantages": ["..."],
      "score_estime": number,
      "comment_les_contrer": "..."
    }},
    {{
      "rang": 3,
      "profil": "...",
      "avantages": ["..."],
      "score_estime": number,
      "comment_les_contrer": "..."
    }},
    {{
      "rang": 4,
      "profil": "...",
      "avantages": ["..."],
      "score_estime": number,
      "comment_les_contrer": "..."
    }},
    {{
      "rang": 5,
      "profil": "...",
      "avantages": ["..."],
      "score_estime": number,
      "comment_les_contrer": "..."
    }}
  ]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        images = []
        for key in request.files:
            f = request.files[key]
            if f and f.filename:
                mt = f.content_type or "image/jpeg"
                img_data = encode_image(f)
                images.append((img_data, mt))

        if not images:
            return jsonify({"success": False, "error": "Aucune image reçue"}), 400

        form_data = {}

        vision = call_1_vision(images)
        scoring = call_2_scoring(vision, form_data)
        reco = call_3_recommendations(vision, scoring, form_data)

        return jsonify({
            "success": True,
            "vision": vision,
            "scoring": scoring,
            "recommendations": reco
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
