import React, { useState, useEffect, useRef } from 'react';
import { FaPaperPlane } from 'react-icons/fa';
import api from '../../services/api';
import './chat.scss';
import ReactMarkdown from 'react-markdown';

interface ChatScreenProps {
    userInput?: string;
}

interface Message {
    id: string;
    text: string;
    sender: 'user' | 'bot';
    timestamp: string;
}

//comment

const getCurrentTimestamp = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://bca-chatbot-fkbfd2cfa2b9gvh0.uaenorth-01.azurewebsites.net/query'

const TypingIndicator = () => (
    <div className="message-container">
        <div className="message-icon bot-icon">
            <span>UBL</span>
        </div>
        <div className="message-bubble bot-bubble">
            <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    </div>
);

interface ChatMessageProps {
    message: Message;
}

const ChatMessage = React.memo(({ message }: ChatMessageProps) => {
    const isUser = message.sender === 'user';

    return (
        <div className={`message-container ${isUser ? 'user-container' : ''}`}>
            <div className={`message-icon ${isUser ? 'user-icon' : 'bot-icon'}`}>
                {isUser ? <span>MA</span> : <span>UBL</span>}
            </div>
            <div className="message-content">
                <div className={`message-bubble ${isUser ? 'user-bubble' : 'bot-bubble'}`}>
                    {isUser ? (
                        message.text
                    ) : (
                        <ReactMarkdown>{message.text}</ReactMarkdown>
                    )}
                </div>
                <div className="message-timestamp">{message.timestamp}</div>
            </div>
        </div>
    );
});

interface ChatInputProps {
    onSendMessage: (text: string) => void;
    isLoading: boolean;
}

const ChatInput = ({ onSendMessage, isLoading }: ChatInputProps) => {
    const [text, setText] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (text.trim() && !isLoading) {
            onSendMessage(text);
            setText('');
        }
    };

    return (
        <footer className="chat-input-section">
            <form onSubmit={handleSubmit} className="convo-chat-input-wrapper border border-secondary rounded shadow-sm">
                <input
                    type="text"
                    className="chat-input"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Send a message..."
                    disabled={isLoading}
                />
                <button
                    type="submit"
                    className="send-button"
                    disabled={isLoading || !text.trim()}
                    aria-label="Send message"
                >
                    <FaPaperPlane />
                </button>
            </form>
        </footer>
    );
};

const Chat = ({ userInput }: ChatScreenProps) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);
    const initialMessageSent = useRef(false);
    const sessionIdRef = useRef<string>(Math.random().toString(36).substring(2, 8));

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    useEffect(() => {
        if (userInput && !initialMessageSent.current) {
            handleSendMessage(userInput);
            initialMessageSent.current = true;
        }
    }, [userInput]);

    const handleSendMessage = async (text: string) => {
        const userMessage: Message = {
            id: `user-${Date.now()}`,
            text,
            sender: 'user',
            timestamp: getCurrentTimestamp(),
        };
        setMessages(prev => [...prev, userMessage]);
        setIsLoading(true);

        try {
            const response = await api.post(BASE_URL, {
                session_id: sessionIdRef.current,
                question: text
            });

            const data = response.data.answer;
            const botText = data || "I'm sorry, I couldn't find an answer.";

            const botMessage: Message = {
                id: `bot-${Date.now()}`,
                text: botText,
                sender: 'bot',
                timestamp: getCurrentTimestamp(),
            };
            setMessages(prev => [...prev, botMessage]);

        } catch (error) {
            console.error("Failed to fetch chat response:", error);

            const errorMessageText = "Sorry, something went wrong. Please try again later.";
            const errorMessage: Message = {
                id: `error-${Date.now()}`,
                text: errorMessageText,
                sender: 'bot',
                timestamp: getCurrentTimestamp(),
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <>
            <div className="chat-screen-container">
                <main className="chat-area">
                    {messages.map(msg => (
                        <ChatMessage key={msg.id} message={msg} />
                    ))}
                    {isLoading && <TypingIndicator />}
                    <div ref={chatEndRef} />
                </main>
            </div>
            <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
        </>
    );
};

export default Chat;
