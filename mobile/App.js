import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  Modal,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { StatusBar as ExpoStatusBar } from "expo-status-bar";
import * as Notifications from "expo-notifications";

const DEFAULT_SERVICES = [
  "Spotify",
  "YouTube",
  "Discord",
  "Telegram",
  "SoundCloud",
  "Яндекс Плюс",
  "Кинопоиск",
  "IVI",
  "Wink",
  "VK Музыка",
  "KION",
  "Boosty",
];

const DEMO_USER = {
  email: "demo@payly.local",
};

const DEMO_SUBSCRIPTIONS = [
  {
    id: 1,
    name: "Spotify Premium",
    price: 299,
    billing_cycle: "monthly",
    next_payment_date: "2026-04-05",
  },
  {
    id: 2,
    name: "YouTube Premium",
    price: 399,
    billing_cycle: "monthly",
    next_payment_date: "2026-04-12",
  },
  {
    id: 3,
    name: "Кинопоиск",
    price: 2990,
    billing_cycle: "yearly",
    next_payment_date: "2026-11-01",
  },
];

const STORAGE_KEYS = {
  token: "payly_mobile_token",
  apiBaseUrl: "payly_mobile_api_base_url",
  localMode: "payly_mobile_local_mode",
  localSubs: "payly_mobile_local_subs",
};
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

const PERIOD_OPTIONS = [
  { key: "30", label: "30 дней", days: 30 },
  { key: "90", label: "3 месяца", days: 90 },
  { key: "365", label: "12 месяцев", days: 365 },
];

function startOfToday() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

function parseDateOnly(value) {
  const d = new Date(`${value}T10:00:00`);
  return Number.isNaN(d.getTime()) ? null : d;
}

function daysUntil(dateString) {
  const today = startOfToday();
  const target = new Date(`${dateString}T00:00:00`);
  if (Number.isNaN(target.getTime())) return 9999;
  target.setHours(0, 0, 0, 0);
  return Math.round((target - today) / 86400000);
}

function getOccurrencesInPeriod(sub, days) {
  const result = [];
  const today = startOfToday();
  const end = new Date(today);
  end.setDate(end.getDate() + days);

  let current = parseDateOnly(sub.next_payment_date);
  if (!current) return result;

  let guard = 0;
  while (current <= end && guard < 100) {
    if (current >= today) {
      result.push({
        name: sub.name,
        price: Number(sub.price || 0),
        date: current.toISOString().slice(0, 10),
        billing_cycle: sub.billing_cycle,
      });
    }

    const next = new Date(current);
    if (sub.billing_cycle === "yearly") {
      next.setFullYear(next.getFullYear() + 1);
    } else {
      next.setMonth(next.getMonth() + 1);
    }
    current = next;
    guard += 1;
  }

  return result;
}

function buildAnalyticsRows(subscriptions, days) {
  const totals = {};

  subscriptions.forEach((sub) => {
    const rows = getOccurrencesInPeriod(sub, days);
    rows.forEach((row) => {
      totals[row.name] = (totals[row.name] || 0) + row.price;
    });
  });

  return Object.entries(totals)
    .map(([name, total]) => ({ name, total }))
    .sort((a, b) => b.total - a.total);
}

function AnalyticsBar({ label, value, maxValue }) {
  const width = Math.max(8, Math.round((value / Math.max(maxValue, 1)) * 100));

  return (
    <View style={styles.analyticsRow}>
      <View style={styles.analyticsTextWrap}>
        <Text style={styles.analyticsLabel}>{label}</Text>
        <Text style={styles.analyticsValue}>{formatMoney(value)}</Text>
      </View>
      <View style={styles.analyticsTrack}>
        <View style={[styles.analyticsFill, { width: `${width}%` }]} />
      </View>
    </View>
  );
}

function guessDefaultApiBaseUrl() {
  if (process.env.EXPO_PUBLIC_API_BASE_URL) {
    return process.env.EXPO_PUBLIC_API_BASE_URL;
  }
  if (Platform.OS === "android") {
    return "http://10.0.2.2:8000";
  }
  return "http://127.0.0.1:8000";
}

function formatMoney(value) {
  const num = Number(value || 0);
  return `${num.toFixed(2)} ₽`;
}

function formatCycle(value) {
  return value === "yearly" ? "В год" : "В месяц";
}

function nextMonthDate() {
  const d = new Date();
  d.setMonth(d.getMonth() + 1);
  return d.toISOString().slice(0, 10);
}

function isValidDateString(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(String(value || ""));
}

function normalizeApiBaseUrl(value) {
  return String(value || "").trim().replace(/\/$/, "");
}

function normalizeSubscription(item, index = 0) {
  return {
    id: Number(item?.id) || Date.now() + index,
    name: String(item?.name || "Без названия"),
    price: Number(item?.price || 0),
    billing_cycle: item?.billing_cycle === "yearly" ? "yearly" : "monthly",
    next_payment_date: String(item?.next_payment_date || nextMonthDate()),
  };
}

async function safeGetItem(key) {
  try {
    return await AsyncStorage.getItem(key);
  } catch (error) {
    console.log("AsyncStorage get error", key, error);
    return null;
  }
}

async function safeSetItem(key, value) {
  try {
    await AsyncStorage.setItem(key, value);
  } catch (error) {
    console.log("AsyncStorage set error", key, error);
  }
}

async function safeRemoveItem(key) {
  try {
    await AsyncStorage.removeItem(key);
  } catch (error) {
    console.log("AsyncStorage remove error", key, error);
  }
}

async function loadLocalSubscriptions() {
  const raw = await safeGetItem(STORAGE_KEYS.localSubs);
  if (!raw) return DEMO_SUBSCRIPTIONS;
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return DEMO_SUBSCRIPTIONS;
    return parsed.map(normalizeSubscription);
  } catch (error) {
    console.log("Local subscriptions parse error", error);
    return DEMO_SUBSCRIPTIONS;
  }
}

async function persistLocalSubscriptions(items) {
  await safeSetItem(
    STORAGE_KEYS.localSubs,
    JSON.stringify((items || []).map((item, index) => normalizeSubscription(item, index))),
  );
}

async function apiFetch(apiBaseUrl, path, { method = "GET", body, token, timeoutMs = 12000 } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${apiBaseUrl}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    const contentType = res.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");
    const data = isJson ? await res.json().catch(() => null) : null;

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      if (data?.detail) {
        if (typeof data.detail === "string") {
          detail = data.detail;
        } else if (Array.isArray(data.detail)) {
          detail = data.detail.map((item) => item?.msg || item?.type || "Ошибка").join(", ");
        }
      }
      const err = new Error(detail);
      err.status = res.status;
      err.data = data;
      throw err;
    }

    return data;
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error("Сервер не ответил вовремя. Проверьте backend и адрес API.");
    }
    if (
      String(error?.message || "").includes("Network request failed") ||
      String(error?.message || "").includes("Failed to fetch")
    ) {
      throw new Error("Нет соединения с backend. Проверьте, что сервер запущен и URL указан правильно.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

function StatCard({ title, value, accent }) {
  return (
    <View style={[styles.statCard, accent && { borderColor: accent }]}> 
      <Text style={styles.statTitle}>{title}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

function ServiceChip({ label, active, onPress }) {
  return (
    <Pressable onPress={onPress} style={[styles.serviceChip, active && styles.serviceChipActive]}>
      <Text style={[styles.serviceChipText, active && styles.serviceChipTextActive]}>{label}</Text>
    </Pressable>
  );
}

function PrimaryButton({ title, onPress, disabled, secondary, danger }) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={[
        styles.primaryButton,
        secondary && styles.secondaryButton,
        danger && styles.dangerButton,
        disabled && styles.buttonDisabled,
      ]}
    >
      <Text style={styles.primaryButtonText}>{title}</Text>
    </Pressable>
  );
}

function Field({
  label,
  value,
  onChangeText,
  placeholder,
  secureTextEntry,
  keyboardType,
  autoCapitalize = "none",
}) {
  return (
    <View style={styles.fieldWrap}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor="#94a3b8"
        secureTextEntry={secureTextEntry}
        keyboardType={keyboardType}
        autoCapitalize={autoCapitalize}
        autoCorrect={false}
        style={styles.input}
      />
    </View>
  );
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: "" };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      errorMessage: error?.message || "Неизвестная ошибка",
    };
  }

  componentDidCatch(error) {
    console.log("App render crash", error);
  }

  handleReset = () => {
    this.setState({ hasError: false, errorMessage: "" });
  };

  render() {
    if (this.state.hasError) {
      return (
        <SafeAreaView style={styles.loadingScreen}>
          <ExpoStatusBar style="light" />
          <Text style={styles.heroTitle}>Payly восстановлен</Text>
          <Text style={[styles.helperText, { textAlign: "center", maxWidth: 320 }]}>
            Приложение перехватило ошибку интерфейса и не закрылось. Нажмите кнопку ниже, чтобы перерисовать экран.
          </Text>
          <Text style={[styles.subMeta, { textAlign: "center", marginTop: 8 }]}>{this.state.errorMessage}</Text>
          <View style={{ width: "100%", maxWidth: 320, marginTop: 18 }}>
            <PrimaryButton title="Попробовать снова" onPress={this.handleReset} />
          </View>
        </SafeAreaView>
      );
    }

    return this.props.children;
  }
}

function AppContent() {
  const [apiBaseUrl, setApiBaseUrl] = useState(guessDefaultApiBaseUrl());
  const [apiBaseUrlDraft, setApiBaseUrlDraft] = useState(guessDefaultApiBaseUrl());
  const [token, setToken] = useState("");
  const [user, setUser] = useState(null);
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState("login");
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [filterService, setFilterService] = useState("Все");
  const [selectedProvider, setSelectedProvider] = useState("gmail");
  const [candidates, setCandidates] = useState([]);
  const [selectedKeys, setSelectedKeys] = useState({});
  const [analyticsPeriod, setAnalyticsPeriod] = useState("30");
  const [usingLocalMode, setUsingLocalMode] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("Проверяем backend…");
  const [backendReachable, setBackendReachable] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [subName, setSubName] = useState("Spotify Premium");
  const [subPrice, setSubPrice] = useState("299");
  const [subCycle, setSubCycle] = useState("monthly");
  const [subDate, setSubDate] = useState(nextMonthDate());

  useEffect(() => {
    bootstrap();
  }, []);
  useEffect(() => {
  registerNotificationPermissions();
}, []);

useEffect(() => {
  if (user && subscriptions.length) {
    scheduleUpcomingNotifications();
  }
}, [user, subscriptions]);

  async function pingBackend(baseUrl) {
    try {
      await apiFetch(baseUrl, "/", { timeoutMs: 4000 });
      setBackendReachable(true);
      setConnectionStatus("Backend доступен");
      return true;
    } catch (error) {
      setBackendReachable(false);
      setConnectionStatus("Backend недоступен — можно включить демо-режим");
      return false;
    }
  }

  async function bootstrap() {
    try {
      const [storedToken, storedApi, storedLocalMode] = await Promise.all([
        safeGetItem(STORAGE_KEYS.token),
        safeGetItem(STORAGE_KEYS.apiBaseUrl),
        safeGetItem(STORAGE_KEYS.localMode),
      ]);

      const base = normalizeApiBaseUrl(storedApi || guessDefaultApiBaseUrl()) || guessDefaultApiBaseUrl();
      setApiBaseUrl(base);
      setApiBaseUrlDraft(base);

      const localModeEnabled = storedLocalMode === "1";
      if (localModeEnabled) {
        const localSubs = await loadLocalSubscriptions();
        setUsingLocalMode(true);
        setUser(DEMO_USER);
        setSubscriptions(localSubs);
        setConnectionStatus("Запущен демо-режим без backend");
        return;
      }

      await pingBackend(base);

      if (storedToken) {
        setToken(storedToken);
        const me = await apiFetch(base, "/me", { token: storedToken, timeoutMs: 7000 });
        const items = await apiFetch(base, "/subscriptions/", { token: storedToken, timeoutMs: 7000 });
        setUser(me);
        setSubscriptions((items || []).map(normalizeSubscription));
        setConnectionStatus("Подключено к backend");
        setBackendReachable(true);
      }
    } catch (error) {
      console.log("Bootstrap error", error);
      await safeRemoveItem(STORAGE_KEYS.token);
      setToken("");
      setUser(null);
      setSubscriptions([]);
      setConnectionStatus("Backend не отвечает. Можно работать в демо-режиме.");
      setBackendReachable(false);
    } finally {
      setLoading(false);
    }
  }

  async function enableLocalMode() {
    const localSubs = await loadLocalSubscriptions();
    setUsingLocalMode(true);
    setUser(DEMO_USER);
    setSubscriptions(localSubs);
    setToken("");
    await safeRemoveItem(STORAGE_KEYS.token);
    await safeSetItem(STORAGE_KEYS.localMode, "1");
    await persistLocalSubscriptions(localSubs);
    setConnectionStatus("Запущен демо-режим без backend");
  }

  async function disableLocalMode() {
    setUsingLocalMode(false);
    setUser(null);
    setSubscriptions([]);
    setCandidates([]);
    setSelectedKeys({});
    await safeSetItem(STORAGE_KEYS.localMode, "0");
    await pingBackend(apiBaseUrl);
  }

  async function saveApiBase() {
    const normalized = normalizeApiBaseUrl(apiBaseUrlDraft);
    if (!normalized.startsWith("http://") && !normalized.startsWith("https://")) {
      Alert.alert("Неверный адрес", "Укажите полный URL, например http://10.0.2.2:8000");
      return;
    }
    setApiBaseUrl(normalized);
    await safeSetItem(STORAGE_KEYS.apiBaseUrl, normalized);
    const ok = await pingBackend(normalized);
    Alert.alert(
      ok ? "Сохранено" : "URL сохранён",
      ok ? "Backend ответил успешно." : "Адрес сохранён, но backend пока не отвечает.",
    );
  }

  async function handleRegister() {
    if (usingLocalMode) {
      Alert.alert("Демо-режим", "В демо-режиме регистрация не нужна. Просто пользуйтесь приложением.");
      return;
    }
    if (!email || !password) {
      Alert.alert("Заполните поля", "Введите email и пароль.");
      return;
    }
    setBusy(true);
    try {
      await apiFetch(apiBaseUrl, "/register", {
        method: "POST",
        body: { email, password },
      });
      await handleLogin(true);
    } catch (error) {
      Alert.alert("Ошибка регистрации", error.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleLogin(silent = false) {
    if (usingLocalMode) {
      if (!silent) {
        Alert.alert("Демо-режим", "Сейчас открыт локальный режим без backend. Чтобы войти в аккаунт, выключите демо-режим.");
      }
      return;
    }
    if (!email || !password) {
      if (!silent) Alert.alert("Заполните поля", "Введите email и пароль.");
      return;
    }
    setBusy(true);
    try {
      const auth = await apiFetch(apiBaseUrl, "/login", {
        method: "POST",
        body: { email, password },
      });
      const nextToken = auth.access_token;
      await safeSetItem(STORAGE_KEYS.token, nextToken);
      setToken(nextToken);
      const me = await apiFetch(apiBaseUrl, "/me", { token: nextToken });
      const items = await apiFetch(apiBaseUrl, "/subscriptions/", { token: nextToken });
      setUser(me);
      setSubscriptions((items || []).map(normalizeSubscription));
      setConnectionStatus("Подключено к backend");
      setBackendReachable(true);
    } catch (error) {
      if (!silent) Alert.alert("Ошибка входа", error.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleLogout() {
    try {
      if (!usingLocalMode && token) {
        await apiFetch(apiBaseUrl, "/logout", { method: "POST", token });
      }
    } catch (error) {
      console.log(error);
    }

    await safeRemoveItem(STORAGE_KEYS.token);
    setToken("");
    setCandidates([]);
    setSelectedKeys({});

    if (usingLocalMode) {
      setUser(DEMO_USER);
      const localSubs = await loadLocalSubscriptions();
      setSubscriptions(localSubs);
      setConnectionStatus("Запущен демо-режим без backend");
      return;
    }

    setUser(null);
    setSubscriptions([]);
  }

  async function refreshSubs() {
    if (usingLocalMode) {
      const items = await loadLocalSubscriptions();
      setSubscriptions(items);
      setConnectionStatus("Данные обновлены из локального демо-режима");
      return;
    }
    if (!token) return;
    setBusy(true);
    try {
      const items = await apiFetch(apiBaseUrl, "/subscriptions/", { token });
      setSubscriptions((items || []).map(normalizeSubscription));
      setConnectionStatus("Подписки обновлены с backend");
    } catch (error) {
      Alert.alert("Не удалось обновить", error.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateSub() {
    if (!subName || !subPrice || !subDate) {
      Alert.alert("Заполните форму", "Название, цена и дата обязательны.");
      return;
    }

    const parsedPrice = Number(String(subPrice).replace(",", "."));
    if (!Number.isFinite(parsedPrice) || parsedPrice < 0) {
      Alert.alert("Неверная цена", "Введите корректную сумму, например 299.");
      return;
    }
    if (!isValidDateString(subDate)) {
      Alert.alert("Неверная дата", "Используйте формат YYYY-MM-DD, например 2026-04-25.");
      return;
    }

    setBusy(true);
    try {
      if (usingLocalMode) {
        const nextItems = [
          normalizeSubscription(
            {
              id: Date.now(),
              name: subName.trim(),
              price: parsedPrice,
              billing_cycle: subCycle,
              next_payment_date: subDate,
            },
            0,
          ),
          ...subscriptions,
        ];
        setSubscriptions(nextItems);
        await persistLocalSubscriptions(nextItems);
        setShowAddModal(false);
        setConnectionStatus("Подписка сохранена локально");
        return;
      }

      await apiFetch(apiBaseUrl, "/subscriptions/", {
        method: "POST",
        token,
        body: {
          name: subName.trim(),
          price: parsedPrice,
          billing_cycle: subCycle,
          next_payment_date: subDate,
        },
      });
      setShowAddModal(false);
      await refreshSubs();
    } catch (error) {
      Alert.alert("Ошибка создания", error.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteSub(id) {
    setBusy(true);
    try {
      if (usingLocalMode) {
        const nextItems = subscriptions.filter((item) => item.id !== id);
        setSubscriptions(nextItems);
        await persistLocalSubscriptions(nextItems);
        setConnectionStatus("Подписка удалена локально");
        return;
      }

      await apiFetch(apiBaseUrl, `/subscriptions/${id}`, { method: "DELETE", token });
      await refreshSubs();
    } catch (error) {
      Alert.alert("Ошибка удаления", error.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleConnectProvider(provider) {
    if (usingLocalMode) {
      Alert.alert("Демо-режим", "В локальном режиме подключение Gmail и Mail.ru отключено. Сначала выключите демо-режим.");
      return;
    }
    setBusy(true);
    try {
      const data = await apiFetch(apiBaseUrl, `/integrations/${provider}/oauth/start?client=mobile`, {
        method: "POST",
        token,
      });
      const url = data?.authorization_url;
      if (!url) throw new Error("Сервер не вернул authorization_url");
      await Linking.openURL(url);
      Alert.alert(
        "Браузер открыт",
        "После подтверждения доступа вернитесь в приложение и нажмите «Проверить импорт».",
      );
    } catch (error) {
      Alert.alert("Не удалось подключить почту", error.message);
    } finally {
      setBusy(false);
    }
  }

  async function handlePreviewImport(provider) {
    if (usingLocalMode) {
      Alert.alert("Демо-режим", "Импорт из почты работает только при запущенном backend.");
      return;
    }
    setBusy(true);
    try {
      const data = await apiFetch(apiBaseUrl, `/integrations/${provider}/sync-subscriptions/preview`, {
        method: "POST",
        token,
      });
      const items = (data?.candidates || []).map(normalizeSubscription).map((item, index) => ({
        ...item,
        candidate_key: data?.candidates?.[index]?.candidate_key,
      }));
      const selected = {};
      items.forEach((item) => {
        if (item.candidate_key) selected[item.candidate_key] = true;
      });
      setSelectedProvider(provider);
      setCandidates(items);
      setSelectedKeys(selected);
      setShowImportModal(true);
    } catch (error) {
      Alert.alert(
        "Импорт пока недоступен",
        error.message.includes("Provider not connected")
          ? "Сначала подключите Gmail или Mail.ru, затем повторите импорт."
          : error.message,
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleImportSelected() {
    const candidate_keys = Object.keys(selectedKeys).filter((key) => selectedKeys[key]);
    if (!candidate_keys.length) {
      Alert.alert("Ничего не выбрано", "Отметьте хотя бы одну подписку для импорта.");
      return;
    }
    setBusy(true);
    try {
      await apiFetch(apiBaseUrl, `/integrations/${selectedProvider}/sync-subscriptions/import`, {
        method: "POST",
        token,
        body: { candidate_keys },
      });
      setShowImportModal(false);
      await refreshSubs();
      Alert.alert("Готово", "Подписки импортированы из почты.");
    } catch (error) {
      Alert.alert("Ошибка импорта", error.message);
    } finally {
      setBusy(false);
    }
  }
  async function registerNotificationPermissions() {
  try {
    const existing = await Notifications.getPermissionsAsync();
    let status = existing.status;

    if (status !== "granted") {
      const requested = await Notifications.requestPermissionsAsync();
      status = requested.status;
    }

    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("payments", {
        name: "Списания",
        importance: Notifications.AndroidImportance.HIGH,
      });
    }
  } catch (error) {
    console.log("notifications permission error", error);
  }
}

async function scheduleUpcomingNotifications() {
  try {
    await Notifications.cancelAllScheduledNotificationsAsync();

    for (const item of subscriptions) {
      const paymentDate = parseDateOnly(item.next_payment_date);
      if (!paymentDate) continue;

      for (const daysBefore of [3, 2, 1]) {
        const triggerDate = new Date(paymentDate);
        triggerDate.setDate(triggerDate.getDate() - daysBefore);
        triggerDate.setHours(10, 0, 0, 0);

        if (triggerDate <= new Date()) continue;

        await Notifications.scheduleNotificationAsync({
          content: {
            title: `Скоро спишется ${item.name}`,
            body: `Через ${daysBefore} дн. будет списано ${formatMoney(item.price)}`,
            ...(Platform.OS === "android" ? { channelId: "payments" } : {}),
          },
          trigger: triggerDate,
        });
      }
    }
  } catch (error) {
    console.log("schedule notification error", error);
  }
}

async function triggerTestNotification() {
  try {
    await registerNotificationPermissions();
    await Notifications.scheduleNotificationAsync({
      content: {
        title: "Payly: тест уведомления",
        body: "Это демонстрация системного напоминания о списании.",
        ...(Platform.OS === "android" ? { channelId: "payments" } : {}),
      },
      trigger: { seconds: 5 },
    });

    Alert.alert("Готово", "Через 5 секунд придёт тестовое уведомление.");
  } catch (error) {
    Alert.alert("Ошибка уведомления", error.message);
  }
}

const selectedPeriodDays = useMemo(() => {
  return PERIOD_OPTIONS.find((item) => item.key === analyticsPeriod)?.days ?? 30;
}, [analyticsPeriod]);

const analyticsRows = useMemo(() => {
  return buildAnalyticsRows(subscriptions, selectedPeriodDays);
}, [subscriptions, selectedPeriodDays]);

const analyticsMax = useMemo(() => {
  if (!analyticsRows.length) return 1;
  return Math.max(...analyticsRows.map((item) => item.total));
}, [analyticsRows]);

const upcomingReminders = useMemo(() => {
  return subscriptions
    .map((item) => ({
      ...item,
      daysLeft: daysUntil(item.next_payment_date),
    }))
    .filter((item) => item.daysLeft >= 1 && item.daysLeft <= 3)
    .sort((a, b) => a.daysLeft - b.daysLeft);
}, [subscriptions]);

  const filteredSubscriptions = useMemo(() => {
    if (filterService === "Все") return subscriptions;
    return subscriptions.filter((item) => String(item.name || "").toLowerCase().includes(filterService.toLowerCase()));
  }, [subscriptions, filterService]);

  const monthlyTotal = useMemo(() => {
    return subscriptions.reduce((sum, item) => {
      const price = Number(item.price || 0);
      return sum + (item.billing_cycle === "yearly" ? price / 12 : price);
    }, 0);
  }, [subscriptions]);

  const yearlyTotal = useMemo(() => monthlyTotal * 12, [monthlyTotal]);

  if (loading) {
    return (
      <SafeAreaView style={styles.loadingScreen}>
        <ExpoStatusBar style="light" />
        <ActivityIndicator size="large" color="#ffffff" />
        <Text style={styles.loadingText}>Payly запускается…</Text>
      </SafeAreaView>
    );
  }

  if (!user) {
    return (
      <SafeAreaView style={styles.screen}>
        <ExpoStatusBar style="light" />
        <StatusBar barStyle="light-content" />
        <ScrollView contentContainerStyle={styles.authScroll} keyboardShouldPersistTaps="handled">
          <View style={styles.heroCard}>
            <Text style={styles.brand}>Payly</Text>
            <Text style={styles.heroTitle}>Отслеживание активных подписок</Text>
            <Text style={styles.heroText}>
              Приложение теперь не падает при недоступном backend: можно сразу запустить демо-режим и проверить интерфейс в Android эмуляторе.
            </Text>
          </View>

          <View style={[styles.connectionBanner, backendReachable ? styles.connectionOk : styles.connectionWarn]}>
            <Text style={styles.connectionBannerText}>{connectionStatus}</Text>
          </View>

          <View style={styles.formCard}>
            <View style={styles.segmentedWrap}>
              <Pressable style={[styles.segmentButton, mode === "login" && styles.segmentButtonActive]} onPress={() => setMode("login")}>
                <Text style={styles.segmentText}>Вход</Text>
              </Pressable>
              <Pressable style={[styles.segmentButton, mode === "register" && styles.segmentButtonActive]} onPress={() => setMode("register")}>
                <Text style={styles.segmentText}>Регистрация</Text>
              </Pressable>
            </View>

            <Field label="Email" value={email} onChangeText={setEmail} placeholder="you@example.com" keyboardType="email-address" />
            <Field label="Пароль" value={password} onChangeText={setPassword} placeholder="Минимум 4 символа" secureTextEntry />

            <PrimaryButton
              title={busy ? "Подождите…" : mode === "login" ? "Войти" : "Создать аккаунт"}
              onPress={mode === "login" ? handleLogin : handleRegister}
              disabled={busy}
            />

            <PrimaryButton title="Запустить демо без backend" onPress={enableLocalMode} secondary />

            <Text style={styles.settingsTitle}>Адрес backend</Text>
            <Field
              label={Platform.OS === "android" ? "Для Android Emulator обычно http://10.0.2.2:8000" : "Для iOS simulator обычно http://127.0.0.1:8000"}
              value={apiBaseUrlDraft}
              onChangeText={setApiBaseUrlDraft}
              placeholder="http://10.0.2.2:8000"
              autoCapitalize="none"
            />
            <PrimaryButton title="Сохранить URL API" onPress={saveApiBase} secondary />
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <ExpoStatusBar style="light" />
      <StatusBar barStyle="light-content" />
      <ScrollView contentContainerStyle={styles.dashboardScroll} keyboardShouldPersistTaps="handled">
        <View style={styles.topBar}>
          <View>
            <Text style={styles.topSubtitle}>{usingLocalMode ? "Локальный демо-режим" : "Подписки пользователя"}</Text>
            <Text style={styles.topTitle}>{user.email}</Text>
          </View>
          <Pressable style={styles.logoutButton} onPress={handleLogout}>
            <Text style={styles.logoutText}>{usingLocalMode ? "Сбросить" : "Выйти"}</Text>
          </Pressable>
        </View>

        <View style={[styles.connectionBanner, usingLocalMode ? styles.connectionWarn : styles.connectionOk]}>
          <Text style={styles.connectionBannerText}>{connectionStatus}</Text>
        </View>

        <View style={styles.statsRow}>
          <StatCard title="Активных" value={String(subscriptions.length)} accent="#60a5fa" />
          <StatCard title="В месяц" value={formatMoney(monthlyTotal)} accent="#34d399" />
          <StatCard title="В год" value={formatMoney(yearlyTotal)} accent="#fbbf24" />
        </View>

        <View style={styles.actionCard}>
          <Text style={styles.sectionTitle}>Быстрые действия</Text>
          <View style={styles.actionRow}>
            <PrimaryButton title="Добавить вручную" onPress={() => setShowAddModal(true)} />
            <PrimaryButton title="Обновить" onPress={refreshSubs} secondary />
          </View>
          <View style={styles.actionRow}>
            <PrimaryButton title="Подключить Gmail" onPress={() => handleConnectProvider("gmail")} disabled={usingLocalMode} />
            <PrimaryButton title="Проверить импорт" onPress={() => handlePreviewImport("gmail")} secondary disabled={usingLocalMode} />
          </View>
          <View style={styles.actionRow}>
            <PrimaryButton title="Подключить Mail.ru" onPress={() => handleConnectProvider("mailru")} disabled={usingLocalMode} />
            <PrimaryButton title="Импорт из Mail.ru" onPress={() => handlePreviewImport("mailru")} secondary disabled={usingLocalMode} />
          </View>
          <View style={styles.actionRow}>
  <PrimaryButton title="Тест уведомления 5 сек" onPress={triggerTestNotification} />
</View>
          {usingLocalMode ? (
            <View style={styles.actionRow}>
              <PrimaryButton title="Выйти из демо-режима" onPress={disableLocalMode} secondary />
            </View>
          ) : null}
          <Text style={styles.helperText}>
            {usingLocalMode
              ? "Сейчас приложение работает полностью локально и не требует backend для теста в эмуляторе."
              : "После подключения почты в браузере вернитесь в приложение и нажмите кнопку проверки импорта."}
          </Text>
        </View>

        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Поддерживаемые сервисы</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.servicesRow}>
            <ServiceChip label="Все" active={filterService === "Все"} onPress={() => setFilterService("Все")} />
            {DEFAULT_SERVICES.map((service) => (
              <ServiceChip
                key={service}
                label={service}
                active={filterService === service}
                onPress={() => setFilterService(service)}
              />
            ))}
          </ScrollView>
        </View>
        <View style={styles.sectionCard}>
  <Text style={styles.sectionTitle}>Уведомления о списаниях</Text>
  <Text style={styles.helperText}>
    Локальные уведомления автоматически планируются за 3, 2 и 1 день до следующего списания.
  </Text>

  {upcomingReminders.length === 0 ? (
    <Text style={styles.emptyText}>На ближайшие 1–3 дня списаний нет.</Text>
  ) : (
    upcomingReminders.map((item) => (
      <View key={`notify-${item.id}`} style={styles.noticeCard}>
        <Text style={styles.subTitle}>{item.name}</Text>
        <Text style={styles.subMeta}>
          Через {item.daysLeft} дн. • {formatMoney(item.price)}
        </Text>
        <Text style={styles.subMeta}>
          Дата списания: {String(item.next_payment_date)}
        </Text>
      </View>
    ))
  )}
</View>

<View style={styles.sectionCard}>
  <Text style={styles.sectionTitle}>Аналитика расходов</Text>
  <Text style={styles.helperText}>
    Прогноз расходов по подпискам за выбранный период.
  </Text>

  <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.servicesRow}>
    {PERIOD_OPTIONS.map((item) => (
      <ServiceChip
        key={item.key}
        label={item.label}
        active={analyticsPeriod === item.key}
        onPress={() => setAnalyticsPeriod(item.key)}
      />
    ))}
  </ScrollView>

  {analyticsRows.length === 0 ? (
    <Text style={styles.emptyText}>Недостаточно данных для графика.</Text>
  ) : (
    analyticsRows.slice(0, 6).map((item) => (
      <AnalyticsBar
        key={item.name}
        label={item.name}
        value={item.total}
        maxValue={analyticsMax}
      />
    ))
  )}
</View>
        <View style={styles.sectionCard}>
          <Text style={styles.sectionTitle}>Мои подписки</Text>
          {filteredSubscriptions.length === 0 ? (
            <Text style={styles.emptyText}>Подписок пока нет. Добавьте вручную или импортируйте из почты.</Text>
          ) : (
            filteredSubscriptions.map((item) => (
              <View key={item.id} style={styles.subCard}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.subTitle}>{item.name}</Text>
                  <Text style={styles.subMeta}>{formatMoney(item.price)} • {formatCycle(item.billing_cycle)}</Text>
                  <Text style={styles.subMeta}>Следующее списание: {String(item.next_payment_date)}</Text>
                </View>
                <Pressable style={styles.deletePill} onPress={() => handleDeleteSub(item.id)}>
                  <Text style={styles.deletePillText}>Удалить</Text>
                </Pressable>
              </View>
            ))
          )}
        </View>
      </ScrollView>

      <Modal visible={showAddModal} animationType="slide" transparent>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Новая подписка</Text>
            <Field label="Название" value={subName} onChangeText={setSubName} placeholder="Spotify Premium" autoCapitalize="sentences" />
            <Field label="Цена" value={subPrice} onChangeText={setSubPrice} placeholder="299" keyboardType="numeric" />
            <View style={styles.switchRow}>
              <Text style={styles.fieldLabel}>Годовой тариф</Text>
              <Switch value={subCycle === "yearly"} onValueChange={(value) => setSubCycle(value ? "yearly" : "monthly")} />
            </View>
            <Field label="Дата следующего платежа" value={subDate} onChangeText={setSubDate} placeholder="2026-04-25" />
            <View style={styles.modalActions}>
              <PrimaryButton title="Сохранить" onPress={handleCreateSub} />
              <PrimaryButton title="Отмена" onPress={() => setShowAddModal(false)} secondary />
            </View>
          </View>
        </View>
      </Modal>

      <Modal visible={showImportModal} animationType="slide" transparent>
        <View style={styles.modalBackdrop}>
          <View style={[styles.modalCard, { maxHeight: "80%" }]}>
            <Text style={styles.modalTitle}>Импорт из {selectedProvider === "gmail" ? "Gmail" : "Mail.ru"}</Text>
            <ScrollView>
              {candidates.length === 0 ? (
                <Text style={styles.emptyText}>Кандидаты не найдены.</Text>
              ) : (
                candidates.map((item) => {
                  const active = !!selectedKeys[item.candidate_key];
                  return (
                    <Pressable
                      key={item.candidate_key}
                      onPress={() => setSelectedKeys((prev) => ({ ...prev, [item.candidate_key]: !prev[item.candidate_key] }))}
                      style={[styles.importItem, active && styles.importItemActive]}
                    >
                      <View style={styles.importCheckbox}>{active ? <View style={styles.importCheckboxInner} /> : null}</View>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.subTitle}>{item.name}</Text>
                        <Text style={styles.subMeta}>{formatMoney(item.price)} • {formatCycle(item.billing_cycle)}</Text>
                        <Text style={styles.subMeta}>Следующая дата: {String(item.next_payment_date)}</Text>
                      </View>
                    </Pressable>
                  );
                })
              )}
            </ScrollView>
            <View style={styles.modalActions}>
              <PrimaryButton title="Импортировать выбранные" onPress={handleImportSelected} disabled={!candidates.length} />
              <PrimaryButton title="Закрыть" onPress={() => setShowImportModal(false)} secondary />
            </View>
          </View>
        </View>
      </Modal>

      {busy ? (
        <View style={styles.busyOverlay}>
          <ActivityIndicator size="large" color="#fff" />
        </View>
      ) : null}
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: "#0f172a",
  },
  loadingScreen: {
    flex: 1,
    backgroundColor: "#0f172a",
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    padding: 24,
  },
  loadingText: {
    color: "#fff",
    fontSize: 16,
  },
  authScroll: {
    padding: 20,
    gap: 18,
    paddingBottom: 36,
  },
  dashboardScroll: {
    padding: 18,
    gap: 16,
    paddingBottom: 40,
  },
  heroCard: {
    backgroundColor: "#1e1b4b",
    borderRadius: 28,
    padding: 24,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  brand: {
    color: "#a5b4fc",
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 10,
  },
  heroTitle: {
    color: "#fff",
    fontSize: 28,
    lineHeight: 34,
    fontWeight: "800",
    marginBottom: 10,
    textAlign: "center",
  },
  heroText: {
    color: "#cbd5e1",
    fontSize: 15,
    lineHeight: 22,
  },
  connectionBanner: {
    borderRadius: 18,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderWidth: 1,
  },
  connectionOk: {
    backgroundColor: "rgba(16,185,129,0.12)",
    borderColor: "rgba(16,185,129,0.35)",
  },
  connectionWarn: {
    backgroundColor: "rgba(251,191,36,0.12)",
    borderColor: "rgba(251,191,36,0.35)",
  },
  connectionBannerText: {
    color: "#e2e8f0",
    fontWeight: "700",
  },
  formCard: {
    backgroundColor: "#111827",
    borderRadius: 28,
    padding: 20,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
    gap: 10,
  },
  segmentedWrap: {
    flexDirection: "row",
    backgroundColor: "#0f172a",
    borderRadius: 999,
    padding: 4,
    marginBottom: 12,
  },
  segmentButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 999,
    alignItems: "center",
  },
  segmentButtonActive: {
    backgroundColor: "#4338ca",
  },
  segmentText: {
    color: "#fff",
    fontWeight: "700",
  },
  fieldWrap: {
    gap: 8,
    marginBottom: 10,
  },
  fieldLabel: {
    color: "#cbd5e1",
    fontSize: 13,
    lineHeight: 18,
  },
  input: {
    borderRadius: 16,
    backgroundColor: "#1f2937",
    color: "#fff",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  settingsTitle: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "700",
    marginTop: 4,
    marginBottom: 4,
  },
  topBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
    gap: 12,
  },
  topSubtitle: {
    color: "#94a3b8",
    fontSize: 13,
  },
  topTitle: {
    color: "#fff",
    fontSize: 20,
    fontWeight: "800",
    marginTop: 2,
    maxWidth: 240,
  },
  logoutButton: {
    backgroundColor: "#1f2937",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  logoutText: {
    color: "#fff",
    fontWeight: "700",
  },
  statsRow: {
    flexDirection: "row",
    gap: 10,
  },
  statCard: {
    flex: 1,
    backgroundColor: "#111827",
    borderRadius: 24,
    padding: 16,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
    minHeight: 110,
    justifyContent: "space-between",
  },
  statTitle: {
    color: "#94a3b8",
    fontSize: 13,
  },
  statValue: {
    color: "#fff",
    fontSize: 22,
    fontWeight: "800",
  },
  actionCard: {
    backgroundColor: "#1e1b4b",
    borderRadius: 28,
    padding: 18,
    gap: 10,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  sectionCard: {
    backgroundColor: "#111827",
    borderRadius: 28,
    padding: 18,
    gap: 12,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  sectionTitle: {
    color: "#fff",
    fontSize: 18,
    fontWeight: "800",
  },
  actionRow: {
    flexDirection: "row",
    gap: 10,
  },
  primaryButton: {
    flex: 1,
    backgroundColor: "#4338ca",
    paddingVertical: 14,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
  },
  secondaryButton: {
    backgroundColor: "#243042",
  },
  dangerButton: {
    backgroundColor: "#991b1b",
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  primaryButtonText: {
    color: "#fff",
    fontWeight: "800",
    fontSize: 14,
    textAlign: "center",
  },
  helperText: {
    color: "#cbd5e1",
    fontSize: 13,
    lineHeight: 19,
  },
  servicesRow: {
    gap: 10,
    paddingRight: 8,
  },
  serviceChip: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 999,
    backgroundColor: "#1f2937",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  serviceChipActive: {
    backgroundColor: "#4338ca",
  },
  serviceChipText: {
    color: "#e2e8f0",
    fontWeight: "700",
  },
  serviceChipTextActive: {
    color: "#fff",
  },
  subCard: {
    flexDirection: "row",
    gap: 12,
    padding: 16,
    borderRadius: 22,
    backgroundColor: "#0f172a",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.06)",
    alignItems: "center",
  },
  subTitle: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "800",
    marginBottom: 4,
  },
  subMeta: {
    color: "#94a3b8",
    fontSize: 13,
    lineHeight: 18,
  },
  deletePill: {
    backgroundColor: "rgba(239,68,68,0.16)",
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 999,
  },
  deletePillText: {
    color: "#fca5a5",
    fontWeight: "800",
  },
  emptyText: {
    color: "#94a3b8",
    fontSize: 14,
    lineHeight: 20,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(2,6,23,0.82)",
    justifyContent: "center",
    padding: 16,
  },
  modalCard: {
    backgroundColor: "#111827",
    borderRadius: 28,
    padding: 18,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
  },
  modalTitle: {
    color: "#fff",
    fontSize: 22,
    fontWeight: "800",
    marginBottom: 12,
  },
  modalActions: {
    flexDirection: "row",
    gap: 10,
    marginTop: 12,
  },
  switchRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#1f2937",
    borderRadius: 16,
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginBottom: 10,
  },
  importItem: {
    flexDirection: "row",
    gap: 12,
    borderRadius: 20,
    padding: 14,
    backgroundColor: "#0f172a",
    marginBottom: 10,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.06)",
  },
  importItemActive: {
    borderColor: "#4338ca",
    backgroundColor: "rgba(67,56,202,0.14)",
  },
  importCheckbox: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: "#6366f1",
    alignItems: "center",
    justifyContent: "center",
    marginTop: 4,
  },
  importCheckboxInner: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: "#818cf8",
  },
  busyOverlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(15,23,42,0.45)",
    alignItems: "center",
    justifyContent: "center",
  },
  analyticsRow: {
  marginTop: 8,
  gap: 8,
},
analyticsTextWrap: {
  flexDirection: "row",
  justifyContent: "space-between",
  alignItems: "center",
},
analyticsLabel: {
  color: "#fff",
  fontSize: 14,
  fontWeight: "700",
  flex: 1,
  marginRight: 12,
},
analyticsValue: {
  color: "#cbd5e1",
  fontSize: 13,
  fontWeight: "700",
},
analyticsTrack: {
  height: 12,
  borderRadius: 999,
  backgroundColor: "#0f172a",
  overflow: "hidden",
  borderWidth: 1,
  borderColor: "rgba(255,255,255,0.06)",
},
analyticsFill: {
  height: "100%",
  borderRadius: 999,
  backgroundColor: "#4338ca",
},
noticeCard: {
  padding: 14,
  borderRadius: 20,
  backgroundColor: "#0f172a",
  borderWidth: 1,
  borderColor: "rgba(255,255,255,0.06)",
  gap: 4,
},
});
