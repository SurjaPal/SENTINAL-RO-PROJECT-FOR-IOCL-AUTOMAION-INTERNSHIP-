import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageSquare, Send, X, Terminal, Loader, Mic, MicOff } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Message {
  id: string;
  sender: 'user' | 'ai';
  text: string;
}

export default function AiAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [sessionId] = useState(() => {
    let sid = localStorage.getItem('sentinel_session_id');
    if (!sid) {
      sid = 'session_' + Math.random().toString(36).substr(2, 9);
      localStorage.setItem('sentinel_session_id', sid);
    }
    return sid;
  });
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', sender: 'ai', text: 'Sentinel-RO AI initialized. Ask me about system anomalies, active complaints, or dispatch tickets.' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const speak = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  const toggleListen = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech Recognition is not supported in this browser.");
      return;
    }
    
    if (isListening) return;

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => setIsListening(true);
    
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInput(transcript);
    };
    
    recognition.onerror = (event: any) => {
      console.error("Speech recognition error", event.error);
      setIsListening(false);
    };
    
    recognition.onend = () => setIsListening(false);
    
    recognition.start();
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { id: Date.now().toString(), sender: 'user', text: userMessage }]);
    setIsTyping(true);

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: userMessage, session_id: sessionId })
      });
      const data = await response.json();
      
      let aiResponse = data.response || "No response generated.";
      
      const actionRegex = /<ACTION:(.*?):(.*?)>/g;
      let match;
      while ((match = actionRegex.exec(aiResponse)) !== null) {
        const actionType = match[1];
        const actionTarget = match[2];
        
        if (actionType === 'NAVIGATE') {
          window.location.href = actionTarget;
        } else if (actionType === 'SCROLL_TO') {
          if (window.location.pathname !== '/dashboard') {
            window.location.href = '/dashboard#section-' + actionTarget;
          } else {
            setTimeout(() => {
              document.getElementById('section-' + actionTarget)?.scrollIntoView({ behavior: 'smooth' });
            }, 500);
          }
        }
      }
      
      aiResponse = aiResponse.replace(/<ACTION:.*?>/g, '').trim();

      setMessages(prev => [...prev, { 
        id: (Date.now() + 1).toString(), 
        sender: 'ai', 
        text: aiResponse 
      }]);
      speak(aiResponse);
    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [...prev, { 
        id: (Date.now() + 1).toString(), 
        sender: 'ai', 
        text: "Error communicating with AI Assistant." 
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <>
      {/* Floating Action Button */}
      <motion.button
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(prev => !prev)}
        className="fixed bottom-12 right-6 z-50 w-16 h-16 rounded-full bg-[var(--color-io-blue)] shadow-[0_0_20px_rgba(24,119,242,0.4)] flex items-center justify-center border border-[var(--color-io-blue-light)]/50 group"
      >
        {isOpen ? (
          <X className="w-7 h-7 text-white" />
        ) : (
          <MessageSquare className="w-7 h-7 text-white group-hover:animate-pulse" />
        )}
      </motion.button>

      {/* Chat Window */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.9 }}
            transition={{ type: "spring", bounce: 0.3 }}
            className="fixed bottom-32 right-6 z-50 w-[380px] h-[500px] max-h-[calc(100vh-200px)] bg-[#03060C] border border-[var(--color-io-blue)]/30 rounded-xl shadow-[0_0_40px_rgba(0,0,0,0.8)] overflow-hidden flex flex-col font-mono"
            style={{ clipPath: 'polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px)' }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 bg-[#050a14] border-b border-gray-800">
              <div className="flex items-center gap-2 text-[var(--color-io-blue-light)]">
                <Terminal className="w-5 h-5" />
                <span className="font-bold tracking-wider text-sm">SENTINEL_AI</span>
              </div>
              <button 
                onClick={() => setIsOpen(false)}
                className="text-gray-500 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]">
              {messages.map((msg) => (
                <motion.div 
                  initial={{ opacity: 0, x: msg.sender === 'user' ? 20 : -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  key={msg.id}
                  className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div 
                    className={`max-w-[85%] p-3 rounded-lg text-sm leading-relaxed ${
                      msg.sender === 'user' 
                        ? 'bg-[var(--color-io-blue)]/20 border border-[var(--color-io-blue)]/50 text-white' 
                        : 'bg-gray-800/50 border border-gray-700 text-gray-300'
                    }`}
                  >
                    {msg.text}
                  </div>
                </motion.div>
              ))}
              {isTyping && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex justify-start"
                >
                  <div className="bg-gray-800/50 border border-gray-700 text-[var(--color-io-blue-light)] p-3 rounded-lg flex items-center gap-2">
                    <Loader className="w-4 h-4 animate-spin" />
                    <span className="text-xs tracking-widest uppercase">Analyzing...</span>
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-3 bg-[#050a14] border-t border-gray-800">
              <div className="relative flex items-center">
                <input 
                  type="text" 
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="Ask Sentinel-RO..."
                  className="w-full bg-black/50 border border-gray-700 text-white text-sm rounded px-4 py-3 focus:outline-none focus:border-[var(--color-io-blue)] transition-colors placeholder:text-gray-600 pr-20"
                />
                <div className="absolute right-2 flex items-center gap-1">
                  <button 
                    onClick={toggleListen}
                    className={`p-2 transition-colors ${isListening ? 'text-red-500 animate-pulse' : 'text-gray-500 hover:text-white'}`}
                  >
                    {isListening ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
                  </button>
                  <button 
                    onClick={handleSend}
                    disabled={!input.trim() || isTyping}
                    className="p-2 text-[var(--color-io-blue)] hover:text-white disabled:opacity-50 transition-colors"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
