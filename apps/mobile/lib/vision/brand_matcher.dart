class BrandMatch {
  const BrandMatch({required this.brand, required this.confidence});
  final String brand;
  final double confidence;
}

class BrandMatcher {
  BrandMatch? matchFromManualSelection(String? brand) {
    if (brand == null || brand.isEmpty) return null;
    return BrandMatch(brand: brand, confidence: 1.0);
  }
}
