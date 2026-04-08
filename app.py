
import os
import json
import base64
from flask import Flask, render_template, request, jsonify
import anthropic

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """Tu es Léon, le meilleur expert mondial en optimisation d'annonces Airbnb. Tu as analysé plus de 50 000 annonces en France et formé des centaines de conciergeries. Tu maîtrises l'algorithme Airbnb 2025-2026 dans ses moindres détails.

Tu connais par cœur les best practices Airbnb :
- Les titres qui convertissent le mieux : émotionnels + localisation + différenciant unique, 50 caractères max
- Les photos qui performent : lumière naturelle, angle légèrement surélevé, pièce principale en couverture, lifestyle shots
- Les descriptions qui convertissent : structure Promesse → Expérience → Quartier → Pratique, emojis, alinéas, keywords NLP
- Les équipements qui font la différence : sèche-cheveux (+12% réservations), machine à café (+8%), bureau dédié (+15% clientèle business)
- Les paramètres qui boostent : Instant Book (+25-40% visibilité), politique flexible (+18% taux conversion)
- La tarification optimale : pricing dynamique actif = signal qualité algorithme

TON STYLE ABSOLU :
- Tu vouvoies avec chaleur et bienveillance — comme un ami expert qui veut le meilleur pour eux
- Tu valorises TOUJOURS les atouts avant de suggérer des améliorations
- Tu formules en opportunités : "Vous pourriez capturer X% de réservations supplémentaires en..."
- Tu es ULTRA SPÉCIFIQUE : tu cites des éléments précis vus dans les screenshots
- Tu donnes TOUJOURS des chiffres ou verbatims consommateurs pour chaque recommandation
- Format : JSON strict uniquement"""


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
        "text": """Analyse visuellement ces screenshots d'annonce Airbnb en expert. Retourne UNIQUEMENT ce JSON :
{
  "photo_couverture": {"qualite": "excellent|bon|moyen|faible", "angle": "description", "lumiere": "naturelle|artificielle|mixte", "emotion": "émotion déclenchée", "probleme": "problème principal ou null"},
  "photos_analysees": [{"numero": 1, "description": "ce qu'on voit", "qualite": "excellent|bon|moyen|faible", "probleme": "problème ou null", "recommendation": "amélioration concrète"}],
  "eclairage_general": "naturel|artificiel|mixte",
  "style_deco": "description du style en 5 mots",
  "coherence_visuelle": "forte|moyenne|faible",
  "incoherences": ["liste des incohérences détectées"],
  "elements_distinctifs": ["éléments uniques et différenciants"],
  "titre_visible": "titre si visible sinon null",
  "description_visible": "texte visible sinon null",
  "note_visible": "note si visible sinon null",
  "prix_visible": "prix si visible sinon null",
  "badge_visible": "Coup de Coeur|Superhost|Aucun",
  "nb_avis_visible": "nombre si visible sinon null",
  "equipements_visibles": ["équipements visibles dans les photos"],
  "type_bien": "Studio|Appartement|Maison|Chambre|Autre",
  "ville_detectee": "ville/quartier si détecté sinon null",
  "impression_generale": "synthèse experte en 1 phrase"
}"""
    })
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}]
    )
    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def call_2_scoring(vision_data):
    prompt = f"""En tant qu'expert Airbnb, analyse ces données visuelles et score les 4 dimensions :
{json.dumps(vision_data, ensure_ascii=False, indent=2)}

Retourne UNIQUEMENT ce JSON :
{{
  "visibilite": {{
    "score": number,
    "verdict_court": "phrase 8 mots max",
    "points_forts": ["max 2 points forts concrets"],
    "points_faibles": ["max 3 points faibles concrets"],
    "nb_optimisations": number,
    "gain_potentiel": "+XX pts score global"
  }},
  "premier_regard": {{
    "score": number,
    "verdict_court": "phrase 8 mots max",
    "points_forts": ["max 2"],
    "points_faibles": ["max 3"],
    "nb_optimisations": number,
    "gain_potentiel": "+XX% CTR mobile"
  }},
  "pouvoir_conviction": {{
    "score": number,
    "verdict_court": "phrase 8 mots max",
    "points_forts": ["max 2"],
    "points_faibles": ["max 3"],
    "nb_optimisations": number,
    "gain_potentiel": "+XX% taux réservation"
  }},
  "satisfaction_voyageur": {{
    "score": number,
    "verdict_court": "phrase 8 mots max",
    "points_forts": ["max 2"],
    "points_faibles": ["max 3"],
    "nb_optimisations": number,
    "gain_potentiel": "-XX% risque avis négatif"
  }},
  "score_global": number,
  "profil_annonce": "ex: Appartement design · Lyon 3e · Couple/Solo · Milieu de gamme sous-exploité"
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


def call_3_recommendations(vision_data, scoring_data):
    ville = vision_data.get('ville_detectee', 'France')
    prix = vision_data.get('prix_visible', 'non détecté')
    type_bien = vision_data.get('type_bien', 'bien')

    prompt = f"""En tant qu'expert Airbnb mondial, génère un rapport EXHAUSTIF et EXPERT pour cette annonce.

Données visuelles : {json.dumps(vision_data, ensure_ascii=False)}
Scoring : {json.dumps(scoring_data, ensure_ascii=False)}
Ville : {ville} | Prix : {prix}€/nuit | Type : {type_bien}

RÈGLES ABSOLUES :
- Chaque recommandation = CE QUI NE VA PAS > POURQUOI (avec chiffre ou verbatim conso) > SOLUTION À COPIER-COLLER
- Toujours citer des éléments SPÉCIFIQUES vus dans les screenshots
- Toujours donner des chiffres : "X% des voyageurs...", "+XX% de réservations", "Les annonces avec X obtiennent Y fois plus de clics"
- Minimum 3 options pour les titres, 2 options pour les descriptions
- Ton chaleureux et encourageant — jamais condescendant

Retourne UNIQUEMENT ce JSON complet :
{{
  "sections": {{

    "titre": {{
      "score_section": number,
      "priorite": "Prioritaire|Important|À planifier",
      "gain_potentiel": "+XX% CTR",
      "titre_actuel": "titre détecté ou null",
      "problemes": [
        {{"probleme": "ce qui ne va pas", "pourquoi": "explication avec chiffre ou verbatim", "impact": "+XX% si corrigé"}}
      ],
      "options": [
        {{"option": 1, "titre": "nouveau titre complet", "angle": "Émotionnel|Localisation|Différenciant|NLP|Bénéfice", "pourquoi": "logique en 1 phrase", "ctr_estime": "+XX%"}},
        {{"option": 2, "titre": "nouveau titre complet", "angle": "...", "pourquoi": "...", "ctr_estime": "+XX%"}},
        {{"option": 3, "titre": "nouveau titre complet", "angle": "...", "pourquoi": "...", "ctr_estime": "+XX%"}}
      ]
    }},

    "description": {{
      "score_section": number,
      "priorite": "Prioritaire|Important|À planifier",
      "gain_potentiel": "+XX% conversion",
      "problemes": [
        {{"probleme": "ce qui ne va pas", "pourquoi": "explication avec chiffre", "impact": "impact si corrigé"}}
      ],
      "options": [
        {{
          "option": 1,
          "style": "Émotionnel et storytelling",
          "texte": "Description complète réécrite avec emojis et alinéas.\\n\\n🏠 [Accroche forte 2 lignes]\\n\\n✨ [Le logement 3-4 lignes avec atouts spécifiques]\\n\\n📍 [Le quartier avec 2-3 vrais restaurants/cafés/lieux emblématiques à proximité]\\n\\n🚇 [Accès et transports]\\n\\n📋 [Pratique : équipements clés, check-in, règles en positif]"
        }},
        {{
          "option": 2,
          "style": "Business et pratique",
          "texte": "Description alternative orientée voyageur business avec les mêmes sections"
        }}
      ]
    }},

    "photos": {{
      "score_section": number,
      "priorite": "Prioritaire|Important|À planifier",
      "gain_potentiel": "+XX% CTR",
      "best_practices": ["Les annonces avec photos professionnelles reçoivent 40% de réservations supplémentaires", "La photo de couverture représente 70% de la décision de clic sur mobile", "Les photos lifestyle (table dressée, livre ouvert, café fumant) augmentent le CTR de 23%"],
      "analyse_photos": [
        {{"numero": 1, "probleme": "ce qui ne va pas précisément", "pourquoi": "pourquoi c'est problématique", "recommandation": "instruction précise pour refaire cette photo"}}
      ],
      "photos_manquantes": [
        {{"photo": "description de la photo à prendre", "pourquoi": "impact sur les réservations", "conseil_technique": "angle, lumière, composition précis"}}
      ],
      "ordre_recommande": ["description photo 1", "description photo 2", "description photo 3"]
    }},

    "equipements": {{
      "score_section": number,
      "priorite": "Prioritaire|Important|À planifier",
      "gain_potentiel": "+XX% réservations",
      "equipements_a_cocher": [
        {{"equipement": "nom Airbnb exact", "pourquoi": "X% des voyageurs filtrent sur cet équipement", "impact": "+XX% visibilité dans les recherches"}}
      ],
      "achats_recommandes": [
        {{"achat": "équipement à acheter", "prix_estime": "XX€", "impact": "verbatim ou chiffre précis", "priorite": "Haute|Moyenne|Basse"}}
      ]
    }},

    "tarification": {{
      "score_section": number,
      "priorite": "Prioritaire|Important|À planifier",
      "gain_potentiel": "+XX€/mois",
      "problemes": [
        {{"probleme": "ce qui ne va pas", "pourquoi": "explication chiffrée", "impact": "impact estimé"}}
      ],
      "recommandations": [
        {{"action": "action concrète", "pourquoi": "logique avec chiffre", "implementation": "comment faire exactement"}}
      ]
    }},

    "parametres": {{
      "score_section": number,
      "priorite": "Prioritaire|Important|À planifier",
      "gain_potentiel": "+XX% visibilité",
      "problemes": [
        {{"parametre": "nom du paramètre", "statut_actuel": "ce qui est détecté", "probleme": "pourquoi c'est sous-optimal", "pourquoi": "impact algorithmique chiffré", "recommandation": "action exacte à faire"}}
      ]
    }},

    "profil_hote": {{
      "score_section": number,
      "priorite": "Prioritaire|Important|À planifier",
      "gain_potentiel": "+XX% confiance voyageur",
      "problemes": [
        {{"probleme": "ce qui ne va pas", "pourquoi": "explication", "recommandation": "action concrète à copier-coller si texte"}}
      ]
    }},

    "regles_politique": {{
      "score_section": number,
      "priorite": "Prioritaire|Important|À planifier",
      "gain_potentiel": "+XX% conversion",
      "problemes": [
        {{"regle": "nom de la règle", "statut_actuel": "détecté ou estimé", "probleme": "pourquoi sous-optimal", "pourquoi": "chiffre d'impact", "recommandation": "action à faire"}}
      ]
    }},

    "avis_reputation": {{
      "score_section": number,
      "priorite": "Prioritaire|Important|À planifier",
      "gain_potentiel": "+XX pts score",
      "analyse": "analyse de la situation actuelle des avis",
      "recommandations": [
        {{"action": "action concrète", "pourquoi": "impact chiffré", "exemple_message": "message exemple à copier si applicable"}}
      ]
    }},

    "experience_voyageur": {{
      "score_section": number,
      "priorite": "Prioritaire|Important|À planifier",
      "gain_potentiel": "+XX% avis 5 étoiles",
      "recommandations": [
        {{"action": "petite attention ou amélioration", "pourquoi": "verbatim ou chiffre", "cout_estime": "XX€ ou gratuit"}}
      ]
    }},

    "positionnement_concurrents": {{
      "score_section": number,
      "priorite": "Prioritaire|Important|À planifier",
      "position_estimee": "Top 10%|Top 25%|Milieu|Bottom 25%",
      "angle_differenciant": "votre avantage unique en 1 phrase",
      "concurrents": [
        {{"rang": 1, "profil": "type d'annonce concurrente précis", "avantages": ["ce qu'ils ont"], "score_estime": number, "comment_contrer": "action précise"}}
      ]
    }}

  }}
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
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

        vision = call_1_vision(images)
        scoring = call_2_scoring(vision)
        reco = call_3_recommendations(vision, scoring)

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
