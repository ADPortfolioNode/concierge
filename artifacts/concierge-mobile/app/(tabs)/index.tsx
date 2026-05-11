import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { useFocusEffect } from 'expo-router';
import React, { useCallback, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { KeyboardAvoidingView } from 'react-native-keyboard-controller';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';

import { useColors } from '@/hooks/useColors';
import { ChatMessage, sendMessage } from '@/lib/api';
import { consumePendingPrompt } from '@/lib/promptStore';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  error?: boolean;
}

let msgCounter = 0;
function genId(): string {
  msgCounter++;
  return `m-${Date.now()}-${msgCounter}-${Math.random().toString(36).slice(2, 7)}`;
}

function TypingIndicator({ colors }: { colors: ReturnType<typeof useColors> }) {
  return (
    <Animated.View
      entering={FadeIn.duration(200)}
      style={[styles.bubble, styles.aiBubble, { backgroundColor: colors.aiBubble, borderColor: colors.border }]}
    >
      <View style={styles.typingDots}>
        {[0, 1, 2].map((i) => (
          <TypingDot key={i} delay={i * 150} color={colors.primary} />
        ))}
      </View>
    </Animated.View>
  );
}

function TypingDot({ delay, color }: { delay: number; color: string }) {
  const [opacity, setOpacity] = React.useState(0.3);
  React.useEffect(() => {
    let mounted = true;
    const run = () => {
      setTimeout(() => {
        if (!mounted) return;
        setOpacity(1);
        setTimeout(() => {
          if (!mounted) return;
          setOpacity(0.3);
          setTimeout(run, 300);
        }, 300);
      }, delay);
    };
    run();
    return () => { mounted = false; };
  }, [delay]);

  return (
    <View style={[styles.dot, { backgroundColor: color, opacity }]} />
  );
}

function MessageBubble({ msg, colors }: { msg: Message; colors: ReturnType<typeof useColors> }) {
  const isUser = msg.role === 'user';
  return (
    <Animated.View
      entering={FadeInDown.duration(250).springify()}
      style={[
        styles.bubbleRow,
        isUser ? styles.bubbleRowUser : styles.bubbleRowAI,
      ]}
    >
      {!isUser && (
        <View style={[styles.avatar, { backgroundColor: colors.primary }]}>
          <Ionicons name="sparkles" size={12} color="#fff" />
        </View>
      )}
      <View
        style={[
          styles.bubble,
          isUser
            ? [styles.userBubble, { backgroundColor: colors.userBubble }]
            : [styles.aiBubble, {
                backgroundColor: msg.error ? '#FEF2F2' : colors.aiBubble,
                borderColor: msg.error ? colors.destructive : colors.border,
              }],
        ]}
      >
        <Text
          style={[
            styles.bubbleText,
            { color: isUser ? colors.userBubbleText : (msg.error ? colors.destructive : colors.aiBubbleText) },
          ]}
        >
          {msg.content}
        </Text>
      </View>
    </Animated.View>
  );
}

function EmptyChat({ colors }: { colors: ReturnType<typeof useColors> }) {
  return (
    <View style={styles.emptyContainer}>
      <View style={[styles.emptyIcon, { backgroundColor: colors.card, borderColor: colors.border }]}>
        <Ionicons name="sparkles-outline" size={32} color={colors.primary} />
      </View>
      <Text style={[styles.emptyTitle, { color: colors.foreground }]}>Concierge AI</Text>
      <Text style={[styles.emptySubtitle, { color: colors.mutedForeground }]}>
        Your intelligent assistant.{'\n'}Ask anything to get started.
      </Text>
    </View>
  );
}

export default function ChatScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const inputRef = useRef<TextInput>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [showTyping, setShowTyping] = useState(false);

  // Pick up any prompt tapped on Goals / Strategy / Workspace tabs
  useFocusEffect(
    useCallback(() => {
      const pending = consumePendingPrompt();
      if (pending) {
        setInput(pending);
        setTimeout(() => inputRef.current?.focus(), 100);
      }
    }, [])
  );

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || sending) return;

    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setInput('');
    setSending(true);
    setShowTyping(true);

    const currentMessages = [...messages];
    const userMsg: Message = { id: genId(), role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);

    const history: ChatMessage[] = currentMessages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const reply = await sendMessage(text, history);
      setShowTyping(false);
      setMessages((prev) => [
        ...prev,
        { id: genId(), role: 'assistant', content: reply },
      ]);
    } catch (err) {
      setShowTyping(false);
      const errMsg = err instanceof Error ? err.message : 'Something went wrong.';
      setMessages((prev) => [
        ...prev,
        { id: genId(), role: 'assistant', content: `Unable to reach the AI: ${errMsg}`, error: true },
      ]);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }, [input, sending, messages]);

  const reversed = [...messages].reverse();
  const webTopInset = Platform.OS === 'web' ? 67 : 0;
  const webBottomInset = Platform.OS === 'web' ? 34 : 0;

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: colors.background }]}
      behavior="padding"
      keyboardVerticalOffset={0}
    >
      <View style={[styles.header, {
        paddingTop: Platform.OS === 'web' ? webTopInset : insets.top,
        backgroundColor: colors.background,
        borderBottomColor: colors.border,
      }]}>
        <View style={[styles.headerIcon, { backgroundColor: colors.primary }]}>
          <Ionicons name="sparkles" size={16} color="#fff" />
        </View>
        <Text style={[styles.headerTitle, { color: colors.foreground }]}>Concierge</Text>
        {sending && <ActivityIndicator size="small" color={colors.primary} style={styles.headerLoader} />}
      </View>

      <FlatList
        data={reversed}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <MessageBubble msg={item} colors={colors} />}
        inverted={messages.length > 0}
        ListHeaderComponent={showTyping ? <TypingIndicator colors={colors} /> : null}
        ListEmptyComponent={<EmptyChat colors={colors} />}
        keyboardDismissMode="interactive"
        keyboardShouldPersistTaps="handled"
        scrollEnabled={!!messages.length}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.listContent}
      />

      <View style={[
        styles.inputBar,
        {
          backgroundColor: colors.background,
          borderTopColor: colors.border,
          paddingBottom: Platform.OS === 'web'
            ? webBottomInset + 8
            : insets.bottom + 8,
        },
      ]}>
        <View style={[styles.inputWrap, {
          backgroundColor: colors.card,
          borderColor: colors.border,
        }]}>
          <TextInput
            ref={inputRef}
            style={[styles.input, { color: colors.foreground, fontFamily: 'Inter_400Regular' }]}
            placeholder="Message Concierge..."
            placeholderTextColor={colors.mutedForeground}
            value={input}
            onChangeText={setInput}
            multiline
            maxLength={2000}
            blurOnSubmit={false}
            onSubmitEditing={handleSend}
            returnKeyType="send"
            testID="chat-input"
          />
          <Pressable
            onPress={handleSend}
            disabled={!input.trim() || sending}
            style={({ pressed }) => [
              styles.sendBtn,
              { backgroundColor: colors.primary, opacity: (!input.trim() || sending) ? 0.4 : pressed ? 0.75 : 1 },
            ]}
            testID="send-button"
          >
            <Ionicons name="arrow-up" size={18} color="#fff" />
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingBottom: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    gap: 10,
  },
  headerIcon: {
    width: 30,
    height: 30,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 18,
    fontFamily: 'Inter_600SemiBold',
    flex: 1,
  },
  headerLoader: { flex: 1, alignItems: 'flex-end' as const },
  listContent: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    flexGrow: 1,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    paddingVertical: 60,
  },
  emptyIcon: {
    width: 72,
    height: 72,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 22,
    fontFamily: 'Inter_600SemiBold',
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 15,
    fontFamily: 'Inter_400Regular',
    textAlign: 'center',
    lineHeight: 22,
  },
  bubbleRow: {
    flexDirection: 'row',
    marginBottom: 12,
    alignItems: 'flex-end',
    gap: 8,
  },
  bubbleRowUser: { justifyContent: 'flex-end' },
  bubbleRowAI: { justifyContent: 'flex-start' },
  avatar: {
    width: 24,
    height: 24,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 2,
  },
  bubble: {
    maxWidth: '78%',
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  userBubble: {
    borderBottomRightRadius: 4,
  },
  aiBubble: {
    borderBottomLeftRadius: 4,
    borderWidth: 1,
  },
  bubbleText: {
    fontSize: 15,
    fontFamily: 'Inter_400Regular',
    lineHeight: 22,
  },
  typingDots: {
    flexDirection: 'row',
    gap: 5,
    paddingVertical: 2,
    alignItems: 'center',
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 4,
  },
  inputBar: {
    paddingHorizontal: 12,
    paddingTop: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  inputWrap: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    borderRadius: 20,
    borderWidth: 1,
    paddingLeft: 14,
    paddingRight: 6,
    paddingVertical: 6,
    gap: 8,
  },
  input: {
    flex: 1,
    fontSize: 15,
    lineHeight: 22,
    maxHeight: 120,
    paddingVertical: 4,
  },
  sendBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 2,
  },
});
