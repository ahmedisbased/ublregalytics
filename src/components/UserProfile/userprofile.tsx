import { useState, useRef, useEffect } from 'react';
// No longer need useNavigate here
import './userprofile.scss';
interface UserProfileProps {
    onLogout: () => void;
}

// Accept onLogout as a prop
const UserProfile = ({ onLogout }: UserProfileProps) => {
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsDropdownOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    const handleDropdownLogoutClick = () => {
        setIsDropdownOpen(false);
        onLogout();
    };

    return (
        <div className="user-profile">
            <div className="dropdown" ref={dropdownRef}>
                <button
                    className="btn btn-secondary dropdown-toggle"
                    type="button"
                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                    aria-expanded={isDropdownOpen}
                >
                    MA
                </button>
                <ul className={`dropdown-menu dropdown-menu-end ${isDropdownOpen ? 'show' : ''}`}>
                    <li>
                        <button className="dropdown-item" type="button" onClick={handleDropdownLogoutClick}>
                            Logout
                        </button>
                    </li>
                </ul>
            </div>
        </div>
    );
};

export default UserProfile;