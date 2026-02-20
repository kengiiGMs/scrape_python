const API_BASE = 'http://localhost:3000';

export async function startPipeline(url, table, clear = false) {
    const response = await fetch(`${API_BASE}/api/pipeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, table, clear }),
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
        throw new Error(data.detail || data.message || 'Erro no pipeline');
    }
    return data;
}

export async function sendChat(message, ID_Conta) {
    const response = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, ID_Conta }),
    });
    const data = await response.json();
    if (!response.ok || !data.success) {
        throw new Error(data.detail || 'Erro no chat');
    }
    return data;
}

export async function loadPipelines() {
    const response = await fetch(`${API_BASE}/api/pipelines`);
    const data = await response.json();
    if (!data.success) {
        throw new Error('Falha ao carregar pipelines');
    }
    return data.data || [];
}
