import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Platform,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Animated, { FadeIn } from 'react-native-reanimated';

import { useColors } from '@/hooks/useColors';
import { Task, fetchTasks } from '@/lib/api';

type StatusKey = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILURE' | 'KILLED' | string;

function statusColor(status: StatusKey, colors: ReturnType<typeof useColors>): string {
  const s = status?.toUpperCase?.() ?? '';
  if (s === 'RUNNING' || s === 'STARTED') return colors.taskRunning;
  if (s === 'SUCCESS' || s === 'COMPLETED' || s === 'DONE') return colors.taskSuccess;
  if (s === 'FAILURE' || s === 'FAILED' || s === 'ERROR' || s === 'KILLED') return colors.taskFailed;
  return colors.taskPending;
}

function statusIcon(status: StatusKey): keyof typeof Ionicons.glyphMap {
  const s = status?.toUpperCase?.() ?? '';
  if (s === 'RUNNING' || s === 'STARTED') return 'pulse-outline';
  if (s === 'SUCCESS' || s === 'COMPLETED' || s === 'DONE') return 'checkmark-circle';
  if (s === 'FAILURE' || s === 'FAILED' || s === 'ERROR') return 'close-circle';
  if (s === 'KILLED') return 'stop-circle';
  return 'ellipse-outline';
}

function formatTime(ts?: string): string {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function TaskCard({ task, colors }: { task: Task; colors: ReturnType<typeof useColors> }) {
  const sColor = statusColor(task.status, colors);
  const sIcon = statusIcon(task.status);
  const id = task.task_id ?? task.id;
  const label = task.goal ?? task.description ?? task.type ?? id;
  const shortId = id.length > 12 ? `${id.slice(0, 8)}…` : id;
  const isRunning = ['RUNNING', 'STARTED'].includes((task.status ?? '').toUpperCase());

  return (
    <Animated.View entering={FadeIn.duration(300)}>
      <View style={[styles.card, { backgroundColor: colors.card, borderColor: colors.border }]}>
        <View style={styles.cardHeader}>
          <View style={[styles.statusDot, { backgroundColor: sColor }]}>
            <Ionicons name={sIcon} size={14} color="#fff" />
          </View>
          <View style={styles.cardMeta}>
            <Text style={[styles.taskLabel, { color: colors.foreground }]} numberOfLines={2}>
              {label}
            </Text>
            <View style={styles.cardFooter}>
              <Text style={[styles.taskId, { color: colors.mutedForeground }]}>{shortId}</Text>
              {task.created_at && (
                <Text style={[styles.taskTime, { color: colors.mutedForeground }]}>
                  {formatTime(task.created_at)}
                </Text>
              )}
            </View>
          </View>
          <View style={[styles.statusBadge, { backgroundColor: `${sColor}20` }]}>
            <Text style={[styles.statusText, { color: sColor }]}>
              {(task.status ?? 'UNKNOWN').toUpperCase()}
            </Text>
          </View>
        </View>
        {isRunning && task.progress !== undefined && (
          <View style={styles.progressRow}>
            <View style={[styles.progressTrack, { backgroundColor: colors.border }]}>
              <View
                style={[
                  styles.progressFill,
                  { backgroundColor: sColor, width: `${Math.min(100, task.progress ?? 0)}%` },
                ]}
              />
            </View>
            <Text style={[styles.progressText, { color: colors.mutedForeground }]}>
              {Math.round(task.progress ?? 0)}%
            </Text>
          </View>
        )}
      </View>
    </Animated.View>
  );
}

function EmptyTasks({ colors, onRefresh }: { colors: ReturnType<typeof useColors>; onRefresh: () => void }) {
  return (
    <View style={styles.emptyContainer}>
      <View style={[styles.emptyIcon, { backgroundColor: colors.card, borderColor: colors.border }]}>
        <Ionicons name="layers-outline" size={32} color={colors.mutedForeground} />
      </View>
      <Text style={[styles.emptyTitle, { color: colors.foreground }]}>No Tasks Yet</Text>
      <Text style={[styles.emptySubtitle, { color: colors.mutedForeground }]}>
        Tasks submitted via chat will appear here.{'\n'}Pull down to refresh.
      </Text>
      <Pressable
        onPress={onRefresh}
        style={({ pressed }) => [
          styles.refreshBtn,
          { backgroundColor: colors.primary, opacity: pressed ? 0.75 : 1 },
        ]}
      >
        <Ionicons name="refresh" size={16} color="#fff" />
        <Text style={[styles.refreshBtnText, { color: '#fff' }]}>Refresh</Text>
      </Pressable>
    </View>
  );
}

export default function TasksScreen() {
  const colors = useColors();
  const insets = useSafeAreaInsets();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadTasks = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    setError(null);
    try {
      const data = await fetchTasks();
      const sorted = [...data].sort((a, b) => {
        const ta = a.created_at ?? '';
        const tb = b.created_at ?? '';
        return tb.localeCompare(ta);
      });
      setTasks(sorted);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();
    pollRef.current = setInterval(() => loadTasks(), 8000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [loadTasks]);

  const handleRefresh = useCallback(() => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    loadTasks(true);
  }, [loadTasks]);

  const webTopInset = Platform.OS === 'web' ? 67 : 0;

  const runningCount = tasks.filter(
    (t) => ['RUNNING', 'STARTED'].includes((t.status ?? '').toUpperCase())
  ).length;

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={[styles.header, {
        paddingTop: Platform.OS === 'web' ? webTopInset : insets.top,
        backgroundColor: colors.background,
        borderBottomColor: colors.border,
      }]}>
        <View style={styles.headerLeft}>
          <Text style={[styles.headerTitle, { color: colors.foreground }]}>Tasks</Text>
          {runningCount > 0 && (
            <View style={[styles.runningBadge, { backgroundColor: colors.taskRunning }]}>
              <Text style={styles.runningBadgeText}>{runningCount} running</Text>
            </View>
          )}
        </View>
        <Pressable
          onPress={handleRefresh}
          style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}
          testID="refresh-tasks-button"
        >
          <Ionicons name="refresh-outline" size={22} color={colors.primary} />
        </Pressable>
      </View>

      {loading && !refreshing ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={[styles.loadingText, { color: colors.mutedForeground }]}>
            Loading tasks…
          </Text>
        </View>
      ) : error ? (
        <View style={styles.errorContainer}>
          <View style={[styles.emptyIcon, { backgroundColor: '#FEF2F2', borderColor: colors.destructive }]}>
            <Ionicons name="warning-outline" size={28} color={colors.destructive} />
          </View>
          <Text style={[styles.errorTitle, { color: colors.destructive }]}>Connection Error</Text>
          <Text style={[styles.errorSubtitle, { color: colors.mutedForeground }]}>{error}</Text>
          <Pressable
            onPress={() => loadTasks()}
            style={({ pressed }) => [
              styles.refreshBtn,
              { backgroundColor: colors.primary, opacity: pressed ? 0.75 : 1 },
            ]}
          >
            <Ionicons name="refresh" size={16} color="#fff" />
            <Text style={[styles.refreshBtnText, { color: '#fff' }]}>Retry</Text>
          </Pressable>
        </View>
      ) : (
        <FlatList
          data={tasks}
          keyExtractor={(item) => item.task_id ?? item.id}
          renderItem={({ item }) => <TaskCard task={item} colors={colors} />}
          ListEmptyComponent={<EmptyTasks colors={colors} onRefresh={handleRefresh} />}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handleRefresh}
              tintColor={colors.primary}
              colors={[colors.primary]}
            />
          }
          contentContainerStyle={[
            styles.listContent,
            {
              paddingBottom: Platform.OS === 'web'
                ? 84 + 34
                : insets.bottom + 84,
            },
          ]}
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingBottom: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  headerTitle: {
    fontSize: 22,
    fontFamily: 'Inter_700Bold',
  },
  runningBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
  },
  runningBadgeText: {
    fontSize: 11,
    fontFamily: 'Inter_600SemiBold',
    color: '#fff',
  },
  listContent: {
    paddingHorizontal: 16,
    paddingTop: 12,
    flexGrow: 1,
  },
  card: {
    borderRadius: 14,
    borderWidth: 1,
    padding: 14,
    marginBottom: 10,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
  },
  statusDot: {
    width: 28,
    height: 28,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 2,
    flexShrink: 0,
  },
  cardMeta: {
    flex: 1,
    gap: 4,
  },
  taskLabel: {
    fontSize: 14,
    fontFamily: 'Inter_500Medium',
    lineHeight: 20,
  },
  cardFooter: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'center',
  },
  taskId: {
    fontSize: 11,
    fontFamily: 'Inter_400Regular',
  },
  taskTime: {
    fontSize: 11,
    fontFamily: 'Inter_400Regular',
  },
  statusBadge: {
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: 6,
    flexShrink: 0,
  },
  statusText: {
    fontSize: 10,
    fontFamily: 'Inter_700Bold',
    letterSpacing: 0.5,
  },
  progressRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 10,
  },
  progressTrack: {
    flex: 1,
    height: 4,
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressFill: {
    height: 4,
    borderRadius: 2,
  },
  progressText: {
    fontSize: 11,
    fontFamily: 'Inter_500Medium',
    width: 32,
    textAlign: 'right',
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 14,
    fontFamily: 'Inter_400Regular',
  },
  errorContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    gap: 10,
  },
  errorTitle: {
    fontSize: 18,
    fontFamily: 'Inter_600SemiBold',
    marginTop: 4,
  },
  errorSubtitle: {
    fontSize: 14,
    fontFamily: 'Inter_400Regular',
    textAlign: 'center',
    lineHeight: 20,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    paddingVertical: 60,
    gap: 8,
  },
  emptyIcon: {
    width: 72,
    height: 72,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    marginBottom: 8,
  },
  emptyTitle: {
    fontSize: 20,
    fontFamily: 'Inter_600SemiBold',
  },
  emptySubtitle: {
    fontSize: 14,
    fontFamily: 'Inter_400Regular',
    textAlign: 'center',
    lineHeight: 20,
  },
  refreshBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 20,
    marginTop: 12,
  },
  refreshBtnText: {
    fontSize: 14,
    fontFamily: 'Inter_600SemiBold',
  },
});
