import { useState, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './components/Navbar/navbar';
import FocusModeModal from './components/FocusModeModal/focus-mode-modal';

export type MainLayoutOutletContext = {
    isFocusMode: boolean;
};

const MainLayout = () => {
    const [isFocusMode, setIsFocusMode] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);

    const handleFocusToggle = useCallback(() => {
        setIsFocusMode((prev) => {
            const next = !prev;
            setIsModalOpen(next);
            return next;
        });
    }, []);

    const handleCloseModal = useCallback(() => {
        setIsModalOpen(false);
    }, []);

    const handleDisableFocusMode = useCallback(() => {
        setIsFocusMode(false);
        setIsModalOpen(false);
    }, []);

    return (
        <>
            <Navbar isFocusMode={isFocusMode} onFocusToggle={handleFocusToggle} />
            <main>
                <Outlet context={{ isFocusMode }} />
            </main>
            {isModalOpen && (
                <FocusModeModal onClose={handleCloseModal} onDisable={handleDisableFocusMode} />
            )}
        </>
    );
};

export default MainLayout;
