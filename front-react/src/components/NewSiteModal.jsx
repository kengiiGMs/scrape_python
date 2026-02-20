import { useState, useRef, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { startPipeline as apiStartPipeline } from '../services/api';
import { X, Link, Globe, Rocket } from 'lucide-react';
import toast from 'react-hot-toast';

export default function NewSiteModal({ open, onClose, onStartPipeline }) {
    const [url, setUrl] = useState('');
    const [loading, setLoading] = useState(false);
    const [shake, setShake] = useState(false);
    const inputRef = useRef(null);
    const { currentTable } = useApp();

    useEffect(() => {
        if (open) setTimeout(() => inputRef.current?.focus(), 300);
    }, [open]);

    const handleSubmit = async () => {
        if (!url.trim()) {
            setShake(true);
            setTimeout(() => setShake(false), 600);
            return;
        }

        setLoading(true);
        onClose();

        try {
            onStartPipeline(url.trim(), currentTable);
        } catch (err) {
            toast.error('Erro: ' + err.message);
            setLoading(false);
        }
    };

    if (!open) return null;

    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className={`modal-box glass-frosted gradient-border ${open ? 'modal-enter' : ''}`}>
                <div className="modal-header">
                    <h2 className="modal-title">
                        <div className="modal-title-icon">
                            <Link size={16} />
                        </div>
                        Analisar URL
                    </h2>
                    <button className="modal-close" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <p className="modal-desc">
                    Insira o link do site que deseja analisar. Nosso agente processará todo o conteúdo e criará uma base de conhecimento inteligente.
                </p>

                <div className="modal-body">
                    <div className="input-wrap">
                        <Globe size={16} className="input-icon" />
                        <input
                            ref={inputRef}
                            type="url"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                            placeholder="https://exemplo.com.br"
                            className={`modal-input ${shake ? 'shake' : ''}`}
                        />
                    </div>
                    <button
                        className="btn-primary modal-submit"
                        disabled={loading}
                        onClick={handleSubmit}
                    >
                        {loading ? (
                            <div className="spinner" />
                        ) : (
                            <Rocket size={16} />
                        )}
                        {loading ? 'Processando...' : 'Processar Site'}
                    </button>
                </div>
            </div>
        </div>
    );
}
