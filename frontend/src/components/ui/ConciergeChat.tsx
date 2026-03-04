import React from 'react';
import { useAppStore } from '@/state/appStore';

const ConciergeChat: React.FC = () => {
  const conversation = useAppStore((s) => s.conversation);
  return (
    <div>
      <h2>Concierge</h2>
      <ul>
        {conversation.map((msg) => (
          <li key={msg.id}>{msg.text}</li>
        ))}
      </ul>
    </div>
  );
};

export default ConciergeChat;