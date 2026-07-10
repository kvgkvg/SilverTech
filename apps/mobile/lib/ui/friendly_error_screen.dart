class FriendlyErrorScreenModel {
  const FriendlyErrorScreenModel({
    required this.titleVi,
    required this.actionVi,
  });
  final String titleVi;
  final String actionVi;

  @override
  String toString() {
    return 'FriendlyErrorScreenModel(titleVi: $titleVi, actionVi: $actionVi)';
  }
}
