# Как собрать APK для Payly

## Самый надёжный порядок

### 1. Перейдите в папку mobile
```bash
cd mobile
```

### 2. Установите зависимости
```bash
npm install
```

### 3. Проверьте совместимость Expo-зависимостей
```bash
npx expo install --fix
npx expo-doctor@latest
```

### 4. Локальный запуск в Android Emulator
```bash
npx expo start
```

Затем нажмите `a` в терминале.

## Сборка APK через EAS Build

### 1. Установить EAS CLI
```bash
npm install -g eas-cli
```

### 2. Войти в Expo
```bash
eas login
```

### 3. Собрать preview APK
```bash
eas build --platform android --profile preview
```

## Важно

- приложение уже настроено на `http://10.0.2.2:8000` для Android Emulator;
- в Android build включён `usesCleartextTraffic`, чтобы локальный backend по HTTP открывался в APK;
- если backend не нужен, можно сразу открыть демо-режим внутри приложения.
