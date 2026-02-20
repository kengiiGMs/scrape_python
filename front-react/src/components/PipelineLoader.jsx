import { useState, useEffect, useRef, useCallback } from 'react';
import { Globe, FileText, Brain, Check } from 'lucide-react';

const STEPS = [
    { label: 'Scraping do site', icon: Globe, subtitle: 'Lendo HTML e extraindo conteúdo...', estimatedMs: 22000, pStart: 2, pEnd: 35, time: '~20s' },
    { label: 'Gerando Markdown', icon: FileText, subtitle: 'Estruturando conteúdo extraído...', estimatedMs: 1500, pStart: 35, pEnd: 40, time: '~1s' },
    { label: 'Ingestão com IA', icon: Brain, subtitle: 'Gemini processando FAQs (2-3 min)...', estimatedMs: 130000, pStart: 40, pEnd: 95, time: '~2min' },
];

export default function PipelineLoader({ visible, pipelineResult, onComplete }) {
    const [activeStep, setActiveStep] = useState(0);
    const [completedSteps, setCompletedSteps] = useState(new Set());
    const [progress, setProgress] = useState(0);
    const [elapsed, setElapsed] = useState(0);
    const [title, setTitle] = useState('Iniciando pipeline...');
    const [subtitle, setSubtitle] = useState('aguardando...');
    const [stepTimes, setStepTimes] = useState({});

    const elapsedRef = useRef(null);
    const progressRef = useRef(null);
    const stepStartRef = useRef(Date.now());

    // Elapsed timer
    useEffect(() => {
        if (!visible) return;
        setElapsed(0);
        setActiveStep(0);
        setCompletedSteps(new Set());
        setProgress(0);
        setStepTimes({});
        setTitle('Iniciando pipeline...');
        setSubtitle('aguardando...');

        const start = Date.now();
        stepStartRef.current = start;
        elapsedRef.current = setInterval(() => {
            setElapsed(Math.floor((Date.now() - start) / 1000));
        }, 1000);

        return () => clearInterval(elapsedRef.current);
    }, [visible]);

    // Activate step 0 on mount
    useEffect(() => {
        if (visible) {
            activateStep(0);
        }
    }, [visible]);

    // When pipeline result arrives — complete all steps
    useEffect(() => {
        if (pipelineResult && visible) {
            clearInterval(progressRef.current);
            setCompletedSteps(new Set([0, 1, 2]));
            setProgress(100);
            setTitle('Concluído!');
            setSubtitle('Base de conhecimento pronta');
            clearInterval(elapsedRef.current);

            setTimeout(() => {
                onComplete?.();
            }, 900);
        }
    }, [pipelineResult]);

    const activateStep = useCallback((index) => {
        const step = STEPS[index];
        if (!step) return;

        setActiveStep(index);
        setTitle(step.label);
        setSubtitle(step.subtitle);
        stepStartRef.current = Date.now();

        // Animate progress
        clearInterval(progressRef.current);
        let current = step.pStart;
        const delta = (step.pEnd - step.pStart) / (step.estimatedMs / 200);

        progressRef.current = setInterval(() => {
            current = Math.min(step.pEnd, current + delta);
            setProgress(current);
            if (current >= step.pEnd) clearInterval(progressRef.current);
        }, 200);

        // Schedule next step transitions
        if (index === 0) {
            setTimeout(() => {
                completeStep(0);
                activateStep(1);
                setTimeout(() => {
                    completeStep(1);
                    activateStep(2);
                }, 1500);
            }, 22000);
        }
    }, []);

    const completeStep = useCallback((index) => {
        setCompletedSteps(prev => new Set([...prev, index]));
        setStepTimes(prev => ({
            ...prev,
            [index]: ((Date.now() - stepStartRef.current) / 1000).toFixed(1) + 's',
        }));
    }, []);

    const formatElapsed = (s) => {
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
    };

    if (!visible) return null;

    return (
        <div className="pipeline-overlay">
            <div className="pipeline-card">
                {/* Animated orb */}
                <div className="pipeline-orb-wrap">
                    <div className="pipeline-orb">
                        <div className="pipeline-ring ring-slow" />
                        <div className="pipeline-ring ring-fast" />
                        <div className="pipeline-orb-center">
                            {(() => {
                                const StepIcon = STEPS[activeStep]?.icon || Globe;
                                return <StepIcon size={28} className="orb-icon" />;
                            })()}
                        </div>
                        <div className="pipeline-orb-glow" />
                    </div>
                </div>

                {/* Title */}
                <div className="pipeline-info">
                    <h3 className="pipeline-title">{title}</h3>
                    <div className="pipeline-meta">
                        <span className="pipeline-elapsed">{formatElapsed(elapsed)}</span>
                        <span className="pipeline-dot">·</span>
                        <span className="pipeline-subtitle">{subtitle}</span>
                    </div>
                </div>

                {/* Steps */}
                <div className="pipeline-steps">
                    {STEPS.map((step, i) => {
                        const isDone = completedSteps.has(i);
                        const isActive = activeStep === i && !isDone;
                        const StepIcon = step.icon;

                        return (
                            <div key={i} className={`pipeline-step ${isActive ? 'step--active' : ''} ${isDone ? 'step--done' : ''}`}>
                                <div className="step-icon-wrap">
                                    <div className={`step-icon ${isDone ? 'step-icon--done' : isActive ? 'step-icon--active' : 'step-icon--pending'}`}>
                                        {isDone ? <Check size={14} /> : isActive ? <div className="step-spin-dot" /> : <StepIcon size={14} />}
                                    </div>
                                    {i < STEPS.length - 1 && <div className="step-connector" />}
                                </div>
                                <div className="step-body">
                                    <div className="step-label">{step.label}</div>
                                    <div className="step-desc">{step.subtitle.replace('...', '')}</div>
                                </div>
                                <div className={`step-time ${isDone ? 'done' : ''}`}>
                                    {isDone && stepTimes[i] ? stepTimes[i] : step.time}
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Progress bar */}
                <div className="pipeline-progress-track">
                    <div className="pipeline-progress-bar" style={{ width: `${progress}%` }} />
                </div>
                <div className="pipeline-progress-labels">
                    <span>Progresso</span>
                    <span>{Math.round(progress)}%</span>
                </div>
            </div>

            <p className="pipeline-hint">Não feche esta janela durante o processamento</p>
        </div>
    );
}
