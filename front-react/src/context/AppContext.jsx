import { createContext, useContext, useState, useCallback } from 'react';

const AppContext = createContext(null);

export function AppProvider({ children }) {
    const [currentIdConta, setCurrentIdConta] = useState(null);
    const [currentUrl, setCurrentUrl] = useState('');
    const [currentTable, setCurrentTable] = useState('marketing_rag');
    const [tables, setTables] = useState(['marketing_rag']);
    const [pipelines, setPipelines] = useState([]);

    const reset = useCallback(() => {
        setCurrentIdConta(null);
        setCurrentUrl('');
    }, []);

    const addTable = useCallback((name) => {
        setTables(prev => {
            if (prev.includes(name)) return prev;
            return [...prev, name];
        });
    }, []);

    return (
        <AppContext.Provider value={{
            currentIdConta, setCurrentIdConta,
            currentUrl, setCurrentUrl,
            currentTable, setCurrentTable,
            tables, addTable,
            pipelines, setPipelines,
            reset,
        }}>
            {children}
        </AppContext.Provider>
    );
}

export function useApp() {
    const ctx = useContext(AppContext);
    if (!ctx) throw new Error('useApp must be inside AppProvider');
    return ctx;
}
