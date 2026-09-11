import 'package:flutter/material.dart';

/// Meme palette que le site web (data/style.css :root) pour une identite coherente.
class RTColors {
  static const bg = Color(0xFF0A0806);
  static const bgSoft = Color(0xFF17130A);
  static const gold = Color(0xFFD4AF37);
  static const goldSoft = Color(0xFFF0D78C);
  static const text = Color(0xFFF0EAD8);
  static const textDim = Color(0xFFB8AC8E);
  static const border = Color(0x59D4AF37);
  static const error = Color(0xFFE5726A);
}

ThemeData buildRituamsTheme() {
  return ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: RTColors.bg,
    colorScheme: const ColorScheme.dark(
      primary: RTColors.gold,
      secondary: RTColors.goldSoft,
      surface: RTColors.bgSoft,
      error: RTColors.error,
    ),
    fontFamily: 'Georgia',
    appBarTheme: const AppBarTheme(
      backgroundColor: RTColors.bg,
      foregroundColor: RTColors.goldSoft,
      elevation: 0,
      centerTitle: true,
    ),
    textTheme: const TextTheme(
      bodyMedium: TextStyle(color: RTColors.text),
      bodyLarge: TextStyle(color: RTColors.text),
      titleLarge: TextStyle(color: RTColors.goldSoft),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: RTColors.bgSoft,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: RTColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: RTColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: RTColors.gold),
      ),
      hintStyle: const TextStyle(color: RTColors.textDim),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: RTColors.gold,
        foregroundColor: RTColors.bg,
        padding: const EdgeInsets.symmetric(vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        textStyle: const TextStyle(fontWeight: FontWeight.bold),
      ),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: RTColors.bgSoft,
      selectedItemColor: RTColors.gold,
      unselectedItemColor: RTColors.textDim,
    ),
    cardTheme: CardThemeData(
      color: RTColors.bgSoft,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
        side: const BorderSide(color: RTColors.border),
      ),
    ),
  );
}
