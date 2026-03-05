import React from 'react';

const HowToPage: React.FC = () => {
  return (
    <div style={{ padding: 'var(--space-6)' }}>
      <h1>How to use Concierge</h1>
      <p>The following example prompts can be used in the chat UI or in automated tests.</p>
      <h2>General prompts</h2>
      <ul>
        <li>"Help me outline a launch plan for the new mobile app."</li>
        <li>"What are the next three milestones for the marketing campaign?"</li>
        <li>"Summarise the latest thread in the team Slack channel."</li>
        <li>"Give me pros and cons of using Chroma vs. Qdrant for our vector store."</li>
        <li>"Act as a code reviewer and explain any issues you see in this snippet:" (attach code)</li>
      </ul>
      <h2>Technical/utility prompts</h2>
      <ul>
        <li>"Write a bash script that clears the ports 5173 and 8000 before starting services."</li>
        <li>"Explain how to add a timeout to an Axios client and handle a slow response."</li>
      </ul>
      <h2>Goal‑setting / planning</h2>
      <ul>
        <li>"Create a list of weekly goals for improving developer workflow."</li>
        <li>"Set up a test plan to verify UI error banners and slow‑server notices."</li>
      </ul>
      <h2>Gemini‑style multimodal prompts</h2>
      <ul>
        <li>"Here’s a photo of a circuit board with one component circled; what is it?"</li>
        <li>"Screenshot attached: the console shows a crash stack trace—what does it mean and how do I fix it?"</li>
        <li>"Listen to this short audio clip (French); please transcribe and translate it."</li>
        <li>"Watch this 10‑second video of someone entering a room; describe what happens."</li>
        <li>"The following diagram shows our architecture (image); list any security weaknesses you spot."</li>
      </ul>
    </div>
  );
};

export default HowToPage;
