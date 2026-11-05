import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, Bot, User, Sparkles, Sliders } from 'lucide-react';

export default function AgentChatBox({ portfolioOverview, activePositions }) {
  const [messages, setMessages] = useState([
    {
      sender: 'AGENT',
      text: 'Hello! I am AETHER, your autonomous crypto and prediction markets trading agent. You can ask me about active trades, market theses, risk parameters, or instruct me to adjust trading guidelines!'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { sender: 'USER', text: userMsg }]);
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg })
      });
      const data = await response.json();
      setMessages((prev) => [...prev, { sender: 'AGENT', text: data.reply }]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { sender: 'AGENT', text: 'Error connecting to backend AI Chat service.' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel p-5 rounded-2xl mb-6 flex flex-col h-[520px]">
      
      {/* Chat Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3 shrink-0">
        <div className="flex items-center space-x-2">
          <MessageSquare className="w-5 h-5 text-cyan-400" />
          <h2 className="text-lg font-bold text-slate-100 tracking-tight">Interactive Agent Conversational Chat</h2>
          <span className="text-xs font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            AI Assistant
          </span>
        </div>
        <div className="text-xs font-mono text-slate-400 flex items-center space-x-1">
          <Sparkles className="w-3.5 h-3.5 text-purple-400" />
          <span>OpenAI / DeepSeek / Ollama Ready</span>
        </div>
      </div>

      {/* Messages Stream */}
      <div className="flex-1 overflow-y-auto space-y-3 font-mono text-xs pr-2 mb-3">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex items-start space-x-2.5 ${
              m.sender === 'USER' ? 'justify-end' : 'justify-start'
            }`}
          >
            {m.sender === 'AGENT' && (
              <div className="w-7 h-7 rounded-lg bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-cyan-400" />
              </div>
            )}

            <div
              className={`max-w-[80%] p-3 rounded-2xl leading-relaxed break-words ${
                m.sender === 'USER'
                  ? 'bg-cyan-600 text-white rounded-tr-none shadow-md shadow-cyan-500/10'
                  : 'bg-slate-900/90 text-slate-200 border border-slate-800 rounded-tl-none'
              }`}
            >
              <div className="text-[10px] font-bold text-slate-400 mb-1">
                {m.sender === 'USER' ? 'YOU' : 'AETHER AGENT'}
              </div>
              <div className="whitespace-pre-wrap">{m.text}</div>
            </div>

            {m.sender === 'USER' && (
              <div className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                <User className="w-4 h-4 text-slate-300" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center space-x-2 text-cyan-400 font-mono text-xs italic">
            <Bot className="w-4 h-4 animate-spin" />
            <span>Agent synthesizing response...</span>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Chat Input Form */}
      <form onSubmit={handleSend} className="flex items-center space-x-2 shrink-0 pt-2 border-t border-slate-800">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask AETHER about trades, thesis, or instruct parameter changes..."
          className="flex-1 bg-slate-950 border border-slate-800 focus:border-cyan-500 rounded-xl px-4 py-2.5 text-xs font-mono text-slate-100 placeholder-slate-500 focus:outline-none transition-all"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-4 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-black font-bold rounded-xl text-xs font-mono transition-all disabled:opacity-50 flex items-center space-x-1 shadow-md shadow-cyan-500/20"
        >
          <Send className="w-4 h-4" />
          <span>Send</span>
        </button>
      </form>

    </div>
  );
}
