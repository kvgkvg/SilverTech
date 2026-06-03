import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:silvertech_mobile/main.dart';

void main() {
  testWidgets('shows elderly-first scanning instruction',
      (WidgetTester tester) async {
    await tester.pumpWidget(const SilverTechApp());

    expect(find.text('SilverTech'), findsOneWidget);
    expect(find.text('Huong camera vao bang dieu khien.'), findsOneWidget);
    expect(find.text('Mo camera'), findsOneWidget);

    await tester.tap(find.text('Mo camera'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('Quet bang dieu khien'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });
}
