/**
 * Job service — distributed Celery job submission and polling.
 *
 * Endpoints:
 *   POST /api/v1/jobs/run_agent     — agent orchestration job
 *   POST /api/v1/jobs/run_plugin    — plugin execution job
 *   POST /api/v1/jobs/process_file  — workstation file processing job
 *   GET  /api/v1/jobs/:jobId        — poll status / result
 */
import apiClient from './client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type JobState = 'queued' | 'running' | 'completed' | 'failed' | 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE';

export interface JobStatus {
  job_id: string;
  state: string;
  status: JobState;
  result?: unknown;
  error?: string;
}

export interface JobAccepted {
  status: 'accepted';
  job_id: string;
  type: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// Submission helpers
// ---------------------------------------------------------------------------

/**
 * Enqueue an agent orchestration job.
 */
export async function submitAgentJob(goal: string, context = ''): Promise<JobAccepted> {
  const { data } = await apiClient.post<{ data: JobAccepted }>('/jobs/run_agent', {
    goal,
    context,
  });
  return data.data;
}

/**
 * Enqueue a plugin execution job.
 */
export async function submitPluginJob(
  pluginName: string,
  inputData: Record<string, unknown> = {},
): Promise<JobAccepted> {
  const { data } = await apiClient.post<{ data: JobAccepted }>('/jobs/run_plugin', {
    plugin_name: pluginName,
    input_data: inputData,
  });
  return data.data;
}

/**
 * Enqueue a workstation file-processing job.
 */
export async function submitFileJob(
  uploadId: string,
  filename: string,
  taskType: 'read_file' | 'dataset_analysis' | 'generate_code' = 'read_file',
  extra?: Record<string, unknown>,
): Promise<JobAccepted> {
  const { data } = await apiClient.post<{ data: JobAccepted }>('/jobs/process_file', {
    upload_id: uploadId,
    filename,
    task_type: taskType,
    extra: extra ?? null,
  });
  return data.data;
}

// ---------------------------------------------------------------------------
// Polling
// ---------------------------------------------------------------------------

/**
 * Fetch the current status of a Celery job.
 */
export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const { data } = await apiClient.get<{ data: JobStatus }>(`/jobs/${encodeURIComponent(jobId)}`);
  return data.data;
}

/**
 * Poll a job until it reaches a terminal state (completed or failed).
 * Resolves with the final JobStatus.
 *
 * @param jobId        Celery task UUID
 * @param intervalMs   Polling interval in milliseconds (default 3000)
 * @param timeoutMs    Maximum wait time before rejection (default 5 minutes)
 */
export function pollUntilDone(
  jobId: string,
  intervalMs = 3000,
  timeoutMs = 300_000,
): Promise<JobStatus> {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;
    const tick = async () => {
      try {
        const status = await getJobStatus(jobId);
        const terminal = status.status === 'completed' || status.status === 'failed'
          || status.state === 'SUCCESS' || status.state === 'FAILURE';
        if (terminal) {
          resolve(status);
          return;
        }
        if (Date.now() >= deadline) {
          reject(new Error(`Job ${jobId} timed out after ${timeoutMs}ms`));
          return;
        }
        setTimeout(tick, intervalMs);
      } catch (err) {
        reject(err);
      }
    };
    tick();
  });
}
