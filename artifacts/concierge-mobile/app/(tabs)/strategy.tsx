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

const FRAMEWORKS = [
  { name: 'OKR', full: 'Objectives & Key Results', desc: 'Ambitious objectives with measurable key results. Best for quarterly cycles.', color: '#2563EB' },
  { name: 'SWOT', full: 'Strengths, Weaknesses, Opportunities, Threats', desc: 'Analyse internal capabilities and external forces before committing.', color: '#0891B2' },
  { name: 'RICE', full: 'Reach, Impact, Confidence, Effort', desc: 'Score and rank features to prioritise the highest-leverage work.', color: '#D97706' },
  { name: 'JTBD', full: 'Jobs-to-be-Done', desc: "Define what 'job' users hire your product to do — uncovers real motivations.", color: '#059669' },
  { name: 'North Star', full: 'Single guiding KPI', desc: 'Identify the one metric that best captures delivered value to align all teams.', color: '#BE185D' },
];

const PROMPT_GROUPS = [
  {
    label: '📐 Frameworks',
    prompts: [
      'Write 3 OKRs for a B2B SaaS product team for Q3 2026.',
      'Run a SWOT analysis for a developer-tools startup entering an enterprise market.',
      'Use RICE scoring to rank these 5 features — ask me for the list.',
      'Identify the North Star Metric for a marketplace app connecting freelancers with clients.',
    ],
  },
  {
    label: '🗺️ Roadmapping',
    prompts: [
      'Build a 6-month product roadmap for a data-analytics platform starting from zero.',
      'Create a phased migration plan from a monolith to microservices — 3 phases, 4 weeks each.',
      'Map out a technology adoption roadmap for adding LLM capabilities to an existing SaaS.',
      'Draft a quarterly roadmap that balances new features, tech debt, and compliance work.',
    ],
  },
  {
    label: '⚖️ Decision analysis',
    prompts: [
      'I need to choose between building in-house vs buying a third-party auth solution — help me decide.',
      'Compare the strategic risk of early monetisation vs growth-first approach for a B2C app.',
      'What are the second-order consequences of adopting a serverless architecture for our backend?',
      'Analyse the tradeoffs between TypeScript strictness levels for a large team.',
    ],
  },
  {
    label: '📈 Metrics & KPIs',
    prompts: [
      'Define KPIs for measuring the success of a developer experience improvement initiative.',
      'What metrics should a 10-person startup track in its first year of operation?',
      'Create a measurement framework for evaluating AI-generated code quality.',
      'Suggest leading indicators for customer churn in a subscription SaaS product.',
    ],
  },
  {
    label: '🤔 Competitive & market',
    prompts: [
      'Outline a competitive analysis framework for a new entry into the AI productivity market.',
      'What positioning strategy would differentiate a privacy-first AI assistant from OpenAI offerings?',
      'Identify the top 5 risks of entering the enterprise data-platform market in 2026.',
    ],
  },
];

export default function StrategyScreen() {
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
        <Text style={[styles.title, { color: colors.foreground }]}>🗺️ Strategy</Text>
        <Text style={[styles.subtitle, { color: colors.mutedForeground }]}>
          Use Concierge as your strategic thinking partner. Apply frameworks, build roadmaps, analyse decisions, and define the metrics that matter.
        </Text>
      </View>

      {/* Framework cards */}
      <View style={[styles.groupDivider, { borderBottomColor: colors.border }]}>
        <Text style={[styles.groupLabel, { color: colors.mutedForeground }]}>Supported frameworks</Text>
      </View>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.frameworkRow}
        style={styles.frameworkScroll}
      >
        {FRAMEWORKS.map(({ name, full, desc, color }) => (
          <View
            key={name}
            style={[styles.frameworkCard, { backgroundColor: colors.card, borderColor: `${color}40` }]}
          >
            <Text style={[styles.frameworkName, { color }]}>{name}</Text>
            <Text style={[styles.frameworkFull, { color: colors.mutedForeground }]}>{full}</Text>
            <Text style={[styles.frameworkDesc, { color: colors.foreground }]}>{desc}</Text>
          </View>
        ))}
      </ScrollView>

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
  frameworkScroll: { marginBottom: 8 },
  frameworkRow: { gap: 10, paddingVertical: 10 },
  frameworkCard: {
    width: 200,
    borderRadius: 12,
    borderWidth: 1,
    padding: 14,
    gap: 4,
  },
  frameworkName: { fontSize: 15, fontFamily: 'Inter_700Bold' },
  frameworkFull: { fontSize: 11, fontFamily: 'Inter_400Regular', lineHeight: 16 },
  frameworkDesc: { fontSize: 12, fontFamily: 'Inter_400Regular', lineHeight: 18, marginTop: 4 },
  group: { marginBottom: 20 },
  groupDivider: { borderBottomWidth: 1, paddingBottom: 8, marginBottom: 10 },
  groupLabel: {
    fontSize: 12,
    fontFamily: 'Inter_700Bold',
    textTransform: 'uppercase',
    letterSpacing: 0.7,
  },
});
