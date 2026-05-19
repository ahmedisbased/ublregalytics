import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FaChartLine, FaPercentage, FaUserTie, FaBalanceScale, FaPaperPlane } from "react-icons/fa";

import ProductCard from '../../components/ProductCard';
import homeLogo from '../../assets/images/ubl-logo.png';
import './home.scss';
// import type { MainLayoutOutletContext } from '../../MainLayout';

interface HomeProps {
    setUserInput: (input: string) => void;
}

const Home = ({ setUserInput }: HomeProps) => {
    const [input, setInput] = useState('');
    const navigate = useNavigate();
    // const { isFocusMode } = useOutletContext<MainLayoutOutletContext>();

    const suggestionCards = [
        {
            title: 'Yearly Revenue (2024)',
            description: 'What is the yearly revenue of Lucky Cement for the year 2024?',
            icon: <FaChartLine size={20} />,
        },
        {
            title: 'YoY Revenue Change',
            description: 'What is the year-over-year change in revenue of Lucky Cement?',
            icon: <FaPercentage size={20} />,
        },
        {
            title: 'Chief Executive Officer',
            description: 'Who is the CEO of Lucky Cement?',
            icon: <FaUserTie size={20} />,
        },
        {
            title: 'Profit or Loss Status',
            description: 'Is Lucky Cement currently operating in profit or loss?',
            icon: <FaBalanceScale size={20} />,
        },
    ];

    const handleCardClick = (description: string) => {
        setInput(description);
    };

    const handleSubmit = (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (input.trim()) {
            setUserInput(input);
            navigate('/conversation');
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    return (
        <div className="home-page-container">
            <header className="home-header text-center">
                <img src={homeLogo} className="logo-img" alt="Company Logo" />
                <h1 className="mt-3">Hello, I'm your dedicated BCA assistant</h1>
                <p className="lead text-muted">How can I assist you today?</p>
            </header>

            <div className="chat-input-section mt-5">
                <div className="container">
                    <form onSubmit={handleSubmit} className="chat-input-wrapper border border-secondary rounded shadow-sm">
                        <input
                            type="text"
                            className="chat-input"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyPress}
                            placeholder="Send a message..."
                        />
                        <button disabled={!input.trim()} type="submit" className="btn-icon" aria-label="Send message">
                            <FaPaperPlane />
                        </button>
                    </form>
                </div>
            </div>

            <main className="container flex-grow-1 mt-2">
                <div className="row g-4 justify-content-center suggestion-cards">
                    {suggestionCards.map((card, index) => (
                        <div key={index} className="col-12 col-sm-6 col-lg-3 d-flex">
                            <div className="suggestion-card-wrapper" onClick={() => handleCardClick(card.description)}>
                                <ProductCard
                                    title={card.title}
                                    description={card.description}
                                    icon={card.icon}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </main>
        </div>
    );
};

export default Home;
