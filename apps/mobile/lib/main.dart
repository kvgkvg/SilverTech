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
          children: <Widget>[
            const Text(
              'Huong camera vao bang dieu khien.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 24),
            const Text(
              'Neu hinh anh chua ro, ung dung se yeu cau quet lai thay vi doan nut.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 24),
            ),
            const SizedBox(height: 32),
            SizedBox(
              height: 64,
              child: FilledButton(
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const CameraScanScreen(),
                    ),
                  );
                },
                child: const Text('Mo camera'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class CameraScanScreen extends StatelessWidget {
  const CameraScanScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Quet bang dieu khien')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Expanded(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: const Color(0xFFF4F8F5),
                  border: Border.all(color: colorScheme.primary, width: 4),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Center(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text(
                      'Dat bang dieu khien vao khung hinh',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 30,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 20),
            const Text(
              'Khi do tin cay thap, SilverTech se yeu cau quet lai va khong hien nut.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 22),
            ),
            const SizedBox(height: 20),
            SizedBox(
              height: 64,
              child: FilledButton(
                onPressed: () {},
                child: const Text('Quet lai'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
