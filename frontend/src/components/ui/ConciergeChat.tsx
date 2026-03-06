import React from 'react';
import { useAppStore } from '@/state/appStore';

const ConciergeChat: React.FC = () => {
  const conversation = useAppStore((s) => s.conversation);
  return (
    <div>
      <h2>Concierge</h2>
      <ul>
        {conversation.map((msg) => {
          // stringified metadata for debugging/testing; put in data attribute
          const metaAttr = msg.meta ? JSON.stringify(msg.meta) : undefined;
          return (
            <li key={msg.id} data-meta={metaAttr}>
              {msg.content || msg.text}
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default ConciergeChat;