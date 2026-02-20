import { useEffect, useState } from 'react';
import { loadPipelines } from '../services/api';
import { useApp } from '../context/AppContext';
import { X, Database, Globe, ChevronRight, Inbox, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

export default function ExistingSitesModal({ open, onClose, onSelect }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const { pipelines, setPipelines } = useApp();

    useEffect(() => {
        if (open) fetchPipelines();
    }, [open]);

    const fetchPipelines = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await loadPipelines();
            setPipelines(data);
        } catch (err) {
            setError(err.message);
            toast.error('Falha ao carregar sites: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    if (!open) return null;

    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="modal-box glass-frosted gradient-border modal-enter">
                <div className="modal-header">
                    <h2 className="modal-title">
                        <div className="modal-title-icon" style={{ background: 'linear-gradient(135deg, #8b5cf6, #3b82f6)' }}>
                            <Database size={16} />
                        </div>
                        Sites Processados
                    </h2>
                    <button className="modal-close" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <p className="modal-desc">Selecione um site já processado para iniciar uma conversa.</p>

                <div className="pipelines-list">
                    {loading && (
                        <div className="pipelines-loading">
                            <div className="spinner" />
                            Carregando bases...
                        </div>
                    )}

                    {!loading && error && (
                        <div className="pipelines-empty">
                            <div className="empty-icon" style={{ background: 'linear-gradient(135deg, rgba(239,68,68,0.1), rgba(239,68,68,0.05))' }}>
                                <AlertCircle size={28} style={{ color: 'rgba(239,68,68,0.7)' }} />
                            </div>
                            <p className="empty-title" style={{ color: '#fca5a5' }}>Erro ao carregar</p>
                            <p className="empty-desc">{error}</p>
                        </div>
                    )}

                    {!loading && !error && pipelines.length === 0 && (
                        <div className="pipelines-empty">
                            <div className="empty-icon">
                                <Inbox size={28} style={{ color: 'rgba(139,92,246,0.6)' }} />
                            </div>
                            <p className="empty-title">Nenhuma base processada</p>
                            <p className="empty-desc">Processe um site para criar sua primeira base de conhecimento</p>
                        </div>
                    )}

                    {!loading && !error && pipelines.map((p, idx) => (
                        <div
                            key={idx}
                            className="pipeline-item"
                            onClick={() => { onSelect(p); onClose(); }}
                        >
                            <div className="pipeline-item-left">
                                <div className="pipeline-item-icon">
                                    <Globe size={16} />
                                </div>
                                <div>
                                    <div className="pipeline-item-url">{p.url_inferido}</div>
                                    <div className="pipeline-item-count">{p.total_faqs} FAQs disponíveis</div>
                                </div>
                            </div>
                            <ChevronRight size={16} className="pipeline-item-arrow" />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
