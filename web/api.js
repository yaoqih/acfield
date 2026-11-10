export async function api(url, data, {timeout = data === undefined ? 8000 : 30000} = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, {
      cache: 'no-store', signal: controller.signal,
      ...(data === undefined ? {} : {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data),
      }),
    });
    const result = await response.json();
    if (!response.ok) throw Error(result.error || '操作失败，请重试');
    return result;
  } catch (error) {
    if (controller.signal.aborted) throw Error(data === undefined
      ? '读取超时，请检查服务连接后重试' : '等待响应超时，请先查看实验事件确认执行结果');
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

export function healthy(state) {
  return state.status === 'running' && state.state_age_ms != null && state.state_age_ms < 500
    && state.frame_age_ms != null && state.frame_age_ms < 500;
}

export function normalizeState(state) {
  if (healthy(state)) return state;
  return {...state, tags: (state.tags || []).map(tag => ({
    ...tag, status: 'lost', speed_px_s: null, speed_m_s: null,
  }))};
}

// One request at a time; a stalled request expires and polling can recover automatically.
export function pollState(onState) {
  let previous = {};
  async function poll() {
    let snapshot;
    try {
      previous = await api('/api/state', undefined, {timeout: 1500});
      snapshot = previous;
    } catch {
      snapshot = {...previous, status: 'offline',
        error: '无法连接本地识别服务，请检查终端中的程序是否运行。'};
    }
    try { onState(normalizeState(snapshot)); }
    finally {
      setTimeout(poll, 200);
    }
  }
  poll();
}
