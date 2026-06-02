import 'package:flutter/material.dart';

void main() {
  runApp(const SilverTechApp());
}

class SilverTechApp extends StatelessWidget {
  const SilverTechApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SilverTech',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0B6E4F)),
        scaffoldBackgroundColor: Colors.white,
        textTheme: const TextTheme(
          headlineMedium: TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
          bodyLarge: TextStyle(fontSize: 24),
          labelLarge: TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
        ),
      ),
      home: const CameraEntryScreen(),
    );
  }
}

class CameraEntryScreen extends StatelessWidget {
  const CameraEntryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('SilverTech')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: const <Widget>[
            Text(
              'Huong camera vao bang dieu khien.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
            ),
            SizedBox(height: 24),
            Text(
              'Neu hinh anh chua ro, ung dung se yeu cau quet lai thay vi doan nut.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 24),
            ),
            SizedBox(height: 32),
            SizedBox(
              height: 64,
              child: FilledButton(
                onPressed: null,
                child: Text('Mo camera'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
