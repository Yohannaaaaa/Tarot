import 'package:flutter/material.dart';
import '../api_client.dart';
import '../theme.dart';
import 'reading_screen.dart';
import 'horoscope_screen.dart';
import 'account_screen.dart';

class HomeScreen extends StatefulWidget {
  final ApiClient api;
  const HomeScreen({super.key, required this.api});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tab = 0;
  Map<String, dynamic>? _account;

  @override
  void initState() {
    super.initState();
    _refreshAccount();
  }

  Future<void> _refreshAccount() async {
    final account = await widget.api.me();
    if (mounted) setState(() => _account = account);
  }

  @override
  Widget build(BuildContext context) {
    final screens = [
      ReadingScreen(api: widget.api, onBalanceChanged: _refreshAccount),
      HoroscopeScreen(api: widget.api),
      AccountScreen(api: widget.api, account: _account, onRefresh: _refreshAccount),
    ];
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text('🔮 '),
            const Text('Rituams Tarot'),
            if (_account != null) ...[
              const Spacer(),
              Text('🪙 ${_account!['balance']}', style: const TextStyle(color: RTColors.goldSoft, fontSize: 14)),
            ],
          ],
        ),
      ),
      body: IndexedStack(index: _tab, children: screens),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _tab,
        onTap: (i) {
          setState(() => _tab = i);
          if (i == 2) _refreshAccount();
        },
        type: BottomNavigationBarType.fixed,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.style), label: 'Tirage'),
          BottomNavigationBarItem(icon: Icon(Icons.nights_stay), label: 'Horoscope'),
          BottomNavigationBarItem(icon: Icon(Icons.person), label: 'Compte'),
        ],
      ),
    );
  }
}
