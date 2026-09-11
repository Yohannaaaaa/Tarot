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

## Étapes suivantes avant publication sur le Play Store

- Fournir le keystore de signature existant (`signing.keystore`, alias `my-key-alias`) en secret
  GitHub pour que la build produise un `.aab` signé avec la même clé que l'app TWA actuelle
  (obligatoire pour mettre à jour la fiche Play Store existante `com.rituams.tarot`
  sans repartir de zéro sur les 12 testeurs).
- Ajouter une icône d'app personnalisée (`flutter_launcher_icons`).
- Étendre l'API et les écrans : rendez-vous, avis clients, lecture de marc de café.
