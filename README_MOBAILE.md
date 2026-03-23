

## Мобильная часть

-  `mobile/App.js`, чтобы приложение не падало при недоступном backend;
- добавлен локальный демо-режим без сервера;
- добавлены таймауты и понятные ошибки сети;
- ручное добавление и удаление подписок работает даже без backend в демо-режиме;
- добавлен UI-индикатор состояния backend / demo mode;
- добавлен Error Boundary, чтобы UI-ошибка не закрывала приложение полностью.

## Конфиг Android / Expo

- в `mobile/app.json` отключена New Architecture (`newArchEnabled: false`) для более стабильного старта на Expo SDK 53;
- добавлен `expo-build-properties` с `usesCleartextTraffic: true`, чтобы APK мог обращаться к локальному `http://10.0.2.2:8000`;
- `extra.defaultApiBaseUrl` выставлен в `http://10.0.2.2:8000`.

## Зависимости

- обновлён `@react-native-async-storage/async-storage`;
- добавлен `expo-build-properties`;
- добавлены команды `doctor` и `fix-deps`.

## Документация

- обновлены `README_MOBILE.md` и `BUILD_APK_RU.md`.

Чтобы получить APK, откройте папку `mobile` и выполните:

```bash
npm install
npx expo install --fix
npx expo-doctor@latest
npx expo start
```

или

```bash
eas build --platform android --profile preview
```
