import { useState } from 'react';
import { Bot, Zap, Database, Brain, Globe, TrendingUp } from 'lucide-react';
import FeatureCard from '../components/FeatureCard';
import NewSiteModal from '../components/NewSiteModal';
import ExistingSitesModal from '../components/ExistingSitesModal';

const FEATURES = [
    {
        icon: Brain,
        title: 'Inteligência Contextual',
        description: 'Entende gírias, áudios e intenções complexas. Não é apenas um bot de palavras-chave.',
    },
    {
        icon: Zap,
        title: 'Setup em 5min',
        description: 'Sem código. Conecte seu WhatsApp e suba seu PDF. Pronto.',
    },
    {
        icon: Globe,
        title: 'Multilíngue Nativo',
        description: 'Atende em Português, Inglês e Espanhol com fluência nativa.',
    },
    {
        icon: TrendingUp,
        title: 'Escala Infinita',
        description: 'Atende milhares de conversas simultâneas. Sem gargalos humanos.',
    },
];

export default function LandingPage({ onStartPipeline, onSelectPipeline }) {
    const [newModalOpen, setNewModalOpen] = useState(false);
    const [existingModalOpen, setExistingModalOpen] = useState(false);

    return (
        <>
            <div className="landing-page">
                <div className="landing-content">
                    {/* Hero */}
                    <div className="hero-section">
                        <div className="hero-logo animate-float">
                            <div className="hero-logo-inner animate-glow">
                                <Bot size={40} />
                            </div>
                        </div>

                        <h1 className="hero-title animate-gradient">
                            Não é um bot. É uma operação.
                        </h1>
                        <p className="hero-subtitle">
                            Esqueça fluxogramas complexos. O MASA aprende sobre seu produto e vende por você.
                        </p>

                        <div className="hero-buttons">
                            <button className="btn-primary hero-btn" onClick={() => setNewModalOpen(true)}>
                                <Zap size={20} />
                                Novo Site
                            </button>
                            <button className="btn-glass hero-btn" onClick={() => setExistingModalOpen(true)}>
                                <Database size={20} />
                                Sites Processados
                            </button>
                        </div>
                    </div>

                    {/* Feature Cards */}
                    <div className="features-grid">
                        {FEATURES.map((f, i) => (
                            <FeatureCard key={i} {...f} />
                        ))}
                    </div>
                </div>
            </div>

            <NewSiteModal
                open={newModalOpen}
                onClose={() => setNewModalOpen(false)}
                onStartPipeline={onStartPipeline}
            />
            <ExistingSitesModal
                open={existingModalOpen}
                onClose={() => setExistingModalOpen(false)}
                onSelect={onSelectPipeline}
            />
        </>
    );
}
