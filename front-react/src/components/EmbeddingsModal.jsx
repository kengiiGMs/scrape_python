import { useState } from 'react';
import { useApp } from '../context/AppContext';
import { X, Layers } from 'lucide-react';
import toast from 'react-hot-toast';

export default function EmbeddingsModal({ open, onClose }) {
    const { currentIdConta, currentTable, setCurrentTable, tables, addTable } = useApp();
    const [newTable, setNewTable] = useState('');

    const handleAdd = () => {
        const name = newTable.trim().replace(/[^a-zA-Z0-9_]/g, '');
        if (!name) return;
        if (tables.includes(name)) {
            toast('Tabela já existe', { icon: 'ℹ️' });
            return;
        }
        addTable(name);
        setNewTable('');
        toast.success(`Tabela "${name}" adicionada`);
    };

    if (!open) return null;

    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="modal-box modal-sm glass-frosted gradient-border modal-enter">
                <div className="modal-header">
                    <h2 className="modal-title">
                        <div className="modal-title-icon" style={{ background: 'linear-gradient(135deg, #8b5cf6, #ef4444)' }}>
                            <Layers size={14} />
                        </div>
                        Embeddings
                    </h2>
                    <button className="modal-close" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <div className="embed-section">
                    <label className="embed-label">ID Conta Ativo</label>
                    <div className="embed-value">{currentIdConta || '—'}</div>
                </div>

                <div className="embed-section">
                    <label className="embed-label">Tabela de Embeddings</label>
                    <div className="embed-tables">
                        {tables.map(t => (
                            <div
                                key={t}
                                className={`table-item ${t === currentTable ? 'active' : ''}`}
                                onClick={() => {
                                    if (t !== currentTable) {
                                        setCurrentTable(t);
                                        toast.success(`Tabela alterada para ${t}`);
                                    }
                                }}
                            >
                                <div className={`table-dot ${t === currentTable ? 'active' : ''}`} />
                                <span className="table-name">{t}</span>
                                <span className="table-badge">{t === currentTable ? 'ativo' : 'selecionar'}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="embed-section">
                    <label className="embed-label">Adicionar Tabela</label>
                    <div className="embed-add-row">
                        <input
                            type="text"
                            value={newTable}
                            onChange={(e) => setNewTable(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
                            placeholder="nome_da_tabela"
                            className="embed-input"
                        />
                        <button className="btn-primary embed-add-btn" onClick={handleAdd}>
                            Adicionar
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
