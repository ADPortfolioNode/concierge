import React from 'react';
import {
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import PromptCard from '@/components/PromptCard';
import { useColors } from '@/hooks/useColors';

const STEPS = [
  { step: '1', title: 'Describe outcome', desc: 'Be specific — include a timeframe and measurable result.' },
  { step: '2', title: 'Planner decomposes', desc: 'Goal → prioritised tasks with dependencies.' },
  { step: '3', title: 'Agents execute', desc: 'Research, Coding, and Critic agents run in parallel.' },
  { step: '4', title: 'Synthesizer reports', desc: 'Key points, risks, and recommendations returned.' },
];

const PROMPT_GROUPS = [
  {
    label: '🚀 Launch & delivery',
    prompts: [
      'Create a 4-week goal to launch a public-facing REST API for our SaaS product.',
      'Plan the rollout of a new authentication system — list tasks, risks, and milestones.',
      'I need to ship a mobile MVP in 6 weeks. Break it into weekly goals.',
      'Map out the go-to-market plan for the v2.0 release.',
    ],
  },
  {
    label: '⚙️ Technical improvement',
    prompts: [
      'Set a goal to reduce CI/CD pipeline time from 12 minutes to under 5.',
      'Improve test coverage from 55% to 85% across all core modules in 3 weeks.',
      'Plan a database schema migration to support multi-tenancy.',
      'Reduce React bundle size by 30% — identify the biggest wins first.',
    ],
  },
  {
    label: '📊 Research & analysis',
    prompts: [
      'Research the top 3 alternatives to Qdrant for our vector store and produce a comparison.',
      'Analyse our Q1 sprint velocity data and recommend process improvements.',
      'Investigate why API p95 latency increased 40% after the last deploy.',
      'Survey industry best practices for LLM observability in 2026.',
    ],
  },
  {
    label: '🤝 Team & process',
    prompts: [
      'Create monthly goals for improving developer onboarding documentation.',
      'Plan a 2-week sprint to reduce the backlog of bug reports by 50%.',
      'Outline a knowledge-transfer plan for the outgoing lead engineer.',
      'Set team objectives for improving code review turnaround to under 24 hours.',
    ],
  },
  {
    label: '🖼️ Multimedia goals',
    prompts: [
      'Generate a logo for this goal/project.',
      'What multimedia assets would support this objective?',
      'Design a promotional banner image for the goal.',
    ],
  },
];

export default function GoalsScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const webTop = Platform.OS === 'web' ? 67 : 0;

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={[
        styles.content,
        {
          paddingTop: Platform.OS === 'web' ? webTop : insets.top,
          paddingBottom: Platform.OS === 'web' ? 84 + 34 : insets.bottom + 84,
        },
      ]}
      showsVerticalScrollIndicator={false}
    >
      {/* Header */}
      <View style={styles.header}>
        <Text style={[styles.title, { color: colors.foreground }]}>🎯 Goals</Text>
        <Text style={[styles.subtitle, { color: colors.mutedForeground }]}>
          Describe an outcome and Concierge decomposes it into a prioritised task tree, runs specialist agents, and synthesises a final report. Tap any prompt to start.
        </Text>
      </View>

      {/* How it works */}
      <View style={[styles.stepsCard, { backgroundColor: colors.card, borderColor: colors.border }]}>
        <Text style={[styles.sectionLabel, { color: colors.primary }]}>HOW IT WORKS</Text>
        {STEPS.map(({ step, title, desc }) => (
          <View key={step} style={styles.stepRow}>
            <View style={[styles.stepNum, { backgroundColor: colors.primary }]}>
              <Text style={styles.stepNumText}>{step}</Text>
            </View>
            <View style={styles.stepBody}>
              <Text style={[styles.stepTitle, { color: colors.foreground }]}>{title}</Text>
              <Text style={[styles.stepDesc, { color: colors.mutedForeground }]}>{desc}</Text>
            </View>
          </View>
        ))}
      </View>

      {/* Prompt groups */}
      {PROMPT_GROUPS.map(({ label, prompts }) => (
        <View key={label} style={styles.group}>
          <View style={[styles.groupDivider, { borderBottomColor: colors.border }]}>
            <Text style={[styles.groupLabel, { color: colors.mutedForeground }]}>{label}</Text>
          </View>
          {prompts.map((p) => <PromptCard key={p} text={p} />)}
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { paddingHorizontal: 16 },
  header: { paddingTop: 20, paddingBottom: 20 },
  title: { fontSize: 26, fontFamily: 'Inter_700Bold', marginBottom: 8 },
  subtitle: { fontSize: 14, fontFamily: 'Inter_400Regular', lineHeight: 22 },
  stepsCard: {
    borderRadius: 14,
    borderWidth: 1,
    padding: 16,
    marginBottom: 24,
    gap: 14,
  },
  sectionLabel: {
    fontSize: 11,
    fontFamily: 'Inter_700Bold',
    letterSpacing: 0.8,
    marginBottom: 4,
  },
  stepRow: { flexDirection: 'row', gap: 12, alignItems: 'flex-start' },
  stepNum: {
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 1,
    flexShrink: 0,
  },
  stepNumText: { fontSize: 12, fontFamily: 'Inter_700Bold', color: '#fff' },
  stepBody: { flex: 1, gap: 2 },
  stepTitle: { fontSize: 13, fontFamily: 'Inter_600SemiBold' },
  stepDesc: { fontSize: 12, fontFamily: 'Inter_400Regular', lineHeight: 18 },
  group: { marginBottom: 20 },
  groupDivider: { borderBottomWidth: 1, paddingBottom: 8, marginBottom: 10 },
  groupLabel: {
    fontSize: 12,
    fontFamily: 'Inter_700Bold',
    textTransform: 'uppercase',
    letterSpacing: 0.7,
  },
});
