import 'package:flutter/material.dart';
import '../api_client.dart';
import '../theme.dart';

class ReadingScreen extends StatefulWidget {
  final ApiClient api;
  final VoidCallback onBalanceChanged;
  const ReadingScreen({super.key, required this.api, required this.onBalanceChanged});

  @override
  State<ReadingScreen> createState() => _ReadingScreenState();
}

class _ReadingScreenState extends State<ReadingScreen> {
  List<dynamic> _spreads = [];
  Map<String, dynamic>? _result;
  bool _loading = false;
  String? _error;
  final _questionCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadSpreads();
  }

  Future<void> _loadSpreads() async {
    try {
      final spreads = await widget.api.spreads();
      if (mounted) setState(() => _spreads = spreads);
    } catch (_) {
      // silencieux : l'ecran reste utilisable, l'utilisateur peut retenter
    }
  }

  Future<void> _draw(String spreadKey) async {
    setState(() {
      _loading = true;
      _error = null;
      _result = null;
    });
    try {
      final result = await widget.api.drawSpread(spreadKey, question: _questionCtrl.text.trim());
      setState(() => _result = result);
      widget.onBalanceChanged();
    } on ApiException catch (e) {
      setState(() => _error = e.code == 'insufficient_funds'
          ? 'Solde de jetons insuffisant.'
          : 'Impossible de faire le tirage pour le moment.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_result != null) {
      return _buildResult();
    }
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Tirage de tarot', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            TextField(
              controller: _questionCtrl,
              decoration: const InputDecoration(hintText: 'Ta question (optionnel)'),
            ),
            const SizedBox(height: 16),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(_error!, style: const TextStyle(color: RTColors.error)),
              ),
            if (_loading) const Center(child: Padding(
              padding: EdgeInsets.all(24),
              child: CircularProgressIndicator(color: RTColors.gold),
            )),
            if (!_loading)
              ..._spreads.map((s) => Card(
                    margin: const EdgeInsets.only(bottom: 10),
                    child: ListTile(
                      title: Text(s['name'], style: const TextStyle(color: RTColors.text)),
                      subtitle: Text('${s['count']} carte(s)', style: const TextStyle(color: RTColors.textDim)),
                      trailing: const Icon(Icons.chevron_right, color: RTColors.gold),
                      onTap: () => _draw(s['id']),
                    ),
                  )),
          ],
        ),
      ),
    );
  }

  Widget _buildResult() {
    final spread = _result!['spread'] as List<dynamic>;
    return SafeArea(
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                IconButton(
                  icon: const Icon(Icons.arrow_back, color: RTColors.goldSoft),
                  onPressed: () => setState(() => _result = null),
                ),
                Expanded(
                  child: Text(_result!['name'] ?? '', style: Theme.of(context).textTheme.titleLarge,
                      textAlign: TextAlign.center),
                ),
                const SizedBox(width: 48),
              ],
            ),
          ),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: spread.length,
              itemBuilder: (context, i) {
                final item = spread[i];
                final card = item['card'];
                return Card(
                  margin: const EdgeInsets.only(bottom: 14),
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(item['position'], style: const TextStyle(color: RTColors.gold, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: Image.network(
                                widget.api.resolveImageUrl(card['image']),
                                width: 64, height: 96, fit: BoxFit.cover,
                                errorBuilder: (_, __, ___) => const SizedBox(width: 64, height: 96),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                '${card['name']}${card['orientation'] == 'reversed' ? ' (inversée)' : ''}',
                                style: const TextStyle(color: RTColors.goldSoft, fontWeight: FontWeight.bold),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(card['intro'] ?? '', style: const TextStyle(color: RTColors.text)),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
