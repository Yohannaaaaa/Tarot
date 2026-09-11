import 'package:flutter/material.dart';
import '../api_client.dart';
import '../theme.dart';

class HoroscopeScreen extends StatefulWidget {
  final ApiClient api;
  const HoroscopeScreen({super.key, required this.api});

  @override
  State<HoroscopeScreen> createState() => _HoroscopeScreenState();
}

class _HoroscopeScreenState extends State<HoroscopeScreen> {
  List<dynamic> _signs = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final signs = await widget.api.horoscope();
      if (mounted) setState(() {
        _signs = signs;
        _loading = false;
      });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator(color: RTColors.gold));
    }
    return SafeArea(
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _signs.length,
        itemBuilder: (context, i) {
          final sign = _signs[i];
          return Card(
            margin: const EdgeInsets.only(bottom: 12),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Text(sign['symbol'], style: const TextStyle(fontSize: 22)),
                    const SizedBox(width: 8),
                    Text(sign['name'], style: const TextStyle(color: RTColors.goldSoft, fontWeight: FontWeight.bold, fontSize: 16)),
                  ]),
                  const SizedBox(height: 8),
                  Text('💛 ${sign['general']}', style: const TextStyle(color: RTColors.text)),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
