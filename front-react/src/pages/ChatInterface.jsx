import { useState, useRef, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { sendChat } from '../services/api';
import { renderMarkdown } from '../utils/markdown';
import EmbeddingsModal from '../components/EmbeddingsModal';
import { Bot, User, Send, RefreshCw, Layers } from 'lucide-react';

export default function ChatInterface({ onReset }) {
    const { currentIdConta, currentUrl, currentTable } = useApp();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [sending, setSending] = useState(false);
    const [embedOpen, setEmbedOpen] = useState(false);
    const messagesRef = useRef(null);
    const inputRef = useRef(null);

    // Initial messages on mount
    useEffect(() => {
        if (currentUrl) {
            setMessages([
                { type: 'system', text: `Agente pronto! Analisei todo o conteúdo de ${currentUrl}` },
            ]);
            setTimeout(() => {
                setMessages(prev => [...prev, {
                    type: 'bot',
                    text: 'Olá! Eu processei o site com sucesso e já entendo todo o contexto, serviços e informações disponíveis. Como posso te ajudar?',
                }]);
            }, 500);
            setTimeout(() => inputRef.current?.focus(), 600);
        }
    }, [currentUrl]);

    // Auto-scroll
    useEffect(() => {
        if (messagesRef.current) {
            messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = async () => {
        const msg = input.trim();
        if (!msg || !currentIdConta) return;

        setMessages(prev => [...prev, { type: 'user', text: msg }]);
        setInput('');
        setSending(true);
        setMessages(prev => [...prev, { type: 'typing' }]);

        try {
            const data = await sendChat(msg, currentIdConta);
            setMessages(prev => {
                const filtered = prev.filter(m => m.type !== 'typing');
                return [...filtered, { type: 'bot', text: data.data.reply || 'Sem resposta do agente' }];
            });
        } catch (error) {
            setMessages(prev => {
                const filtered = prev.filter(m => m.type !== 'typing');
                return [...filtered, { type: 'system', text: 'Erro: ' + error.message }];
            });
        } finally {
            setSending(false);
            inputRef.current?.focus();
        }
    };

    return (
        <>
            <div className="chat-container">
                <div className="chat-card glass-strong gradient-border glow-multi">
                    {/* Header */}
                    <div className="chat-header glass-crystal">
                        <div className="chat-header-left">
                            <div className="chat-avatar">
                                <Bot size={24} />
                            </div>
                            <div>
                                <h4 className="chat-agent-name">Agente Conversacional</h4>
                                <div className="chat-status">
                                    <span className="chat-status-dot" />
                                    <span className="chat-status-text">{currentUrl || 'conectado'}</span>
                                </div>
                            </div>
                        </div>
                        <div className="chat-header-right">
                            <button className="embed-badge" onClick={() => setEmbedOpen(true)}>
                                <Layers size={14} />
                                <span>{currentTable}</span>
                            </button>
                            <button className="btn-ghost" onClick={onReset}>
                                <RefreshCw size={14} />
                                Novo Site
                            </button>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="chat-messages" ref={messagesRef}>
                        {messages.map((msg, i) => {
                            if (msg.type === 'system') {
                                return (
                                    <div key={i} className="chat-system animate-slide-down">
                                        <span>{msg.text}</span>
                                    </div>
                                );
                            }
                            if (msg.type === 'user') {
                                return (
                                    <div key={i} className="chat-bubble-row user animate-slide-up">
                                        <div className="chat-user-avatar">
                                            <User size={16} />
                                        </div>
                                        <div className="bubble-user">{msg.text}</div>
                                    </div>
                                );
                            }
                            if (msg.type === 'bot') {
                                return (
                                    <div key={i} className="chat-bubble-row bot animate-slide-up">
                                        <div className="chat-bot-avatar">
                                            <Bot size={16} />
                                        </div>
                                        <div
                                            className="bot-msg bubble-bot"
                                            dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }}
                                        />
                                    </div>
                                );
                            }
                            if (msg.type === 'typing') {
                                return (
                                    <div key={i} className="chat-bubble-row bot animate-slide-up">
                                        <div className="chat-bot-avatar">
                                            <Bot size={16} />
                                        </div>
                                        <div className="bubble-bot typing-bubble">
                                            <div className="typing-dot" />
                                            <div className="typing-dot" />
                                            <div className="typing-dot" />
                                        </div>
                                    </div>
                                );
                            }
                            return null;
                        })}
                    </div>

                    {/* Input */}
                    <div className="chat-input-bar glass-crystal">
                        <div className="chat-input-wrap">
                            <input
                                ref={inputRef}
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && !sending && handleSend()}
                                placeholder="Pergunte qualquer coisa sobre o site..."
                                disabled={sending}
                            />
                            <button
                                className="btn-primary chat-send-btn"
                                onClick={handleSend}
                                disabled={sending || !input.trim()}
                            >
                                <Send size={16} />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <EmbeddingsModal open={embedOpen} onClose={() => setEmbedOpen(false)} />
        </>
    );
}
