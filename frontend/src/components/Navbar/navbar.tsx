import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import UserProfile from '../UserProfile/userprofile';

import { IoMenu, IoClose } from 'react-icons/io5';
import './navbar.scss';
import logo from '../../assets/images/ubl-logo.png';
import UploadImageModal from '../UploadImageModal/upload-image-modal';

import { clearAuthSession, getDefaultRouteForPermissions, getStoredPermissions, hasPermission } from '../../services/authPermissions';

interface NavBarProps {
    isFocusMode: boolean;
    onFocusToggle: () => void;
}

const NavBar = ({ isFocusMode, onFocusToggle }: NavBarProps) => {
    void isFocusMode;
    const [isOpen, setIsOpen] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();
    const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
    const permissions = getStoredPermissions();
    const isXmlGeneratorActive = location.pathname.startsWith('/xml-generator');
    const isCtrGeneratorActive = location.pathname.startsWith('/ctr-generator');
    const isRcoaActive = location.pathname.startsWith('/rcoa');
    const isHomeActive =
        location.pathname.startsWith('/home') ||
        location.pathname.startsWith('/conversation');
    const canUseSummaryToggle = isHomeActive;

    const handleAdminViewChange = (view: 'rcoa' | 'xml-generator' | 'ctr-generator') => {
        navigate(`/${view}`);
        setIsOpen(false);
    };

    const toDefaultRoute = () => {
        navigate(getDefaultRouteForPermissions(permissions));
    };

    const handleLogout = () => {
        clearAuthSession();
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

    void handleFocusToggle;

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
                {/* {canUseSummaryToggle && (
                    <button
                        type="button"
                        className="focus-toggle-btn"
                        onClick={handleFocusToggle}
                        aria-pressed={isFocusMode}
                    >
                        <FiTarget size={18} />
                        <span>{'Summary Mode'}</span>
                    </button>
                )} */}

                {(hasPermission('RCOA') || hasPermission('STR') || hasPermission('CTR')) && (
                    <div className="admin-view-toggle" role="group" aria-label="Admin interface toggle">
                        {hasPermission('RCOA') && (
                            <button
                                type="button"
                                className={`toggle-btn ${isRcoaActive ? 'active' : ''}`}
                                onClick={() => handleAdminViewChange('rcoa')}
                                aria-pressed={isRcoaActive}
                            >
                                RCOA
                            </button>
                        )}
                        {hasPermission('STR') && (
                            <button
                                type="button"
                                className={`toggle-btn ${isXmlGeneratorActive ? 'active' : ''}`}
                                onClick={() => handleAdminViewChange('xml-generator')}
                                aria-pressed={isXmlGeneratorActive}
                            >
                                XML Generator
                            </button>
                        )}
                        {hasPermission('CTR') && (
                            <button
                                type="button"
                                className={`toggle-btn ${isCtrGeneratorActive ? 'active' : ''}`}
                                onClick={() => handleAdminViewChange('ctr-generator')}
                                aria-pressed={isCtrGeneratorActive}
                            >
                                CTR Generator
                            </button>
                        )}
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
