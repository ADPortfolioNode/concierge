import React from 'react';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import { useAppStore } from '@/state/appStore';

const ChatContainer: React.FC = () => {
  const messages = useAppStore((s) => s.conversation);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ flex: '1 1 auto', minHeight: 0 }}>
        <MessageList messages={messages} />
      </div>
      <div style={{ flex: '0 0 auto' }}>
        <MessageInput />
      </div>
    </div>
  );
};

export default ChatContainer;
