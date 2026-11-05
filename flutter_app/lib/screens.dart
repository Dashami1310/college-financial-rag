import 'package:file_picker/file_picker.dart';
import 'package:file_saver/file_saver.dart';
import 'package:flutter/material.dart';

import 'api_client.dart';

const _green = Color(0xFF0F766E);
const _ink = Color(0xFF182A29);
const _muted = Color(0xFF71817F);

String _money(dynamic value) {
  final number = value is num ? value : num.tryParse('$value') ?? 0;
  return '₹${number.toStringAsFixed(0).replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+(?!\d))'), (m) => '${m[1]},')}';
}

double _number(dynamic value) =>
    value is num ? value.toDouble() : double.tryParse('$value') ?? 0;

List<Map<String, dynamic>> _maps(dynamic value) {
  if (value is! List) return [];
  return value
      .whereType<Map>()
      .map((item) => Map<String, dynamic>.from(item))
      .toList();
}

void _message(BuildContext context, String text, {bool error = false}) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(
      SnackBar(
        content: Text(text),
        backgroundColor: error ? Colors.red.shade700 : _ink,
        behavior: SnackBarBehavior.floating,
      ),
    );
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({
    required this.onAuthenticated,
    this.initialError,
    super.key,
  });

  final ValueChanged<Map<String, dynamic>> onAuthenticated;
  final String? initialError;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _server = TextEditingController(text: ApiClient.instance.baseUrl);
  bool _loading = false;
  bool _signingUp = false;
  bool _showSettings = false;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _server.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      if (_showSettings) {
        await ApiClient.instance.setBaseUrl(_server.text);
      }
      if (_signingUp) {
        await ApiClient.instance.signUp(
          name: _name.text.trim(),
          email: _email.text.trim(),
          password: _password.text,
          department: _department.text.trim(),
        );
        if (mounted) {
          _message(context, 'Account created. You can now sign in.');
          setState(() => _signingUp = false);
        }
      } else {
        final data = await ApiClient.instance.login(
          _email.text.trim(),
          _password.text,
        );
        final user = data['user'];
        if (user is! Map) {
          throw const FormatException('The server returned an invalid user.');
        }
        widget.onAuthenticated(Map<String, dynamic>.from(user));
      }
    } catch (error) {
      if (mounted) {
        _message(context, ApiClient.errorMessage(error), error: true);
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  final _name = TextEditingController();
  final _department = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 430),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(28),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Container(
                        width: 58,
                        height: 58,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: _green.withValues(alpha: .1),
                          borderRadius: BorderRadius.circular(18),
                        ),
                        child: const Icon(
                          Icons.account_balance_wallet_outlined,
                          color: _green,
                          size: 30,
                        ),
                      ),
                      const SizedBox(height: 22),
                      Text(
                        _signingUp ? 'Create your account' : 'Welcome back',
                        style:
                            Theme.of(context).textTheme.headlineSmall?.copyWith(
                                  fontWeight: FontWeight.w800,
                                  color: _ink,
                                ),
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'College Financial Analytics',
                        style: TextStyle(color: _muted),
                      ),
                      if (widget.initialError != null) ...[
                        const SizedBox(height: 12),
                        Text(
                          'Could not restore the previous session: ${widget.initialError}',
                          style: TextStyle(color: Colors.red.shade700),
                        ),
                      ],
                      const SizedBox(height: 24),
                      if (_signingUp) ...[
                        TextFormField(
                          controller: _name,
                          decoration: const InputDecoration(
                            labelText: 'Full name',
                          ),
                          validator: (v) => (v == null || v.trim().length < 2)
                              ? 'Enter your name'
                              : null,
                        ),
                        const SizedBox(height: 12),
                      ],
                      TextFormField(
                        controller: _email,
                        keyboardType: TextInputType.emailAddress,
                        decoration: const InputDecoration(labelText: 'Email'),
                        validator: (v) => (v == null || !v.contains('@'))
                            ? 'Enter a valid email'
                            : null,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _password,
                        obscureText: true,
                        decoration: InputDecoration(
                          labelText: 'Password',
                          helperText:
                              _signingUp ? 'At least 8 characters' : null,
                        ),
                        validator: (v) =>
                            (v == null || v.length < (_signingUp ? 8 : 1))
                                ? (_signingUp
                                    ? 'Use at least 8 characters'
                                    : 'Enter your password')
                                : null,
                      ),
                      if (_signingUp) ...[
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: _department,
                          decoration: const InputDecoration(
                            labelText: 'Department (optional)',
                          ),
                        ),
                      ],
                      if (_showSettings) ...[
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: _server,
                          keyboardType: TextInputType.url,
                          decoration: const InputDecoration(
                            labelText: 'Backend server URL',
                            helperText: 'Example: http://192.168.1.10:8000',
                          ),
                          validator: (v) {
                            final uri = Uri.tryParse(v?.trim() ?? '');
                            return uri == null ||
                                    !uri.hasScheme ||
                                    uri.host.isEmpty
                                ? 'Enter a valid server URL'
                                : null;
                          },
                        ),
                      ],
                      const SizedBox(height: 18),
                      FilledButton(
                        onPressed: _loading ? null : _submit,
                        style: FilledButton.styleFrom(
                          backgroundColor: _green,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                        ),
                        child: _loading
                            ? const SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : Text(_signingUp ? 'Create account' : 'Sign in'),
                      ),
                      TextButton(
                        onPressed: _loading
                            ? null
                            : () => setState(() => _signingUp = !_signingUp),
                        child: Text(
                          _signingUp
                              ? 'Already have an account? Sign in'
                              : 'Create accounts-staff account',
                        ),
                      ),
                      Align(
                        alignment: Alignment.center,
                        child: TextButton.icon(
                          onPressed: () =>
                              setState(() => _showSettings = !_showSettings),
                          icon: const Icon(Icons.settings_ethernet, size: 18),
                          label: Text(
                            _showSettings
                                ? 'Hide server settings'
                                : 'Configure server',
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class MainShell extends StatefulWidget {
  const MainShell({required this.user, required this.onLogout, super.key});

  final Map<String, dynamic> user;
  final Future<void> Function() onLogout;

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _index = 0;
  late final List<Widget> _pages = [
    DashboardScreen(user: widget.user),
    const AnalyticsScreen(),
    const AnomaliesScreen(),
    const ForecastScreen(),
    const ChatScreen(),
    ReportsScreen(user: widget.user),
  ];

  static const _destinations = [
    NavigationDestination(
      icon: Icon(Icons.dashboard_outlined),
      label: 'Dashboard',
    ),
    NavigationDestination(icon: Icon(Icons.query_stats), label: 'Analytics'),
    NavigationDestination(
      icon: Icon(Icons.warning_amber_rounded),
      label: 'Anomalies',
    ),
    NavigationDestination(icon: Icon(Icons.trending_up), label: 'Forecast'),
    NavigationDestination(
      icon: Icon(Icons.chat_bubble_outline),
      label: 'Assistant',
    ),
    NavigationDestination(
      icon: Icon(Icons.folder_open_outlined),
      label: 'Reports',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 900;
    final current = _destinations[_index].label;
    return Scaffold(
      appBar: AppBar(
        title: Text(
          current,
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        actions: [
          if (widget.user['name'] is String)
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: Center(
                child: Text(
                  widget.user['name'] as String,
                  style: const TextStyle(color: _muted),
                ),
              ),
            ),
          IconButton(
            tooltip: 'Sign out',
            onPressed: () async {
              try {
                await widget.onLogout();
              } catch (error) {
                if (context.mounted) {
                  _message(context, ApiClient.errorMessage(error), error: true);
                }
              }
            },
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: Row(
        children: [
          if (wide)
            NavigationRail(
              selectedIndex: _index,
              onDestinationSelected: (value) => setState(() => _index = value),
              labelType: NavigationRailLabelType.all,
              destinations: _destinations
                  .map(
                    (item) => NavigationRailDestination(
                      icon: item.icon,
                      label: Text(item.label),
                    ),
                  )
                  .toList(),
            ),
          Expanded(
            child: Align(
              alignment: Alignment.topCenter,
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1200),
                child: IndexedStack(index: _index, children: _pages),
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: wide
          ? null
          : NavigationBar(
              selectedIndex: _index,
              onDestinationSelected: (value) => setState(() => _index = value),
              destinations: _destinations,
            ),
    );
  }
}

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({required this.user, super.key});
  final Map<String, dynamic> user;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? _summary;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      _summary = await ApiClient.instance.getMap('/dashboard/summary');
    } catch (error) {
      _error = ApiClient.errorMessage(error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading && _summary == null) return const LoadingView();
    if (_error != null && _summary == null) {
      return ErrorView(message: _error!, onRetry: _load);
    }
    final data = _summary ?? {};
    final departments = _maps(data['department_wise_spending']);
    final stats = [
      ('Total budget', data['total_budget'], Icons.account_balance_outlined),
      ('Expenditure', data['total_expenditure'], Icons.payments_outlined),
      ('Remaining', data['remaining_budget'], Icons.savings_outlined),
      (
        'Utilization',
        '${_number(data['budget_utilization_pct']).toStringAsFixed(1)}%',
        Icons.pie_chart_outline,
      ),
      ('Departments', data['active_departments'], Icons.domain_outlined),
      ('Transactions', data['total_transactions'], Icons.receipt_long_outlined),
    ];
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          Text(
            'Financial overview',
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(color: _ink, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 5),
          const Text(
            'A current view of your uploaded financial data.',
            style: TextStyle(color: _muted),
          ),
          const SizedBox(height: 18),
          if (_error != null) InlineError(message: _error!, onRetry: _load),
          LayoutBuilder(
            builder: (context, constraints) {
              final columns = constraints.maxWidth > 700 ? 3 : 2;
              return GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: stats.length,
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: columns,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  childAspectRatio: 1.65,
                ),
                itemBuilder: (context, index) {
                  final (label, value, icon) = stats[index];
                  return MetricCard(
                    label: label,
                    value: value is num && index < 3
                        ? _money(value)
                        : '${value ?? 0}',
                    icon: icon,
                  );
                },
              );
            },
          ),
          const SizedBox(height: 18),
          SectionCard(
            title: 'Department spending',
            trailing: IconButton(
              tooltip: 'Refresh',
              onPressed: _load,
              icon: const Icon(Icons.refresh),
            ),
            child: departments.isEmpty
                ? const EmptyView(message: 'No department data available yet.')
                : Column(
                    children: departments.map((department) {
                      final budget = _number(department['budget']);
                      final spent = _number(department['expenditure']);
                      final ratio =
                          budget > 0 ? (spent / budget).clamp(0, 1.25) : 0.0;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 15),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    '${department['department'] ?? 'Unknown'}',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ),
                                Text(
                                  _money(spent),
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            LinearProgressIndicator(
                              value: ratio.toDouble(),
                              minHeight: 8,
                              borderRadius: BorderRadius.circular(9),
                              color:
                                  spent > budget ? Colors.deepOrange : _green,
                              backgroundColor: const Color(0xFFE8EFEE),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Budget ${_money(budget)}',
                              style: const TextStyle(
                                color: _muted,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
          ),
        ],
      ),
    );
  }
}

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({super.key});
  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  Map<String, dynamic> _filters = {};
  Map<String, dynamic> _breakdown = {};
  List<Map<String, dynamic>> _comparison = [];
  String? _year;
  String? _quarter;
  String? _department;
  String? _compareFirst;
  String? _compareSecond;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      _filters = await ApiClient.instance.getMap('/analytics/filters');
      final params = <String, dynamic>{
        if (_year != null) 'financial_year': _year,
        if (_quarter != null) 'quarter': _quarter,
        if (_department != null) 'department': _department,
      };
      _breakdown = await ApiClient.instance.getMap(
        '/analytics/breakdown',
        queryParameters: params,
      );
      if (_compareFirst != null &&
          _compareSecond != null &&
          _compareFirst != _compareSecond) {
        final response = await ApiClient.instance.getMap(
          '/analytics/compare',
          queryParameters: {
            'departments': '$_compareFirst,$_compareSecond',
          },
        );
        _comparison = _maps(response['data']);
      } else {
        _comparison = [];
      }
    } catch (error) {
      _error = ApiClient.errorMessage(error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Widget _filter(
    String label,
    String? selected,
    List<dynamic> options,
    ValueChanged<String?> onChanged,
  ) =>
      DropdownButtonFormField<String>(
        initialValue: selected,
        decoration: InputDecoration(labelText: label),
        items: [
          const DropdownMenuItem(value: null, child: Text('All')),
          ...options.map(
            (value) => DropdownMenuItem(
              value: '$value',
              child: Text('$value', overflow: TextOverflow.ellipsis),
            ),
          ),
        ],
        onChanged: onChanged,
      );

  @override
  Widget build(BuildContext context) {
    final departments = _maps(_breakdown['by_department']);
    final quarters = _maps(_breakdown['by_quarter']);
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        Text(
          'Analyze your reports',
          style: Theme.of(context)
              .textTheme
              .headlineSmall
              ?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 16),
        SectionCard(
          title: 'Filters',
          child: Column(
            children: [
              _filter(
                'Financial year',
                _year,
                _filters['financial_years'] as List? ?? [],
                (v) {
                  _year = v;
                  _load();
                },
              ),
              const SizedBox(height: 10),
              _filter(
                'Quarter',
                _quarter,
                _filters['quarters'] as List? ?? [],
                (v) {
                  _quarter = v;
                  _load();
                },
              ),
              const SizedBox(height: 10),
              _filter(
                'Department',
                _department,
                _filters['departments'] as List? ?? [],
                (v) {
                  _department = v;
                  _load();
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        if (_error != null) InlineError(message: _error!, onRetry: _load),
        if (_loading) const LinearProgressIndicator(),
        SectionCard(
          title: 'By department',
          child: departments.isEmpty
              ? const EmptyView(message: 'No results for the selected filters.')
              : Column(
                  children: departments.map((row) {
                    final spent = _number(row['actual_expenditure']);
                    final budget = _number(row['budget_allocated']);
                    return ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text('${row['department'] ?? 'Department'}'),
                      subtitle: Text(
                        'Budget ${_money(budget)} · ${row['transactions'] ?? 0} transactions',
                      ),
                      trailing: Text(
                        _money(spent),
                        style: const TextStyle(fontWeight: FontWeight.w700),
                      ),
                    );
                  }).toList(),
                ),
        ),
        const SizedBox(height: 14),
        SectionCard(
          title: 'Quarterly trend',
          child: quarters.isEmpty
              ? const EmptyView(message: 'No quarterly data available.')
              : Column(
                  children: quarters
                      .map(
                        (row) => ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(
                            '${row['financial_year'] ?? ''} ${row['quarter'] ?? ''}',
                          ),
                          trailing: Text(_money(row['actual_expenditure'])),
                        ),
                      )
                      .toList(),
                ),
        ),
        const SizedBox(height: 14),
        SectionCard(
          title: 'Compare departments',
          child: Column(
            children: [
              _filter(
                'First department',
                _compareFirst,
                _filters['departments'] as List? ?? [],
                (value) => setState(() => _compareFirst = value),
              ),
              const SizedBox(height: 10),
              _filter(
                'Second department',
                _compareSecond,
                _filters['departments'] as List? ?? [],
                (value) => setState(() => _compareSecond = value),
              ),
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.tonal(
                  onPressed: _compareFirst == null ||
                          _compareSecond == null ||
                          _compareFirst == _compareSecond ||
                          _loading
                      ? null
                      : _load,
                  child: const Text('Compare'),
                ),
              ),
              if (_comparison.isNotEmpty)
                ..._comparison.map(
                  (row) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text('${row['department'] ?? ''}'),
                    subtitle: Text(
                      'Remaining ${_money(row['remaining_budget'])} · ${row['transactions'] ?? 0} transactions',
                    ),
                    trailing: Text(
                      _money(row['actual_expenditure']),
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
              if (_compareFirst != null &&
                  _compareSecond != null &&
                  _compareFirst == _compareSecond)
                const Text(
                  'Choose two different departments.',
                  style: TextStyle(color: Colors.deepOrange),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class AnomaliesScreen extends StatefulWidget {
  const AnomaliesScreen({super.key});
  @override
  State<AnomaliesScreen> createState() => _AnomaliesScreenState();
}

class _AnomaliesScreenState extends State<AnomaliesScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      _data = await ApiClient.instance.getMap('/anomaly/detect');
    } catch (error) {
      _error = ApiClient.errorMessage(error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final results = _maps(_data?['results']);
    final risky = _maps(_data?['high_risk_departments']);
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        Text(
          'Anomaly detection',
          style: Theme.of(context)
              .textTheme
              .headlineSmall
              ?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 8),
        const Text(
          'Scan your financial records for unusual spending patterns.',
          style: TextStyle(color: _muted),
        ),
        const SizedBox(height: 16),
        if (_error != null) InlineError(message: _error!, onRetry: _load),
        if (_loading) const LinearProgressIndicator(),
        if (_data != null) ...[
          Row(
            children: [
              Expanded(
                child: MetricCard(
                  label: 'Records analyzed',
                  value: '${_data!['total_records_analyzed'] ?? 0}',
                  icon: Icons.fact_check_outlined,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: MetricCard(
                  label: 'Anomalies found',
                  value: '${_data!['anomalies_found'] ?? 0}',
                  icon: Icons.warning_amber_outlined,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          SectionCard(
            title: 'Highest-risk departments',
            child: risky.isEmpty
                ? const EmptyView(message: 'No high-risk departments found.')
                : Column(
                    children: risky
                        .map(
                          (row) => ListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text('${row['department'] ?? ''}'),
                            subtitle: Text(
                              '${row['anomalies_count'] ?? 0} anomalous records',
                            ),
                            trailing: Text(
                              '${_number(row['avg_risk_score']).toStringAsFixed(1)} risk',
                            ),
                          ),
                        )
                        .toList(),
                  ),
          ),
          const SizedBox(height: 14),
          SectionCard(
            title: 'Flagged records',
            child: results.isEmpty
                ? const EmptyView(message: 'No records available for review.')
                : Column(
                    children: results
                        .take(40)
                        .map(
                          (row) => ListTile(
                            contentPadding: EdgeInsets.zero,
                            leading: Icon(
                              row['is_anomaly'] == true
                                  ? Icons.error_outline
                                  : Icons.check_circle_outline,
                              color: row['is_anomaly'] == true
                                  ? Colors.deepOrange
                                  : _green,
                            ),
                            title: Text(
                              '${row['department']} · ${row['quarter']}',
                            ),
                            subtitle: Text(
                              '${row['financial_year']} · ${row['reason'] ?? 'No explanation'}',
                            ),
                            trailing: Text(
                              _number(row['risk_score']).toStringAsFixed(0),
                            ),
                          ),
                        )
                        .toList(),
                  ),
          ),
        ],
      ],
    );
  }
}

class ForecastScreen extends StatefulWidget {
  const ForecastScreen({super.key});
  @override
  State<ForecastScreen> createState() => _ForecastScreenState();
}

class _ForecastScreenState extends State<ForecastScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      _data = await ApiClient.instance.getMap('/forecast');
    } catch (error) {
      _error = ApiClient.errorMessage(error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final forecasts = _maps(_data?['forecast']);
    final trend = _maps(_data?['annual_trend']);
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        Text(
          'Expenditure forecast',
          style: Theme.of(context)
              .textTheme
              .headlineSmall
              ?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 8),
        const Text(
          'Projected spending based on the available financial history.',
          style: TextStyle(color: _muted),
        ),
        const SizedBox(height: 16),
        if (_error != null) InlineError(message: _error!, onRetry: _load),
        if (_loading) const LinearProgressIndicator(),
        SectionCard(
          title: 'Next-period estimates',
          child: forecasts.isEmpty
              ? const EmptyView(
                  message: 'Upload financial records to generate forecasts.',
                )
              : Column(
                  children: forecasts
                      .map(
                        (row) => ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text('${row['department'] ?? 'Department'}'),
                          subtitle: Text(
                            '${row['period_label'] ?? ''} · ${row['engine'] ?? 'forecast'}',
                          ),
                          trailing: Text(
                            _money(row['predicted_expenditure']),
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                        ),
                      )
                      .toList(),
                ),
        ),
        const SizedBox(height: 14),
        SectionCard(
          title: 'Annual history',
          child: trend.isEmpty
              ? const EmptyView(message: 'No annual trend data is available.')
              : Column(
                  children: trend
                      .map(
                        (row) => ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text('${row['financial_year'] ?? ''}'),
                          subtitle: Text(
                            'Budget ${_money(row['total_budget'])}',
                          ),
                          trailing: Text(_money(row['total_expenditure'])),
                        ),
                      )
                      .toList(),
                ),
        ),
      ],
    );
  }
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<Map<String, dynamic>> _messages = [];
  bool _loading = false;

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _send([String? suggestion]) async {
    final question = (suggestion ?? _input.text).trim();
    if (question.isEmpty || _loading) return;
    setState(() {
      _messages.add({'role': 'user', 'content': question});
      _loading = true;
      _input.clear();
    });
    try {
      final response = await ApiClient.instance.postMap(
        '/rag/chat',
        data: {'question': question},
      );
      if (mounted) {
        setState(
          () => _messages.add({
            'role': 'assistant',
            'content': response['answer'] ?? 'No answer was returned.',
            'mode': response['generation_mode'],
            'sources': response['sources'],
          }),
        );
      }
    } catch (error) {
      if (mounted) {
        setState(
          () => _messages.add({
            'role': 'assistant',
            'content':
                'Unable to get an answer: ${ApiClient.errorMessage(error)}',
          }),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (_scroll.hasClients) {
            _scroll.animateTo(
              _scroll.position.maxScrollExtent,
              duration: const Duration(milliseconds: 250),
              curve: Curves.easeOut,
            );
          }
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    const suggestions = [
      'Which department overspent in Q2?',
      'Compare spending by department',
      'Summarize the financial report',
    ];
    return Column(
      children: [
        Expanded(
          child: _messages.isEmpty
              ? ListView(
                  padding: const EdgeInsets.all(20),
                  children: [
                    Text(
                      'Financial assistant',
                      style: Theme.of(context)
                          .textTheme
                          .headlineSmall
                          ?.copyWith(fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Ask questions about your uploaded financial data and audit reports.',
                      style: TextStyle(color: _muted),
                    ),
                    const SizedBox(height: 22),
                    ...suggestions.map(
                      (q) => Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: OutlinedButton.icon(
                          onPressed: () => _send(q),
                          icon: const Icon(Icons.auto_awesome_outlined),
                          label: Text(q),
                        ),
                      ),
                    ),
                  ],
                )
              : ListView.builder(
                  controller: _scroll,
                  padding: const EdgeInsets.all(16),
                  itemCount: _messages.length + (_loading ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (index >= _messages.length) {
                      return const Align(
                        alignment: Alignment.centerLeft,
                        child: Padding(
                          padding: EdgeInsets.all(12),
                          child: CircularProgressIndicator(),
                        ),
                      );
                    }
                    final message = _messages[index];
                    final user = message['role'] == 'user';
                    return Align(
                      alignment:
                          user ? Alignment.centerRight : Alignment.centerLeft,
                      child: Container(
                        constraints: const BoxConstraints(maxWidth: 680),
                        margin: const EdgeInsets.only(bottom: 12),
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: user ? const Color(0xFFD7F0EA) : Colors.white,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: const Color(0xFFE3EBEA)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('${message['content'] ?? ''}'),
                            if (!user && message['mode'] == 'extractive')
                              const Padding(
                                padding: EdgeInsets.only(top: 8),
                                child: Text(
                                  'Extractive answer from uploaded data.',
                                  style: TextStyle(color: _muted, fontSize: 11),
                                ),
                              ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _input,
                    minLines: 1,
                    maxLines: 4,
                    onSubmitted: (_) => _send(),
                    decoration: const InputDecoration(
                      hintText: 'Ask about college finances…',
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  onPressed: _loading ? null : () => _send(),
                  icon: const Icon(Icons.send),
                  style: IconButton.styleFrom(backgroundColor: _green),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({required this.user, super.key});
  final Map<String, dynamic> user;
  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  List<Map<String, dynamic>> _reports = [];
  bool _loading = true;
  bool _busy = false;
  String? _error;

  bool get _canUpload =>
      widget.user['role'] == 'admin' || widget.user['role'] == 'accounts_staff';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      _reports = _maps(await ApiClient.instance.getList('/reports/mine'));
    } catch (error) {
      _error = ApiClient.errorMessage(error);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _pickAndUpload({required bool pdf}) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: pdf ? ['pdf'] : ['csv', 'xlsx', 'xls'],
      withData: true,
    );
    if (!mounted) return;
    if (result == null || result.files.isEmpty) return;
    final file = result.files.single;
    final bytes = file.bytes;
    if (bytes == null || bytes.isEmpty) {
      _message(context, 'Could not read the selected file.', error: true);
      return;
    }
    setState(() => _busy = true);
    try {
      final result = await ApiClient.instance.uploadFile(
        filename: file.name,
        bytes: bytes,
        isPdf: pdf,
        reportName: pdf
            ? file.name.replaceFirst(
                RegExp(r'\.pdf$', caseSensitive: false),
                '',
              )
            : null,
      );
      if (!mounted) return;
      final report = result['report'];
      _message(
        context,
        pdf
            ? 'Audit PDF uploaded successfully.'
            : 'Dataset uploaded${report is Map ? ' (${report['row_count']} rows)' : ''}.',
      );
      await _load();
    } catch (error) {
      if (mounted) {
        _message(context, ApiClient.errorMessage(error), error: true);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _delete(Map<String, dynamic> report) async {
    final id = report['id'];
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete report?'),
        content: Text(
          'Delete "${report['report_name']}" and its associated data?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (!mounted) return;
    if (confirmed != true) return;
    try {
      await ApiClient.instance.delete('/reports/$id');
    } catch (error) {
      if (mounted) {
        _message(context, ApiClient.errorMessage(error), error: true);
      }
      return;
    }
    if (mounted) _message(context, 'Report deleted.');
    await _load();
  }

  Future<void> _generateReport(String format) async {
    setState(() => _busy = true);
    try {
      final bytes = await ApiClient.instance.generateReport(
        reportType: 'summary',
        format: format,
      );
      await FileSaver.instance.saveFile(
        name: 'college_financial_summary',
        bytes: bytes,
        ext: format == 'excel' ? 'xlsx' : 'pdf',
      );
      if (!mounted) return;
      if (mounted) _message(context, 'Report generated and saved.');
    } catch (error) {
      if (mounted) {
        _message(context, ApiClient.errorMessage(error), error: true);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(18),
      children: [
        Text(
          'Reports & uploads',
          style: Theme.of(context)
              .textTheme
              .headlineSmall
              ?.copyWith(fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 8),
        const Text(
          'Manage uploaded datasets and export financial summaries.',
          style: TextStyle(color: _muted),
        ),
        const SizedBox(height: 16),
        if (_canUpload)
          SectionCard(
            title: 'Upload data',
            child: Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                OutlinedButton.icon(
                  onPressed: _busy ? null : () => _pickAndUpload(pdf: false),
                  icon: const Icon(Icons.table_view_outlined),
                  label: const Text('CSV / Excel'),
                ),
                OutlinedButton.icon(
                  onPressed: _busy ? null : () => _pickAndUpload(pdf: true),
                  icon: const Icon(Icons.picture_as_pdf_outlined),
                  label: const Text('Audit PDF'),
                ),
              ],
            ),
          ),
        if (_busy) const LinearProgressIndicator(),
        const SizedBox(height: 12),
        SectionCard(
          title: 'Generate summary',
          child: Wrap(
            spacing: 10,
            children: [
              FilledButton.tonalIcon(
                onPressed: _busy ? null : () => _generateReport('pdf'),
                icon: const Icon(Icons.picture_as_pdf),
                label: const Text('PDF'),
              ),
              FilledButton.tonalIcon(
                onPressed: _busy ? null : () => _generateReport('excel'),
                icon: const Icon(Icons.table_chart_outlined),
                label: const Text('Excel'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        if (_error != null) InlineError(message: _error!, onRetry: _load),
        SectionCard(
          title: 'Your reports',
          trailing: IconButton(
            onPressed: _load,
            icon: const Icon(Icons.refresh),
          ),
          child: _loading
              ? const Center(
                  child: Padding(
                    padding: EdgeInsets.all(18),
                    child: CircularProgressIndicator(),
                  ),
                )
              : _reports.isEmpty
                  ? const EmptyView(
                      message: 'No reports have been uploaded yet.')
                  : Column(
                      children: _reports
                          .map(
                            (report) => ListTile(
                              contentPadding: EdgeInsets.zero,
                              leading: Icon(
                                '${report['report_type']}'
                                        .toLowerCase()
                                        .contains(
                                          'pdf',
                                        )
                                    ? Icons.picture_as_pdf_outlined
                                    : Icons.dataset_outlined,
                                color: _green,
                              ),
                              title: Text(
                                '${report['report_name'] ?? 'Untitled report'}',
                              ),
                              subtitle: Text(
                                '${report['report_type'] ?? 'data'} · ${report['row_count'] ?? 0} rows · ${report['status'] ?? ''}',
                              ),
                              trailing: _canUpload
                                  ? IconButton(
                                      tooltip: 'Delete report',
                                      onPressed: () => _delete(report),
                                      icon: const Icon(
                                        Icons.delete_outline,
                                        color: Colors.redAccent,
                                      ),
                                    )
                                  : null,
                            ),
                          )
                          .toList(),
                    ),
        ),
      ],
    );
  }
}

class LoadingView extends StatelessWidget {
  const LoadingView({super.key});
  @override
  Widget build(BuildContext context) => const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: CircularProgressIndicator(),
        ),
      );
}

class EmptyView extends StatelessWidget {
  const EmptyView({required this.message, super.key});
  final String message;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 18),
        child: Center(
          child: Text(
            message,
            textAlign: TextAlign.center,
            style: const TextStyle(color: _muted),
          ),
        ),
      );
}

class ErrorView extends StatelessWidget {
  const ErrorView({required this.message, required this.onRetry, super.key});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.cloud_off_outlined,
                size: 42,
                color: Colors.deepOrange,
              ),
              const SizedBox(height: 12),
              Text(message, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
}

class InlineError extends StatelessWidget {
  const InlineError({required this.message, required this.onRetry, super.key});
  final String message;
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) => Card(
        color: const Color(0xFFFFF3F0),
        child: ListTile(
          leading: const Icon(Icons.error_outline, color: Colors.deepOrange),
          title: Text(message, style: const TextStyle(fontSize: 13)),
          trailing:
              IconButton(onPressed: onRetry, icon: const Icon(Icons.refresh)),
        ),
      );
}

class MetricCard extends StatelessWidget {
  const MetricCard({
    required this.label,
    required this.value,
    required this.icon,
    super.key,
  });
  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Icon(icon, color: _green),
              const SizedBox(height: 10),
              FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: Text(
                  value,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    fontSize: 19,
                    color: _ink,
                  ),
                ),
              ),
              Text(label, style: const TextStyle(color: _muted, fontSize: 12)),
            ],
          ),
        ),
      );
}

class SectionCard extends StatelessWidget {
  const SectionCard({
    required this.title,
    required this.child,
    this.trailing,
    super.key,
  });
  final String title;
  final Widget child;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w800,
                        color: _ink,
                      ),
                    ),
                  ),
                  if (trailing != null) trailing!,
                ],
              ),
              const SizedBox(height: 10),
              child,
            ],
          ),
        ),
      );
}
