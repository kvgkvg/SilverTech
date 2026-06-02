class AccessibilityAudit {
  bool passes({required double fontSize, required double touchTarget}) {
    return fontSize >= 24 && touchTarget >= 56;
  }
}
