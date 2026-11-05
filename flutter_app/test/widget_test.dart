import 'package:college_financial_app/screens.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('login screen exposes sign-in and server configuration', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(home: LoginScreen(onAuthenticated: (_) {})),
    );

    expect(find.text('Welcome back'), findsOneWidget);
    expect(find.text('Sign in'), findsOneWidget);
    expect(find.text('Configure server'), findsOneWidget);

    await tester.tap(find.text('Configure server'));
    await tester.pumpAndSettle();

    expect(find.text('Backend server URL'), findsOneWidget);
  });
}
