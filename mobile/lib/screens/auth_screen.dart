import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import '../api_client.dart';
import '../google_config.dart';
import '../theme.dart';
import 'home_screen.dart';

class AuthScreen extends StatefulWidget {
  final ApiClient api;
  const AuthScreen({super.key, required this.api});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  bool _isRegister = false;
  bool _loading = false;
  String? _error;

  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _password2Ctrl = TextEditingController();
  final _nicknameCtrl = TextEditingController();
  bool _obscure = true;

  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: ['email'],
    serverClientId: googleServerClientId,
  );

  Future<void> _submitGoogle() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final account = await _googleSignIn.signIn();
      if (account == null) {
        // L'utilisateur a annule la selection de compte.
        setState(() => _loading = false);
        return;
      }
      final auth = await account.authentication;
      final idToken = auth.idToken;
      if (idToken == null) {
        throw ApiException('error_google_not_configured', 0);
      }
      await widget.api.loginWithGoogle(idToken);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => HomeScreen(api: widget.api)),
      );
    } on ApiException catch (e) {
      setState(() => _error = _errorMessages[e.code] ?? "Erreur Google (${e.code}).");
    } catch (e) {
      setState(() => _error = "Erreur Google inattendue : $e");
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  static const Map<String, String> _errorMessages = {
    'error_email_required': "Adresse e-mail invalide.",
    'error_password_short': "Le mot de passe doit contenir au moins 6 caractères.",
    'error_passwords_mismatch': "Les mots de passe ne correspondent pas.",
    'error_email_taken': "Cette adresse e-mail est déjà utilisée.",
    'error_invalid_credentials': "E-mail ou mot de passe incorrect.",
    'network_error': "Impossible de contacter le serveur. Vérifie ta connexion.",
    'unexpected_response': "Réponse inattendue du serveur (pas du JSON). Réessaie dans un instant.",
  };

  Future<void> _submit() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      if (_isRegister) {
        await widget.api.register(
          email: _emailCtrl.text.trim(),
          password: _passwordCtrl.text,
          password2: _password2Ctrl.text,
          nickname: _nicknameCtrl.text.trim(),
        );
      } else {
        await widget.api.login(email: _emailCtrl.text.trim(), password: _passwordCtrl.text);
      }
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(builder: (_) => HomeScreen(api: widget.api)),
      );
    } on ApiException catch (e) {
      setState(() => _error = _errorMessages[e.code] ?? "Erreur (${e.code}, code ${e.statusCode}).");
    } catch (e) {
      setState(() => _error = "Erreur inattendue : $e");
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text('🔮', style: TextStyle(fontSize: 56)),
                const SizedBox(height: 8),
                Text(
                  'Rituams Tarot',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(fontSize: 28),
                ),
                const SizedBox(height: 24),
                if (_isRegister)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: TextField(
                      controller: _nicknameCtrl,
                      decoration: const InputDecoration(hintText: 'Pseudo'),
                    ),
                  ),
                TextField(
                  controller: _emailCtrl,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(hintText: 'E-mail'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _passwordCtrl,
                  obscureText: _obscure,
                  decoration: InputDecoration(
                    hintText: 'Mot de passe',
                    suffixIcon: IconButton(
                      icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off, color: RTColors.textDim),
                      onPressed: () => setState(() => _obscure = !_obscure),
                    ),
                  ),
                ),
                if (_isRegister) ...[
                  const SizedBox(height: 12),
                  TextField(
                    controller: _password2Ctrl,
                    obscureText: _obscure,
                    decoration: const InputDecoration(hintText: 'Confirmer le mot de passe'),
                  ),
                ],
                if (_error != null) ...[
                  const SizedBox(height: 14),
                  Text(_error!, style: const TextStyle(color: RTColors.error), textAlign: TextAlign.center),
                ],
                const SizedBox(height: 20),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton(
                    onPressed: _loading ? null : _submit,
                    child: _loading
                        ? const SizedBox(
                            height: 20, width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2, color: RTColors.bg))
                        : Text(_isRegister ? "S'inscrire" : 'Se connecter'),
                  ),
                ),
                const SizedBox(height: 16),
                TextButton(
                  onPressed: () => setState(() => _isRegister = !_isRegister),
                  child: Text(
                    _isRegister ? 'Déjà un compte ? Se connecter' : "Pas de compte ? S'inscrire",
                    style: const TextStyle(color: RTColors.goldSoft),
                  ),
                ),
                const SizedBox(height: 8),
                Row(children: const [
                  Expanded(child: Divider(color: RTColors.border)),
                  Padding(
                    padding: EdgeInsets.symmetric(horizontal: 10),
                    child: Text('ou', style: TextStyle(color: RTColors.textDim)),
                  ),
                  Expanded(child: Divider(color: RTColors.border)),
                ]),
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: _loading ? null : _submitGoogle,
                    icon: const Text('🔵'),
                    label: const Text('Continuer avec Google'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: RTColors.text,
                      side: const BorderSide(color: RTColors.border),
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
