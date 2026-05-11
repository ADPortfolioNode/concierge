import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { router } from 'expo-router';
import React from 'react';
import { Pressable, StyleSheet, Text } from 'react-native';

import { useColors } from '@/hooks/useColors';
import { setPendingPrompt } from '@/lib/promptStore';

interface PromptCardProps {
  text: string;
}

export default function PromptCard({ text }: PromptCardProps) {
  const colors = useColors();

  const handlePress = () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setPendingPrompt(text);
    router.navigate('/');
  };

  return (
    <Pressable
      onPress={handlePress}
      style={({ pressed }) => [
        styles.card,
        {
          backgroundColor: pressed ? colors.secondary : colors.card,
          borderColor: colors.border,
        },
      ]}
    >
      <Text style={[styles.text, { color: colors.foreground }]} numberOfLines={3}>
        {text}
      </Text>
      <Ionicons name="arrow-forward-circle-outline" size={18} color={colors.primary} style={styles.icon} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 14,
    marginBottom: 8,
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
  },
  text: {
    flex: 1,
    fontSize: 14,
    fontFamily: 'Inter_400Regular',
    lineHeight: 20,
  },
  icon: {
    marginTop: 1,
    flexShrink: 0,
  },
});
