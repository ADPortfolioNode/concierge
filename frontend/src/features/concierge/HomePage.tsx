import React, { useEffect } from 'react';
import { useAppStore } from '@/state/appStore';
import { fetchConversation } from '@/api/conciergeService';

const HomePage: React.FC = () => {
  const setConversation = useAppStore((s) => s.setConversation);
  const setActiveMedia = useAppStore((s) => s.setActiveMedia);

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await fetchConversation();
        if (resp.data.status === 'success') {
          setConversation(resp.data.data.conversation || []);
        }
      } catch (e) {
        // handle error gracefully
      }
    };
    load();
    // auto-populate UI for local testing when enabled
    try {
      const auto = (typeof window !== 'undefined' && window.localStorage && window.localStorage.getItem('AUTO_POPULATE')) || null;
      if (auto === 'yes') {
        setConversation([
          { id: '1', text: 'Welcome — this is a seeded conversation for UI review.', timestamp: new Date().toISOString(), media: null },
          { id: '2', text: 'Click Test Media to display an image.', timestamp: new Date().toISOString(), media: 'https://placehold.co/600x400' },
        ]);
        setActiveMedia('https://placehold.co/600x400');
      }
    } catch (e) {
      // ignore
    }
  }, [setConversation]);

  return (
    <div>
      Welcome to Concierge
      <button onClick={() => setActiveMedia('https://placehold.co/600x400')}>
        Test Media
      </button>
      <button
        onClick={() => {
          try {
            window.localStorage.setItem('AUTO_POPULATE', 'yes');
            window.localStorage.setItem('AUTO_AUTHORIZE', 'yes');
            window.location.reload();
          } catch (e) {}
        }}
      >
        Enable Auto (authorize+populate)
      </button>
    </div>
  );
};

export default HomePage;