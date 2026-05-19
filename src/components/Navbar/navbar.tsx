import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { FiTarget } from 'react-icons/fi';
import UserProfile from './../UserProfile/userprofile';
import { IoMenu, IoClose } from 'react-icons/io5';
import './navbar.scss';
import logo from '../../assets/images/ubl-logo.png';
import { type UserRole } from '../../types/auth';
import UploadImageModal from '../UploadImageModal/upload-image-modal';

interface NavBarProps {
    isFocusMode: boolean;
    onFocusToggle: () => void;
}

const NavBar = ({ isFocusMode, onFocusToggle }: NavBarProps) => {
    const [isOpen, setIsOpen] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
    const role = (localStorage.getItem('userRole') as UserRole | null) ?? null;
    const isSuperAdmin = role === 'superAdmin';
    const isXmlGeneratorActive = location.pathname.startsWith('/xml-generator');
    const isHomeActive =
        location.pathname.startsWith('/home') ||
        location.pathname.startsWith('/conversation');
    const canUseSummaryToggle = !isSuperAdmin || isHomeActive;

    const handleAdminViewChange = (view: 'home' | 'upload' | 'xml-generator') => {
        navigate(`/${view}`);
        setIsOpen(false);
    };

    const toDefaultRoute = () => {
        navigate(isSuperAdmin ? '/xml-generator' : '/home');
    };

    const handleLogout = () => {
        localStorage.removeItem('userEmail');
        localStorage.removeItem('userName');
        localStorage.removeItem('userRole');
        setIsOpen(false);
        navigate('/login');
    };

    const handleFocusToggle = () => {
        if (!canUseSummaryToggle) {
            return;
        }
        onFocusToggle();
        if (isOpen) {
            setIsOpen(false);
        }
    };

    // const handleOpenUploadModal = () => {
    //     setIsUploadModalOpen(true);
    //     if (isOpen) {
    //         setIsOpen(false);
    //     }
    // };

    return (
        <nav className='border-bottom border-secondary'>
            <div className="navbar-left">
                <img src={logo} alt="UBL Logo" className="logo" onClick={toDefaultRoute} /> Regalytics
            </div>

            <div className="hamburger" onClick={() => setIsOpen(!isOpen)}>
                {isOpen ? <IoClose size={24} /> : <IoMenu size={24} />}
            </div>

            <div className={`nav-items ${isOpen ? 'open' : ''}`}>
                {canUseSummaryToggle && (
                    <button
                        type="button"
                        className="focus-toggle-btn"
                        onClick={handleFocusToggle}
                        aria-pressed={isFocusMode}
                    >
                        <FiTarget size={18} />
                        <span>{'Summary Mode'}</span>
                    </button>
                )}

                {isSuperAdmin && (
                    <div className="admin-view-toggle" role="group" aria-label="Admin interface toggle">
                        {/* <button
                            type="button"
                            className={`toggle-btn ${isUploadActive ? 'active' : ''}`}
                            onClick={() => handleAdminViewChange('upload')}
                            aria-pressed={isUploadActive}
                        >
                            Upload
                        </button>
                        <button
                            type="button"
                            className={`toggle-btn ${isHomeActive ? 'active' : ''}`}
                            onClick={() => handleAdminViewChange('home')}
                            aria-pressed={isHomeActive}
                        >
                            Home
                        </button> */}
                        <button
                            type="button"
                            className={`toggle-btn ${isXmlGeneratorActive ? 'active' : ''}`}
                            onClick={() => handleAdminViewChange('xml-generator')}
                            aria-pressed={isXmlGeneratorActive}
                        >
                            XML Generator
                        </button>
                    </div>
                )}

                {/* {isSuperAdmin && (
                    <button
                        type="button"
                        className="upload-image-btn"
                        onClick={handleOpenUploadModal}
                    >
                        Smart FinOCR
                    </button>
                )} */}

                <UserProfile onLogout={handleLogout} />

                <button className="mobile-logout-btn" onClick={handleLogout}>
                    Logout
                </button>
            </div>

            {isUploadModalOpen && (
                <UploadImageModal onClose={() => setIsUploadModalOpen(false)} />
            )}
        </nav>
    );
};

export default NavBar;
