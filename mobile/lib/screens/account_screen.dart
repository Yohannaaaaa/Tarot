import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../api_client.dart';
import '../theme.dart';
import 'auth_screen.dart';

class AccountScreen extends StatelessWidget {
  final ApiClient api;
  final Map<String, dynamic>? account;
  final VoidCallback onRefresh;
  const AccountScreen({super.key, required this.api, required this.account, required this.onRefresh});

  Future<void> _logout(BuildContext context) async {
    await api.logout();
    if (!context.mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => AuthScreen(api: api)),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final acc = account;
    if (acc == null) {
      return const Center(child: CircularProgressIndicator(color: RTColors.gold));
    }
    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Mon compte', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(acc['nickname'] ?? '', style: const TextStyle(color: RTColors.goldSoft, fontWeight: FontWeight.bold, fontSize: 18)),
                  Text(acc['email'] ?? '', style: const TextStyle(color: RTColors.textDim)),
                  const SizedBox(height: 12),
                  Text('🪙 ${acc['balance']} jetons', style: const TextStyle(color: RTColors.text, fontSize: 16)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          if (acc['referralLink'] != null)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Parraine un ami', style: TextStyle(color: RTColors.goldSoft, fontWeight: FontWeight.bold)),
                    const SizedBox(height: 6),
                    const Text('Partage ton lien : 300 jetons offerts à chacun.', style: TextStyle(color: RTColors.textDim)),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: Text(acc['referralLink'], style: const TextStyle(color: RTColors.text), overflow: TextOverflow.ellipsis),
                        ),
                        IconButton(
                          icon: const Icon(Icons.copy, color: RTColors.gold),
                          onPressed: () {
                            Clipboard.setData(ClipboardData(text: acc['referralLink']));
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Lien copié !')),
                            );
                          },
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text('Filleuls : ${acc['referralCount']}', style: const TextStyle(color: RTColors.textDim)),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 24),
          OutlinedButton(
            style: OutlinedButton.styleFrom(
              foregroundColor: RTColors.error,
              side: const BorderSide(color: RTColors.error),
              padding: const EdgeInsets.symmetric(vertical: 14),
            ),
            onPressed: () => _logout(context),
            child: const Text('Se déconnecter'),
          ),
        ],
      ),
    );
  }
}
