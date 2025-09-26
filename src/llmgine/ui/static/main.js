// Enhanced UI functionality with detailed feedback and status updates
const el = (id) => document.getElementById(id);
const statusEl = el('status');
const eventsContainer = el('events-container');
const metricsEl = el('metrics');
const metricsSummary = el('metrics-summary');
const statusMessages = el('status-messages');
const commandResults = el('command-results');

// State management
let events = [];
let commandHistory = [];

// Utility functions
function formatTime(timestamp) {
  return new Date(timestamp || Date.now()).toLocaleTimeString();
}

function formatJson(obj, maxLines = 3) {
  const str = JSON.stringify(obj, null, 2);
  const lines = str.split('\n');
  if (lines.length <= maxLines) return str;
  return lines.slice(0, maxLines).join('\n') + `\n... (${lines.length - maxLines} more lines)`;
}

function addStatusMessage(message, type = 'info', duration = 5000) {
  const div = document.createElement('div');
  div.className = `status-message ${type}`;
  div.textContent = `${formatTime()} - ${message}`;
  statusMessages.appendChild(div);

  setTimeout(() => {
    if (div.parentNode) div.parentNode.removeChild(div);
  }, duration);

  // Keep only last 10 messages
  while (statusMessages.children.length > 10) {
    statusMessages.removeChild(statusMessages.firstChild);
  }
}

function addCommandResult(command, result, success = true) {
  const div = document.createElement('div');
  div.className = 'command-result';

  const header = document.createElement('h4');
  header.textContent = `${command} - ${success ? 'SUCCESS' : 'FAILED'} (${formatTime()})`;
  div.appendChild(header);

  const details = document.createElement('pre');
  details.textContent = formatJson(result, 5);
  div.appendChild(details);

  commandResults.insertBefore(div, commandResults.firstChild);

  // Keep only last 20 results
  while (commandResults.children.length > 20) {
    commandResults.removeChild(commandResults.lastChild);
  }

  commandHistory.push({ command, result, success, timestamp: Date.now() });
}

function setButtonState(button, state) {
  button.classList.remove('loading', 'success', 'error');
  if (state !== 'normal') {
    button.classList.add(state);
    if (state === 'loading') {
      button.disabled = true;
    } else {
      setTimeout(() => {
        button.classList.remove(state);
        button.disabled = false;
      }, 2000);
    }
  } else {
    button.disabled = false;
  }
}

async function executeCommand(button, url, payload, commandName) {
  setButtonState(button, 'loading');
  try {
    const result = await post(url, payload);
    setButtonState(button, 'success');
    addCommandResult(commandName, result, true);
    addStatusMessage(`${commandName} executed successfully`, 'success');
    return result;
  } catch (error) {
    setButtonState(button, 'error');
    addCommandResult(commandName, { error: error.message }, false);
    addStatusMessage(`${commandName} failed: ${error.message}`, 'error');
    throw error;
  }
}

function addEvent(eventData) {
  const div = document.createElement('div');
  const eventType = eventData.event_type || 'Unknown';
  const isCommand = eventType.includes('Command');
  const isError = eventType.includes('Error') || eventType.includes('Failed');

  div.className = `event-item ${isCommand ? 'command' : 'event'} ${isError ? 'error' : ''}`;

  const header = document.createElement('div');
  header.className = 'event-header';

  const typeSpan = document.createElement('span');
  typeSpan.className = 'event-type';
  typeSpan.textContent = eventType;

  const timeSpan = document.createElement('span');
  timeSpan.className = 'event-time';
  timeSpan.textContent = formatTime(eventData.timestamp);

  header.appendChild(typeSpan);
  header.appendChild(timeSpan);
  div.appendChild(header);

  const details = document.createElement('div');
  details.className = 'event-details';
  details.innerHTML = `
    <div><strong>Session:</strong> ${eventData.session_id || 'BUS'}</div>
    <div><strong>ID:</strong> ${eventData.event_id || eventData.command_id || 'N/A'}</div>
  `;

  if (eventData.result) {
    details.innerHTML += `<div><strong>Result:</strong> ${JSON.stringify(eventData.result)}</div>`;
  }
  if (eventData.error) {
    details.innerHTML += `<div><strong>Error:</strong> ${eventData.error}</div>`;
  }
  if (eventData.message) {
    details.innerHTML += `<div><strong>Message:</strong> ${eventData.message}</div>`;
  }

  div.appendChild(details);

  // Show content if available
  if (eventData.text || eventData.payload || eventData.count) {
    const contentDiv = document.createElement('div');
    contentDiv.className = 'event-content';
    const content = eventData.text || eventData.payload || `count: ${eventData.count}`;
    contentDiv.textContent = typeof content === 'string' ? content : JSON.stringify(content);
    div.appendChild(contentDiv);
  }

  events.unshift({ ...eventData, timestamp: Date.now() });
  eventsContainer.insertBefore(div, eventsContainer.firstChild);

  // Keep only last 100 events in UI
  while (eventsContainer.children.length > 100) {
    eventsContainer.removeChild(eventsContainer.lastChild);
    events.pop();
  }

  // Auto-scroll if enabled
  if (el('auto-scroll')?.checked) {
    div.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function updateMetricsSummary(metrics) {
  if (!metrics || !metrics.metrics) return;

  metricsSummary.innerHTML = '';

  const counters = metrics.metrics.counters || {};
  const gauges = metrics.metrics.gauges || {};
  const stats = metrics.stats || {};

  // Key metrics cards
  const keyMetrics = [
    { title: 'Bus Status', value: stats.running ? 'RUNNING' : 'STOPPED', type: stats.running ? 'success' : 'error' },
    { title: 'Commands Sent', value: counters.commands_sent_total?.value || 0, type: 'success' },
    { title: 'Events Published', value: counters.events_published_total?.value || 0, type: 'success' },
    { title: 'Queue Size', value: gauges.queue_size?.value || 0, type: 'success' },
    { title: 'Total Errors', value: stats.total_errors || 0, type: stats.total_errors > 0 ? 'error' : 'success' },
    { title: 'Active Sessions', value: gauges.active_sessions?.value || 0, type: 'success' },
  ];

  if (metrics.bus_kind === 'resilient') {
    keyMetrics.push(
      { title: 'Backpressure', value: gauges.backpressure_active?.value ? 'ACTIVE' : 'INACTIVE', type: gauges.backpressure_active?.value ? 'warning' : 'success' },
      { title: 'DLQ Size', value: metrics.dead_letter_queue_size || 0, type: metrics.dead_letter_queue_size > 0 ? 'warning' : 'success' }
    );
  }

  keyMetrics.forEach(metric => {
    const card = document.createElement('div');
    card.className = `metric-card ${metric.type}`;
    card.innerHTML = `
      <h4>${metric.title}</h4>
      <div class="value">${metric.value}</div>
    `;
    metricsSummary.appendChild(card);
  });
}

async function post(url, payload) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {})
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`HTTP ${r.status}: ${text}`);
  }
  return r.json();
}

async function refreshMetrics() {
  try {
    const metrics = await fetch('/api/metrics').then(r => r.json());
    metricsEl.textContent = JSON.stringify(metrics, null, 2);
    updateMetricsSummary(metrics);
  } catch (error) {
    addStatusMessage(`Failed to refresh metrics: ${error.message}`, 'error');
  }
}

function connectWS() {
  const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${wsProto}://${location.host}/ws`);

  ws.onopen = () => {
    statusEl.textContent = 'Connected';
    addStatusMessage('WebSocket connected', 'success');
  };

  ws.onclose = () => {
    statusEl.textContent = 'Disconnected';
    addStatusMessage('WebSocket disconnected, reconnecting...', 'error');
    setTimeout(connectWS, 1500);
  };

  ws.onerror = () => {
    statusEl.textContent = 'Error';
    addStatusMessage('WebSocket error', 'error');
  };

  ws.onmessage = (msg) => {
    try {
      const { type, data } = JSON.parse(msg.data);
      if (type === 'event') {
        addEvent(data);
      } else if (type === 'snapshot') {
        metricsEl.textContent = JSON.stringify(data, null, 2);
        updateMetricsSummary(data);
      } else if (type === 'notice') {
        addStatusMessage(data.msg, 'info');
      }
    } catch(e) {
      console.warn('WebSocket message error:', e);
    }
  };
}

// Initialize WebSocket connection
connectWS();

// Bus Controls
el('start').onclick = () => executeCommand(
  el('start'),
  '/api/bus/start',
  {
    kind: el('bus-kind').value,
    queue_size: parseInt(el('queue-size').value || '10000', 10),
    backpressure: el('backpressure').value,
  },
  'Start Bus'
);

el('stop').onclick = () => executeCommand(el('stop'), '/api/bus/stop', {}, 'Stop Bus');
el('reset').onclick = () => executeCommand(el('reset'), '/api/bus/reset', {}, 'Reset Bus');

el('apply-batch').onclick = () => executeCommand(
  el('apply-batch'),
  '/api/bus/batch',
  {
    size: parseInt(el('batch-size').value || '10', 10),
    timeout: parseFloat(el('batch-timeout').value || '0.01'),
  },
  'Apply Batch Config'
);

// Middleware toggles
document.querySelectorAll('input[type=checkbox][data-mw]').forEach(cb => {
  cb.addEventListener('change', async () => {
    const name = cb.getAttribute('data-mw');
    const payload = { name, enabled: cb.checked };
    if (name === 'rate_limit') payload.max_per_second = parseFloat(el('mw-rate-pps').value || '10');

    try {
      await post('/api/mw', payload);
      addStatusMessage(`${name} middleware ${cb.checked ? 'enabled' : 'disabled'}`, 'success');
    } catch (error) {
      addStatusMessage(`Failed to toggle ${name} middleware: ${error.message}`, 'error');
      cb.checked = !cb.checked; // Revert checkbox
    }
  });
});

// Filters
el('add-debug-filter').onclick = () => executeCommand(el('add-debug-filter'), '/api/filters/pattern', {}, 'Add Debug Filter');
el('add-session-filter').onclick = () => executeCommand(el('add-session-filter'), '/api/filters/session', { include: ['BUS'] }, 'Add Session Filter');
el('add-type-filter').onclick = () => executeCommand(el('add-type-filter'), '/api/filters/type', { include: ['LogEvent'] }, 'Add Type Filter');
el('add-pattern-filter').onclick = () => executeCommand(el('add-pattern-filter'), '/api/filters/pattern', { include: ['.*ResultEvent'] }, 'Add Pattern Filter');

// Playground Commands
el('btn-echo').onclick = () => executeCommand(
  el('btn-echo'),
  '/api/commands/echo',
  { text: el('echo-text').value, session: el('pg-session').value || null },
  'EchoCommand'
);

el('btn-fail').onclick = () => executeCommand(
  el('btn-fail'),
  '/api/commands/fail',
  { message: el('fail-msg').value, raise_exception: true, session: el('pg-session').value || null },
  'FailingCommand'
);

el('btn-sleep').onclick = () => executeCommand(
  el('btn-sleep'),
  '/api/commands/sleep',
  { seconds: parseFloat(el('sleep-sec').value || '0.25'), session: el('pg-session').value || null },
  'SleepCommand'
);

el('btn-gen').onclick = () => executeCommand(
  el('btn-gen'),
  '/api/commands/generate',
  {
    count: parseInt(el('gen-count').value || '100', 10),
    delay_ms: parseInt(el('gen-delay').value || '0', 10),
    payload: 'ping',
    session: el('pg-session').value || null
  },
  'GenerateEventsCommand'
);

el('btn-evt').onclick = () => executeCommand(
  el('btn-evt'),
  '/api/events/log',
  { message: el('evt-msg').value, session: el('pg-session').value || null },
  'Publish LogEvent'
);

el('btn-sched').onclick = () => executeCommand(
  el('btn-sched'),
  '/api/events/schedule_ping',
  { in_seconds: parseFloat(el('sched-sec').value || '3'), session: el('pg-session').value || null },
  'Schedule Ping'
);

el('btn-fire').onclick = () => executeCommand(
  el('btn-fire'),
  '/api/loadgen/start',
  {
    rps: parseFloat(el('fire-rps').value || '200'),
    duration_s: parseFloat(el('fire-dur').value || '10'),
    prefix: el('fire-prefix').value || 'firehose',
    session: el('pg-session').value || null
  },
  'Start Firehose'
);

// Event controls
el('clear-events').onclick = () => {
  eventsContainer.innerHTML = '';
  events = [];
  addStatusMessage('Events cleared', 'info');
};

el('refresh-metrics').onclick = refreshMetrics;

// Auto-refresh metrics every 5 seconds
setInterval(refreshMetrics, 5000);