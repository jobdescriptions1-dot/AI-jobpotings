import React, { useState, useRef, useEffect } from 'react';

const ChatConsole = () => {
    const [messages, setMessages] = useState([
        { role: 'assistant', text: 'Hello! I am your Procurement AI. How can I help you today?' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const scrollRef = useRef(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg = input;
        setMessages(prev => [...prev, { role: 'user', text: userMsg }]);
        setInput('');
        setLoading(true);

        try {
            const response = await fetch('http://localhost:5000/rag/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: userMsg })
            });

            const data = await response.json();
            setMessages(prev => [...prev, {
                role: 'assistant',
                text: data.answer || data.summary || "I couldn't find an answer for that."
            }]);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'assistant', text: "Error: Could not connect to the RAG system." }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="chat-view">
            <header className="view-header">
                <h1 className="gradient-text">AI Chat Console</h1>
                <p>Ask questions about jobs, requirements, and postings</p>
            </header>

            <div className="chat-container glass-panel">
                <div className="messages" ref={scrollRef}>
                    {messages.map((msg, i) => (
                        <div key={i} className={`message-wrapper ${msg.role}`}>
                            <div className="message-bubble">
                                {msg.text}
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="message-wrapper assistant">
                            <div className="message-bubble loading">
                                <span>.</span><span>.</span><span>.</span>
                            </div>
                        </div>
                    )}
                </div>

                <div className="input-area">
                    <input
                        type="text"
                        placeholder="Ask about Java jobs in Virginia..."
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                    />
                    <button className="gradient-btn" onClick={handleSend} disabled={loading}>
                        Send
                    </button>
                </div>
            </div>

            <style jsx="true">{`
        .chat-view { display: flex; flex-direction: column; gap: 32px; height: calc(100vh - 100px); }
        .chat-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .messages { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 20px; }
        .message-wrapper { display: flex; width: 100%; }
        .message-wrapper.user { justify-content: flex-end; }
        .message-bubble { 
            max-width: 80%; 
            padding: 16px 20px; 
            border-radius: 18px; 
            font-size: 15px; 
            white-space: pre-wrap;
            line-height: 1.6;
        }
        .user .message-bubble { background: var(--accent-primary); color: white; border-bottom-right-radius: 4px; }
        .assistant .message-bubble { background: var(--glass-border); color: var(--text-primary); border-bottom-left-radius: 4px; }
        
        .input-area { padding: 24px; border-top: 1px solid var(--glass-border); display: flex; gap: 16px; }
        input { 
            flex: 1; 
            background: rgba(0,0,0,0.2); 
            border: 1px solid var(--glass-border); 
            border-radius: 12px; 
            padding: 12px 20px; 
            color: white; 
            font-family: var(--font-main);
            outline: none;
        }
        input:focus { border-color: var(--accent-primary); }
        
        .loading span { animation: blink 1.4s infinite both; }
        .loading span:nth-child(2) { animation-delay: .2s; }
        .loading span:nth-child(3) { animation-delay: .4s; }
        @keyframes blink { 0% { opacity: .2; } 20% { opacity: 1; } 100% { opacity: .2; } }
      `}</style>
        </div>
    );
};

export default ChatConsole;
