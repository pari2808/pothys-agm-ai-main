import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Animated,
  Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useAICopilotQuery, useAIConversations } from '../../hooks/useAI';
import { useAuthStore } from '../../store/authStore';
import { useThemeStore } from '../../store/themeStore';
import apiClient from '../../services/api';

const SUGGESTED_PROMPTS = [
  "Which branches haven't submitted today's report?",
  "Compare Padi and Coimbatore.",
  "Show today's operational alerts.",
  "Summarize yesterday's performance.",
];

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  retrieved_sources?: string[] | null;
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good Morning';
  if (hour < 17) return 'Good Afternoon';
  return 'Good Evening';
}

export default function AICopilotScreen() {
  const { user } = useAuthStore();
  const { colors } = useThemeStore();

  // ─── Core state ────────────────────────────────────────────────────────────
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedSourceContent, setSelectedSourceContent] = useState<string | null>(null);

  // ─── Refs ──────────────────────────────────────────────────────────────────
  const flatListRef = useRef<FlatList>(null);
  const headerOpacity = useRef(new Animated.Value(0)).current;
  // Using refs for values read inside async callbacks — prevents stale closures
  // and avoids recreating useCallback on every state change (which was the
  // primary cause of the accumulated re-render freeze after ~5 messages).
  const activeConvIdRef = useRef<string | null>(null);
  const isLoadingRef = useRef(false); // ← THE KEY FIX: never stale inside callbacks
  const inputTextRef = useRef('');

  // Keep refs in sync with state
  useEffect(() => { activeConvIdRef.current = activeConvId; }, [activeConvId]);
  useEffect(() => { inputTextRef.current = inputText; }, [inputText]);

  // ─── React Query ───────────────────────────────────────────────────────────
  // NOTE: We do NOT use useAIConversationDetails here.
  // Polling convDetails and syncing it to local `messages` caused an infinite
  // re-render loop: messages change → effect fires → setMessages → messages change…
  // Instead we manage all message state locally and only call the backend imperatively.
  const { refetch: refetchConvs } = useAIConversations();

  // ─── Fade-in header ────────────────────────────────────────────────────────
  useEffect(() => {
    Animated.timing(headerOpacity, {
      toValue: 1,
      duration: 700,
      useNativeDriver: true,
    }).start();
  }, []);

  // ─── Auto-scroll ───────────────────────────────────────────────────────────
  const msgCount = messages.length;
  useEffect(() => {
    if (msgCount === 0) return;
    const t = setTimeout(() => {
      try { flatListRef.current?.scrollToEnd({ animated: true }); } catch (_) {}
    }, 250);
    return () => clearTimeout(t);
  }, [msgCount]);

  const handleSend = useCallback(async (text?: string) => {
    // Read current input: prefer parameter if passed (e.g. from suggestion chips)
    // fallback to current inputTextRef value
    const rawInput = typeof text === 'string' ? text : inputTextRef.current;
    const trimmed = rawInput ? rawInput.trim() : '';

    console.log({
      input: rawInput,
      trimmedInput: trimmed,
      loading: isLoadingRef.current,
      isLoading: isLoading,
      isSending: isLoading
    });

    if (!trimmed) {
      console.log('[CHAT] handleSend blocked: empty');
      return;
    }
    if (isLoadingRef.current) {
      console.log('[CHAT] handleSend blocked: loading');
      return;
    }

    // Synchronously lock refs to prevent race conditions from double submission
    isLoadingRef.current = true;
    inputTextRef.current = '';

    // Clear input state immediately
    setInputText('');

    // Set loading = true state
    setIsLoading(true);
    console.log('[CHAT] Loading state: TRUE');

    // Optimistically add user bubble
    const userMsg: Message = {
      id: `user-${Date.now()}-${Math.random()}`,
      role: 'user',
      content: trimmed,
    };
    setMessages(prev => {
      const next = [...prev, userMsg];
      console.log(`[CHAT] User message added. Total messages: ${next.length}`);
      return next;
    });

    try {
      const payload: { conversation_id?: string; content: string } = {
        content: trimmed,
      };
      if (activeConvIdRef.current) {
        payload.conversation_id = activeConvIdRef.current;
      }

      console.log(`[CHAT] [LOG_TRACE] Call start: dispatching POST request to /ai/query. ConvId: ${activeConvIdRef.current || 'new'}. Payload:`, payload);
      const requestStartTime = Date.now();
      const res = await apiClient.post('/ai/query', payload);
      const requestEndTime = Date.now();
      console.log(`[CHAT] [LOG_TRACE] Call complete: response received for /ai/query in ${requestEndTime - requestStartTime}ms. Response data:`, res.data);
      const data = res.data;

      // Save conversation ID on first message
      if (!activeConvIdRef.current && data.conversation_id) {
        setActiveConvId(data.conversation_id);
        activeConvIdRef.current = data.conversation_id; // update ref immediately
        refetchConvs();
      }

      const assistantMsg: Message = {
        id: data.id || `ai-${Date.now()}-${Math.random()}`,
        role: 'assistant',
        content: data.content,
        retrieved_sources: data.retrieved_sources,
      };

      setMessages(prev => {
        const next = [...prev, assistantMsg];
        console.log(`[CHAT] Assistant message added. Total messages: ${next.length}`);
        return next;
      });
    } catch (err: any) {
      console.error('[CHAT] Request error:', err?.message || err);
      const detail = err?.response?.data?.detail;
      const errorMsg: Message = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: detail
          ? `⚠️ ${detail}`
          : '⚠️ I encountered an issue processing your request. Please try again.',
        retrieved_sources: [],
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      // ALWAYS unlock — prevents permanent input disable even after exceptions
      isLoadingRef.current = false;
      setIsLoading(false);
      console.log('[CHAT] Loading state: FALSE (finally)');
    }
  }, [refetchConvs]); // ← isLoading intentionally NOT listed here

  // ─── Message renderer ──────────────────────────────────────────────────────
  const renderMessage = useCallback(({ item }: { item: Message }) => {
    const isUser = item.role === 'user';
    return (
      <View style={[styles.msgWrapper, isUser ? styles.msgWrapperUser : styles.msgWrapperAssistant]}>
        {!isUser && (
          <View style={[styles.avatarDot, { backgroundColor: colors.primary + '20', borderColor: colors.primary + '40' }]}>
            <Text style={styles.avatarDotText}>✨</Text>
          </View>
        )}
        <View style={[
          styles.bubble,
          isUser
            ? [styles.bubbleUser, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]
            : [styles.bubbleAssistant, { backgroundColor: colors.surface, borderColor: colors.primary + '30' }]
        ]}>
          <Text style={[styles.bubbleText, { color: colors.text }]}>
            {item.content}
          </Text>

          {/* Citation chips */}
          {!isUser && item.retrieved_sources && item.retrieved_sources.length > 0 && (
            <View style={[styles.sourcesRow, { borderColor: colors.border }]}>
              <Text style={[styles.sourcesLabel, { color: colors.textSecondary }]}>Sources: </Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                {item.retrieved_sources.map((src, idx) => (
                  <TouchableOpacity
                    key={idx}
                    style={[styles.sourceChip, { backgroundColor: colors.primary + '18', borderColor: colors.primary + '40' }]}
                    onPress={() => {
                      setSelectedSourceContent(`[RAG Source ${idx + 1}]\n\n${src}`);
                      setModalVisible(true);
                    }}
                  >
                    <Text style={[styles.sourceChipText, { color: colors.primary }]}>⟨ {idx + 1} ⟩</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>
          )}
        </View>
      </View>
    );
  }, [colors]);

  // ─── Render ────────────────────────────────────────────────────────────────
  const showEmpty = messages.length === 0;

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['bottom']}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.keyboardContainer}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        {/* Chat list */}
        <FlatList
          ref={flatListRef}
          data={messages}
          renderItem={renderMessage}
          keyExtractor={item => item.id}
          extraData={messages.length}
          style={{ flex: 1 }}
          contentContainerStyle={showEmpty ? styles.emptyContent : styles.msgContent}
          removeClippedSubviews={false}
          windowSize={21}
          initialNumToRender={50}
          maxToRenderPerBatch={50}
          ListEmptyComponent={
            <Animated.View style={[styles.emptyContainer, { opacity: headerOpacity }]}>
              <View style={[styles.emptyLogo, { backgroundColor: colors.surfaceAlt, borderColor: colors.primary + '50' }]}>
                <Text style={styles.emptyLogoIcon}>✨</Text>
              </View>
              <Text style={[styles.emptyTitle, { color: colors.text }]}>Pothys AGM AI Copilot</Text>
              <Text style={[styles.emptyGreeting, { color: colors.primary }]}>{getGreeting()}, {user?.full_name?.split(' ')[0] || 'Sir'}.</Text>
              <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>How can I assist you today?</Text>

              <View style={styles.suggestionsContainer}>
                {SUGGESTED_PROMPTS.map((prompt, idx) => (
                  <TouchableOpacity
                    key={idx}
                    style={[styles.suggestionCard, { backgroundColor: colors.surface, borderColor: colors.border }]}
                    onPress={() => handleSend(prompt)}
                    activeOpacity={0.8}
                    disabled={isLoading}
                  >
                    <Text style={[styles.suggestionText, { color: colors.textSecondary }]}>{prompt}</Text>
                    <Text style={[styles.suggestionArrow, { color: colors.primary }]}>›</Text>
                  </TouchableOpacity>
                ))}
              </View>
            </Animated.View>
          }
        />

        {/* Typing indicator */}
        {isLoading && (
          <View style={styles.typingBar}>
            <View style={styles.typingDots}>
              <TypingDot delay={0} color={colors.primary} />
              <TypingDot delay={200} color={colors.primary} />
              <TypingDot delay={400} color={colors.primary} />
            </View>
            <Text style={[styles.typingText, { color: colors.primary }]}>Copilot is thinking...</Text>
          </View>
        )}

        {/* Input area */}
        <View style={[styles.inputArea, { borderColor: colors.border, backgroundColor: colors.surface }]}>
          <TextInput
            style={[styles.input, { backgroundColor: colors.background, borderColor: colors.border, color: colors.text }]}
            placeholder="Ask a business question..."
            placeholderTextColor={colors.textMuted}
            value={inputText}
            onChangeText={setInputText}
            editable={!isLoading}
            multiline
            maxLength={500}
            onSubmitEditing={() => handleSend()}
            returnKeyType="send"
            blurOnSubmit
          />
          <TouchableOpacity
            style={[
              styles.sendBtn,
              { backgroundColor: colors.primary },
              (!inputText.trim() || isLoading) && styles.sendBtnDisabled
            ]}
            onPress={() => handleSend()}
            disabled={!inputText.trim() || isLoading}
            activeOpacity={0.8}
          >
            <Text style={[styles.sendBtnText, { color: colors.textOnPrimary }]}>↑</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {/* Source detail modal */}
      <Modal
        animationType="slide"
        transparent
        visible={modalVisible}
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalSheet, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <View style={[styles.modalHandle, { backgroundColor: colors.border }]} />
            <Text style={[styles.modalTitle, { color: colors.primary }]}>RAG Source Reference</Text>
            <ScrollView style={styles.modalScroll} showsVerticalScrollIndicator={false}>
              <Text style={[styles.modalBody, { color: colors.text }]}>{selectedSourceContent}</Text>
            </ScrollView>
            <TouchableOpacity
              style={[styles.modalCloseBtn, { backgroundColor: colors.surfaceAlt, borderColor: colors.border }]}
              onPress={() => setModalVisible(false)}
              activeOpacity={0.8}
            >
              <Text style={[styles.modalCloseBtnText, { color: colors.textSecondary }]}>Close</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

// ─── Typing dot animation ───────────────────────────────────────────────────
function TypingDot({ delay, color }: { delay: number; color: string }) {
  const anim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(anim, { toValue: 1, duration: 400, delay, useNativeDriver: true }),
        Animated.timing(anim, { toValue: 0, duration: 400, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, []);

  return (
    <Animated.View
      style={[
        styles.typingDot,
        {
          backgroundColor: color,
          opacity: anim,
          transform: [{ translateY: anim.interpolate({ inputRange: [0, 1], outputRange: [0, -4] }) }],
        },
      ]}
    />
  );
}

// ─── Styles ─────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  container: { flex: 1 },
  keyboardContainer: { flex: 1 },
  emptyContent: { flexGrow: 1 },
  msgContent: { padding: 20, paddingBottom: 12 },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 28,
    paddingVertical: 40,
  },
  emptyLogo: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 24,
  },
  emptyLogoIcon: { fontSize: 36 },
  emptyTitle: { fontSize: 22, fontWeight: '800', letterSpacing: 0.3, marginBottom: 10 },
  emptyGreeting: { fontSize: 18, fontWeight: '600', marginBottom: 6 },
  emptySubtitle: { fontSize: 15, marginBottom: 36 },
  suggestionsContainer: { width: '100%', gap: 12 },
  suggestionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 16,
    paddingHorizontal: 20,
    paddingVertical: 15,
  },
  suggestionText: { flex: 1, fontSize: 14, lineHeight: 20 },
  suggestionArrow: { fontSize: 20, fontWeight: '300', marginLeft: 10 },
  msgWrapper: { flexDirection: 'row', marginBottom: 20, alignItems: 'flex-end' },
  msgWrapperUser: { justifyContent: 'flex-end' },
  msgWrapperAssistant: { justifyContent: 'flex-start', gap: 12 },
  avatarDot: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  avatarDotText: { fontSize: 15 },
  bubble: { maxWidth: '82%', borderRadius: 20, padding: 16, borderWidth: 1 },
  bubbleUser: { borderBottomRightRadius: 4 },
  bubbleAssistant: { borderBottomLeftRadius: 4 },
  bubbleText: { fontSize: 16, lineHeight: 24 },
  sourcesRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
  },
  sourcesLabel: { fontSize: 11, fontWeight: '700', marginRight: 8 },
  sourceChip: { borderWidth: 1, paddingHorizontal: 12, paddingVertical: 5, borderRadius: 10, marginRight: 8 },
  sourceChipText: { fontSize: 11, fontWeight: '700' },
  typingBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 12,
    gap: 12,
  },
  typingDots: { flexDirection: 'row', gap: 5, alignItems: 'center' },
  typingDot: { width: 6, height: 6, borderRadius: 3 },
  typingText: { fontSize: 13, fontWeight: '500' },
  inputArea: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderTopWidth: 1,
    alignItems: 'center',
    gap: 12,
  },
  input: {
    flex: 1,
    borderWidth: 1,
    paddingHorizontal: 20,
    paddingVertical: Platform.OS === 'ios' ? 14 : 10,
    borderRadius: 28,
    fontSize: 16,
    maxHeight: 120,
    lineHeight: 22,
  },
  sendBtn: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 5,
    elevation: 3,
  },
  sendBtnDisabled: { opacity: 0.4, shadowOpacity: 0 },
  sendBtnText: { fontSize: 22, fontWeight: '800', lineHeight: 24 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'flex-end' },
  modalSheet: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 28,
    maxHeight: '60%',
    borderWidth: 1,
  },
  modalHandle: { width: 40, height: 5, borderRadius: 2.5, alignSelf: 'center', marginBottom: 20 },
  modalTitle: {
    fontSize: 15,
    fontWeight: '800',
    letterSpacing: 2,
    textTransform: 'uppercase',
    marginBottom: 20,
    textAlign: 'center',
  },
  modalScroll: { marginBottom: 24, maxHeight: 300 },
  modalBody: { fontSize: 15, lineHeight: 24 },
  modalCloseBtn: { borderWidth: 1, paddingVertical: 16, borderRadius: 14, alignItems: 'center' },
  modalCloseBtnText: { fontWeight: '700', fontSize: 15 },
});
