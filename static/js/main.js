// main.js — students will add JavaScript here as features are built

const modal = document.getElementById('howItWorksModal');
const openBtn = document.getElementById('openHowItWorks');
const closeBtn = document.getElementById('modalClose');
const video = document.getElementById('howItWorksVideo');

function openModal() {
    video.src = video.dataset.src;
    modal.classList.add('open');
}

function closeModal() {
    modal.classList.remove('open');
    video.src = '';
}

if (openBtn) {
    openBtn.addEventListener('click', openModal);
    closeBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}
