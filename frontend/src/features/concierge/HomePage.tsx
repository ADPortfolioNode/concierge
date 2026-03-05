import React, { useEffect } from 'react';
import { useAppStore } from '@/state/appStore';
import { fetchConversation } from '@/api/conciergeService';

const HomePage: React.FC = () => {
  const setConversation = useAppStore((s) => s.setConversation);

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
  }, [setConversation]);

  return <div>Welcome to Concierge</div>;
};

export default HomePage;