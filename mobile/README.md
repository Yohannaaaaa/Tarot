# Rituams Tarot — application mobile native

Application Flutter qui remplace le TWA (wrapper web) par une vraie app native.
Elle parle au backend Flask existant via `/api/v1/*` (voir `lib/api_client.dart`).

## Récupérer un APK de test (sans installer Flutter)

Chaque push qui touche `mobile/` déclenche une build automatique sur GitHub Actions :

1. Va dans l'onglet **Actions** du dépôt GitHub
2. Ouvre le run le plus récent de **"Build mobile app (debug APK)"**
3. Télécharge l'artifact **rituams-tarot-debug-apk** (fichier `.zip` contenant `app-debug.apk`)
4. Transfère l'APK sur ton téléphone Android et installe-le (autoriser "sources inconnues" si demandé)

Cet APK de debug sert uniquement à tester — il n'est pas signé pour le Play Store.

## Connexion Google dans l'app

Le bouton "Continuer avec Google" a besoin de deux choses côté Google Cloud Console
(même projet que celui qui a déjà `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` pour le site) :

1. **Renseigner `googleServerClientId`** dans `mobile/lib/google_config.dart` avec la
   valeur exacte de la variable d'environnement `GOOGLE_CLIENT_ID` du serveur
   (visible dans Render → service "tarot" → Environment). C'est un identifiant
   public, pas un secret.
2. **Créer un client OAuth "Android"** dans Google Cloud Console → APIs & Services →
   Identifiants → Créer des identifiants → ID client OAuth → type Android :
   - Nom du package : `com.rituams.tarot.debug` (pour les builds de test CI)
   - Empreinte du certificat SHA-1 : `DC:F5:3E:87:85:AC:94:7F:9A:45:E4:E9:4C:55:10:40:C8:06:2D:1E`
     (empreinte du keystore de debug fixe `mobile/ci/debug.keystore`, committé dans
     le dépôt pour rester stable entre les builds CI)

   Plus tard, pour la vraie app signée (`com.rituams.tarot`), il faudra ajouter un
   deuxième client Android avec le SHA-1 du vrai `signing.keystore`.

## Étapes suivantes avant publication sur le Play Store

- Fournir le keystore de signature existant (`signing.keystore`, alias `my-key-alias`) en secret
  GitHub pour que la build produise un `.aab` signé avec la même clé que l'app TWA actuelle
  (obligatoire pour mettre à jour la fiche Play Store existante `com.rituams.tarot`
  sans repartir de zéro sur les 12 testeurs).
- Ajouter une icône d'app personnalisée (`flutter_launcher_icons`).
- Étendre l'API et les écrans : rendez-vous, avis clients, lecture de marc de café.
