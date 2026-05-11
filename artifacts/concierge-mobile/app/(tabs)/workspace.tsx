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

const FILE_TYPES = [
  { ext: '.txt', label: 'Plain text', color: '#6B7280' },
  { ext: '.csv', label: 'CSV / spreadsheet', color: '#059669' },
  { ext: '.json', label: 'JSON data', color: '#0891B2' },
  { ext: '.pdf', label: 'PDF document', color: '#DC2626' },
  { ext: '.docx', label: 'Word document', color: '#2563EB' },
  { ext: '.png/.jpg', label: 'Images', color: '#9333EA' },
  { ext: '.mp3/.wav', label: 'Audio (Whisper)', color: '#D97706' },
  { ext: '.mp4/.mov', label: 'Video (metadata)', color: '#BE185D' },
];

const UPLOAD_STEPS = [
  { n: '1', t: 'Tap 📎 in the chat input', d: 'A file picker appears. Select any supported file type.' },
  { n: '2', t: 'Select your file', d: 'Up to 50 MB. Text is extracted automatically.' },
  { n: '3', t: 'Send your message', d: 'A reference is prepended so the AI can use the file content.' },
  { n: '4', t: 'Attach to a project (optional)', d: 'Provide a project_id to group the file with related work.' },
];

const PROMPT_GROUPS = [
  {
    label: '📄 Document analysis',
    prompts: [
      'I uploaded a PDF spec — summarise the authentication requirements.',
      'Read the uploaded DOCX and extract all action items.',
      'Scan the uploaded requirements doc and flag any ambiguities.',
      'Compare the two uploaded specs and list the differences.',
    ],
  },
  {
    label: '📊 Data & CSVs',
    prompts: [
      'Analyse the uploaded CSV and give me a summary table of numeric columns.',
      'What are the top 10 rows by revenue in the uploaded sales file?',
      'Detect any missing values or obvious data-quality issues in the CSV.',
      'Generate a Python script to visualise the data in the uploaded CSV.',
    ],
  },
  {
    label: '🗂️ Projects & organisation',
    prompts: [
      'Create a project called "Q3 Product Launch" — attach the brief I uploaded.',
      'List all files attached to the current project.',
      'What projects exist? Show names and file counts.',
      'Generate an image for the project logo.',
    ],
  },
  {
    label: '🖼️ Images & media',
    prompts: [
      'I uploaded a UI screenshot — describe the layout and suggest UX improvements.',
      'What metadata was extracted from the uploaded image?',
      'Transcribe the audio file I just uploaded.',
      'Create an image of a friendly robot greeting me.',
    ],
  },
];

export default function WorkspaceScreen() {
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
        <Text style={[styles.title, { color: colors.foreground }]}>📁 Workspace</Text>
        <Text style={[styles.subtitle, { color: colors.mutedForeground }]}>
          Upload files, organise them into Projects, and give the AI direct access to your content. Tap 📎 in the chat to attach files mid-conversation.
        </Text>
      </View>

      {/* Upload guide */}
      <View style={[styles.uploadCard, { backgroundColor: colors.card, borderColor: colors.border }]}>
        <Text style={[styles.uploadTitle, { color: colors.primary }]}>How to upload a file</Text>
        {UPLOAD_STEPS.map(({ n, t, d }) => (
          <View key={n} style={styles.stepRow}>
            <View style={[styles.stepNum, { backgroundColor: colors.primary }]}>
              <Text style={styles.stepNumText}>{n}</Text>
            </View>
            <View style={styles.stepBody}>
              <Text style={[styles.stepTitle, { color: colors.foreground }]}>{t}</Text>
              <Text style={[styles.stepDesc, { color: colors.mutedForeground }]}>{d}</Text>
            </View>
          </View>
        ))}
      </View>

      {/* File types */}
      <View style={[styles.groupDivider, { borderBottomColor: colors.border }]}>
        <Text style={[styles.groupLabel, { color: colors.mutedForeground }]}>Allowed file types</Text>
      </View>
      <View style={styles.fileTypesGrid}>
        {FILE_TYPES.map(({ ext, label, color }) => (
          <View
            key={ext}
            style={[styles.fileTypeChip, { backgroundColor: `${color}14`, borderColor: `${color}40` }]}
          >
            <Text style={[styles.fileTypeExt, { color }]}>{ext}</Text>
            <Text style={[styles.fileTypeLabel, { color: colors.mutedForeground }]}>{label}</Text>
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
  uploadCard: {
    borderRadius: 14,
    borderWidth: 1,
    padding: 16,
    marginBottom: 24,
    gap: 14,
  },
  uploadTitle: { fontSize: 15, fontFamily: 'Inter_600SemiBold', marginBottom: 4 },
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
  fileTypesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 24,
  },
  fileTypeChip: {
    borderRadius: 8,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 8,
    gap: 2,
  },
  fileTypeExt: { fontSize: 12, fontFamily: 'Inter_700Bold' },
  fileTypeLabel: { fontSize: 11, fontFamily: 'Inter_400Regular' },
  group: { marginBottom: 20 },
  groupDivider: { borderBottomWidth: 1, paddingBottom: 8, marginBottom: 10 },
  groupLabel: {
    fontSize: 12,
    fontFamily: 'Inter_700Bold',
    textTransform: 'uppercase',
    letterSpacing: 0.7,
  },
});
