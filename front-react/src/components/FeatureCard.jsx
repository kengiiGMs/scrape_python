import { useState } from 'react';

export default function FeatureCard({ icon: Icon, title, description }) {
    const [hovered, setHovered] = useState(false);

    return (
        <div
            className="feature-card"
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
            style={{
                transform: hovered ? 'scale(1.04) translateY(-4px)' : 'scale(1)',
                boxShadow: hovered
                    ? '0 0 30px rgba(139, 92, 246, 0.25), 0 12px 40px rgba(0,0,0,0.3)'
                    : '0 4px 20px rgba(0,0,0,0.2)',
            }}
        >
            <div className="feature-icon-wrap" style={{
                boxShadow: hovered ? '0 0 20px rgba(139, 92, 246, 0.3)' : 'none',
            }}>
                <Icon size={22} strokeWidth={1.8} />
            </div>
            <h3 className="feature-title">{title}</h3>
            <p className="feature-desc">{description}</p>
        </div>
    );
}
