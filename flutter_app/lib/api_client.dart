import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiClient {
  ApiClient._() {
    _dio = Dio(
      BaseOptions(
        baseUrl: _normalizeBaseUrl(
          const String.fromEnvironment('API_BASE_URL').isNotEmpty
              ? const String.fromEnvironment('API_BASE_URL')
              : (kIsWeb
                  ? 'http://127.0.0.1:8000/api'
                  : 'http://10.0.2.2:8000/api'),
        ),
        connectTimeout: const Duration(seconds: 15),
        receiveTimeout: const Duration(seconds: 60),
        headers: {'Accept': 'application/json'},
      ),
    );
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _storage.read(key: _tokenKey);
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
      ),
    );
  }

  static final ApiClient instance = ApiClient._();

  static const _tokenKey = 'college_financial_access_token';
  static const _baseUrlKey = 'college_financial_api_url';
  static const _storage = FlutterSecureStorage();

  late final Dio _dio;

  String get baseUrl => _dio.options.baseUrl;

  static String _normalizeBaseUrl(String value) {
    final trimmed = value.trim().replaceAll(RegExp(r'/+$'), '');
    if (trimmed.isEmpty) {
      throw ArgumentError.value(value, 'value', 'API URL cannot be empty');
    }
    return trimmed.endsWith('/api') ? trimmed : '$trimmed/api';
  }

  Future<void> loadSavedBaseUrl() async {
    final preferences = await SharedPreferences.getInstance();
    final saved = preferences.getString(_baseUrlKey);
    if (saved != null && saved.trim().isNotEmpty) {
      _dio.options.baseUrl = _normalizeBaseUrl(saved);
    }
  }

  Future<void> setBaseUrl(String value) async {
    final normalized = _normalizeBaseUrl(value);
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(_baseUrlKey, normalized);
    _dio.options.baseUrl = normalized;
  }

  Future<String?> readToken() => _storage.read(key: _tokenKey);

  Future<void> saveToken(String token) =>
      _storage.write(key: _tokenKey, value: token);

  Future<void> clearToken() => _storage.delete(key: _tokenKey);

  Future<Map<String, dynamic>> getMap(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final response = await _dio.get<dynamic>(
      path,
      queryParameters: queryParameters,
    );
    return _asMap(response.data);
  }

  Future<List<dynamic>> getList(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) async {
    final response = await _dio.get<dynamic>(
      path,
      queryParameters: queryParameters,
    );
    if (response.data is! List) {
      throw const FormatException(
        'The server returned an unexpected response.',
      );
    }
    return response.data as List<dynamic>;
  }

  Future<Map<String, dynamic>> postMap(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
  }) async {
    final response = await _dio.post<dynamic>(
      path,
      data: data,
      queryParameters: queryParameters,
    );
    return _asMap(response.data);
  }

  Future<void> delete(String path) async {
    await _dio.delete<dynamic>(path);
  }

  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await postMap(
      '/auth/login',
      data: {'email': email, 'password': password},
    );
    final token = response['access_token'];
    if (token is! String || token.isEmpty) {
      throw const FormatException('The server did not return an access token.');
    }
    await saveToken(token);
    return response;
  }

  Future<Map<String, dynamic>> signUp({
    required String name,
    required String email,
    required String password,
    String? department,
  }) =>
      postMap(
        '/auth/signup',
        data: {
          'name': name,
          'email': email,
          'password': password,
          'role': 'accounts_staff',
          if (department != null && department.trim().isNotEmpty)
            'department': department.trim(),
        },
      );

  Future<Map<String, dynamic>> uploadFile({
    required String filename,
    required Uint8List bytes,
    required bool isPdf,
    String? reportName,
    String? reportYear,
  }) async {
    final form = FormData.fromMap({
      'file': MultipartFile.fromBytes(bytes, filename: filename),
      if (isPdf && reportName != null) 'report_name': reportName,
      if (isPdf && reportYear != null) 'report_year': reportYear,
    });
    final response = await _dio.post<dynamic>(
      isPdf ? '/upload/pdf' : '/upload',
      data: form,
    );
    return _asMap(response.data);
  }

  Future<Uint8List> generateReport({
    required String reportType,
    required String format,
    String? financialYear,
    String? quarter,
    String? department,
  }) async {
    final response = await _dio.post<List<int>>(
      '/reports/generate',
      data: {
        'report_type': reportType,
        'export_format': format,
        if (financialYear != null) 'financial_year': financialYear,
        if (quarter != null) 'quarter': quarter,
        if (department != null) 'department': department,
      },
      options: Options(responseType: ResponseType.bytes),
    );
    final bytes = response.data;
    if (bytes == null || bytes.isEmpty) {
      throw const FormatException('The server returned an empty report.');
    }
    return Uint8List.fromList(bytes);
  }

  Future<void> logout() async {
    try {
      await _dio.post<dynamic>('/auth/logout');
    } finally {
      await clearToken();
    }
  }

  static Map<String, dynamic> _asMap(dynamic value) {
    if (value is Map<String, dynamic>) return value;
    if (value is Map) return Map<String, dynamic>.from(value);
    throw const FormatException('The server returned an unexpected response.');
  }

  static String errorMessage(Object error) {
    if (error is DioException) {
      final detail = error.response?.data;
      if (detail is Map) {
        final message = detail['detail'];
        if (message is String) return message;
        if (message is Map && message['errors'] is List) {
          return (message['errors'] as List).join(', ');
        }
        if (message is List) {
          return message
              .map((item) => item is Map ? item['msg'] : item)
              .join(', ');
        }
      }
      if (error.type == DioExceptionType.connectionTimeout ||
          error.type == DioExceptionType.connectionError) {
        return 'Cannot reach the server. Check the API URL and make sure the backend is running.';
      }
      return error.message ?? 'The request failed. Please try again.';
    }
    if (error is FormatException) return error.message;
    if (error is ArgumentError) {
      return error.message?.toString() ?? 'Invalid value.';
    }
    return error.toString();
  }
}
