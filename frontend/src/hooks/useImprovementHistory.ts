import { useState, useCallback } from 'react';

interface ImprovementHistoryEntry {
  section: string;
  questions: string[];
  answers: string[];
  timestamp: number;
  originalContent: string;
  improvedContent?: string;
}

export const useImprovementHistory = () => {
  const [history, setHistory] = useState<ImprovementHistoryEntry[]>([]);

  const addHistoryEntry = useCallback((entry: Omit<ImprovementHistoryEntry, 'timestamp'>) => {
    const newEntry: ImprovementHistoryEntry = {
      ...entry,
      timestamp: Date.now()
    };
    
    console.log('📝 History: Adding entry for section:', entry.section, newEntry);
    setHistory(prev => [...prev, newEntry]);
    return newEntry;
  }, []);

  const updateHistoryEntry = useCallback((timestamp: number, improvedContent: string) => {
    console.log('✨ History: Updating entry with timestamp:', timestamp, 'improved content:', improvedContent);
    setHistory(prev => prev.map(entry => 
      entry.timestamp === timestamp 
        ? { ...entry, improvedContent }
        : entry
    ));
  }, []);

  const clearHistory = useCallback(() => {
    console.log('🧹 History: Clearing all history');
    setHistory([]);
  }, []);

  const getHistoryForSection = useCallback((section: string) => {
    return history.filter(entry => entry.section === section);
  }, [history]);

  return {
    history,
    addHistoryEntry,
    updateHistoryEntry,
    clearHistory,
    getHistoryForSection
  };
};