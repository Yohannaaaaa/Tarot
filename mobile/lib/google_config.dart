/// Identifiant client OAuth "Web" existant (meme valeur que la variable
/// d'environnement GOOGLE_CLIENT_ID sur le serveur Flask). google_sign_in
/// s'en sert comme serverClientId pour que l'ID token renvoye ait la bonne
/// audience et puisse etre verifie par le backend.
const String googleServerClientId = 'REMPLACER_PAR_GOOGLE_CLIENT_ID.apps.googleusercontent.com';
