import 'package:flutter/material.dart';
import 'api_client.dart';
import 'theme.dart';
import 'screens/auth_screen.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(const RituamsApp());
}

class RituamsApp extends StatelessWidget {
  const RituamsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Rituams Tarot',
      debugShowCheckedModeBanner: false,
      theme: buildRituamsTheme(),
      home: const _StartupGate(),
    );
  }
}

/// Verifie si une session existe deja (cookie persiste) avant de choisir
/// l'ecran de connexion ou l'ecran d'accueil.
class _StartupGate extends StatefulWidget {
  const _StartupGate();

  @override
  State<_StartupGate> createState() => _StartupGateState();
}

class _StartupGateState extends State<_StartupGate> {
  final ApiClient _api = ApiClient();
  bool _checking = true;
  bool _loggedIn = false;

  @override
  void initState() {
    super.initState();
    _check();
  }

  Future<void> _check() async {
    final account = await _api.me();
    if (!mounted) return;
    setState(() {
      _loggedIn = account != null;
      _checking = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator(color: RTColors.gold)),
      );
    }
    return _loggedIn ? HomeScreen(api: _api) : AuthScreen(api: _api);
  }
}
