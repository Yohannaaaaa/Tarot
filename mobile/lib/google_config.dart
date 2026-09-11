/// Identifiant client OAuth "Web" existant (meme valeur que la variable
/// d'environnement GOOGLE_CLIENT_ID sur le serveur Flask). google_sign_in
/// s'en sert comme serverClientId pour que l'ID token renvoye ait la bonne
/// audience et puisse etre verifie par le backend.
const String googleServerClientId = '387884836590-ej4na10hpj1vivjmmtjpk13ncc659b1a.apps.googleusercontent.com';
