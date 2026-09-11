import 'package:dio/dio.dart';
import 'package:cookie_jar/cookie_jar.dart';
import 'package:dio_cookie_manager/dio_cookie_manager.dart';
import 'package:path_provider/path_provider.dart';

/// Wraps the Rituams Tarot Flask backend. Auth is a signed session cookie
/// (same mechanism as the website), persisted on disk so the user stays
/// logged in between app launches.
class ApiException implements Exception {
  final String code;
  final int statusCode;
  ApiException(this.code, this.statusCode);

  @override
  String toString() => 'ApiException($code, $statusCode)';
}

class ApiClient {
  static const String baseUrl = 'https://rituamstarot.com';

  final Dio _dio = Dio(BaseOptions(baseUrl: baseUrl, connectTimeout: const Duration(seconds: 15)));
  bool _cookiesReady = false;

  Future<void> _ensureCookieJar() async {
    if (_cookiesReady) return;
    final dir = await getApplicationDocumentsDirectory();
    final jar = PersistCookieJar(storage: FileStorage('${dir.path}/.cookies'));
    _dio.interceptors.add(CookieManager(jar));
    _cookiesReady = true;
  }

  Map<String, dynamic> _asJsonMap(dynamic data) {
    if (data is Map<String, dynamic>) return data;
    // Le serveur a repondu avec autre chose que du JSON (page HTML, blocage
    // reseau intermediaire, etc.) : on le signale clairement au lieu de
    // planter silencieusement sur un cast invalide.
    throw ApiException('unexpected_response', 0);
  }

  Future<Map<String, dynamic>> _get(String path, {Map<String, dynamic>? query}) async {
    await _ensureCookieJar();
    try {
      final res = await _dio.get(path, queryParameters: query);
      return _asJsonMap(res.data);
    } on DioException catch (e) {
      throw _toApiException(e);
    }
  }

  Future<Map<String, dynamic>> _post(String path, Map<String, dynamic> body) async {
    await _ensureCookieJar();
    try {
      final res = await _dio.post(
        path,
        data: body,
        options: Options(contentType: Headers.jsonContentType),
      );
      return _asJsonMap(res.data);
    } on DioException catch (e) {
      throw _toApiException(e);
    }
  }

  ApiException _toApiException(DioException e) {
    final data = e.response?.data;
    final code = (data is Map && data['error'] != null) ? data['error'].toString() : 'network_error';
    return ApiException(code, e.response?.statusCode ?? 0);
  }

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String password2,
    String nickname = '',
    String? ref,
  }) {
    return _post('/api/v1/register', {
      'email': email,
      'password': password,
      'password2': password2,
      'nickname': nickname,
      if (ref != null) 'ref': ref,
    });
  }

  Future<Map<String, dynamic>> login({required String email, required String password}) {
    return _post('/api/v1/login', {'email': email, 'password': password});
  }

  Future<Map<String, dynamic>> loginWithGoogle(String idToken) {
    return _post('/api/v1/auth/google', {'id_token': idToken});
  }

  Future<void> logout() async {
    await _post('/api/v1/logout', {});
  }

  Future<Map<String, dynamic>?> me() async {
    try {
      final res = await _get('/api/v1/me');
      return res['account'] as Map<String, dynamic>;
    } on ApiException {
      // Pas connecte, ou reponse inattendue au demarrage : on retombe sur
      // l'ecran de connexion plutot que de bloquer l'appli.
      return null;
    }
  }

  Future<List<dynamic>> spreads() async {
    final res = await _get('/api/v1/spreads');
    return res['spreads'] as List<dynamic>;
  }

  Future<Map<String, dynamic>> drawSpread(String spreadKey, {String question = ''}) {
    return _post('/api/tirage/$spreadKey', {'question': question});
  }

  Future<Map<String, dynamic>> drawInstantCard() async {
    await _ensureCookieJar();
    try {
      final res = await _dio.post('/api/anlik');
      return res.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _toApiException(e);
    }
  }

  Future<Map<String, dynamic>> jetonBalance() => _get('/api/jeton');

  Future<List<dynamic>> horoscope({String lang = 'fr'}) async {
    final res = await _get('/api/v1/horoscope', query: {'lang': lang});
    return res['signs'] as List<dynamic>;
  }

  Future<Map<String, dynamic>> compatibility(String sign1, String sign2, {String lang = 'fr'}) async {
    final res = await _get('/api/v1/compatibility', query: {'sign1': sign1, 'sign2': sign2, 'lang': lang});
    return res['result'] as Map<String, dynamic>;
  }

  Future<List<dynamic>> reviews() async {
    final res = await _get('/api/v1/reviews');
    return res['reviews'] as List<dynamic>;
  }

  String resolveImageUrl(String path) {
    if (path.startsWith('http')) return path;
    return '$baseUrl$path';
  }
}
