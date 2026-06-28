NoFuS-TX Mobile App (Flutter)

Die Mobile-App liegt in folgendem Ordner:
APP/nofus_tx_mobile

Schnellstart
1. In den App-Ordner wechseln.
	cd APP/nofus_tx_mobile
2. Abhaengigkeiten laden.
	flutter pub get
3. Analyse ausfuehren.
	flutter analyze
4. App starten (Debug).
	flutter run

Android Release
1. APK bauen:
	flutter build apk --release
	Ausgabe: build/app/outputs/flutter-apk/app-release.apk
2. App Bundle bauen (Play Store):
	flutter build appbundle --release
	Ausgabe: build/app/outputs/bundle/release/app-release.aab

iOS Release (nur auf macOS mit Xcode)
1. Build erzeugen:
	flutter build ios --release
2. Danach Signierung/Archivierung in Xcode abschliessen.

Versionierung
Die Versionsnummer wird in pubspec.yaml gepflegt.
Beispiel:
version: 1.02.1+1

Release-Checkliste
1. flutter clean
2. flutter pub get
3. flutter analyze
4. Optional Tests:
	flutter test
5. Release-Build erzeugen

Hinweis zur Repo-Struktur
Dieses Hauptrepo enthaelt die Desktop/Python-Hauptanwendung und die Mobile-App gemeinsam.
Die Mobile-App wird innerhalb von APP/nofus_tx_mobile weiterentwickelt.
