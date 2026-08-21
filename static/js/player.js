// static/js/player.js
// Полностью отключены все функции кроме play/pause

class VideoPlayer {
    constructor(videoElement, lessonId, initialPosition = 0) {
        this.video = videoElement;
        this.lessonId = lessonId;
        this.saveInterval = 5000;
        this.lastSavedPosition = 0;
        this.initialPosition = initialPosition;

        if (this.video) {
            this.init();
        }
    }

    init() {
        if (this.initialPosition > 0) {
            this.video.currentTime = this.initialPosition;
        }

        // Полностью отключаем все элементы управления
        this.video.controls = false;
        this.video.controlsList = 'nodownload noremoteplayback noplaybackrate';
        this.video.disablePictureInPicture = true;

        // Блокируем все клавиши
        this.video.addEventListener('keydown', (e) => {
            e.preventDefault();
            e.stopPropagation();
            return false;
        });

        // Блокируем двойной клик
        this.video.addEventListener('dblclick', (e) => {
            e.preventDefault();
            e.stopPropagation();
            return false;
        });

        // Блокируем контекстное меню
        this.video.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            e.stopPropagation();
            return false;
        });

        // Блокируем все события мыши
        this.video.addEventListener('mousedown', (e) => {
            e.preventDefault();
            e.stopPropagation();
            return false;
        });

        this.video.addEventListener('mouseup', (e) => {
            e.preventDefault();
            e.stopPropagation();
            return false;
        });

        this.video.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            return false;
        });

        this.setupListeners();
    }

    setupListeners() {
        this.video.addEventListener('pause', () => {
            this.saveProgress(false);
        });

        this.video.addEventListener('ended', () => {
            this.saveProgress(true);
            this.showCompleted();
        });

        this.autoSaveInterval = setInterval(() => {
            if (!this.video.paused) {
                this.saveProgress(false);
            }
        }, this.saveInterval);

        window.addEventListener('beforeunload', () => {
            this.saveProgress(true);
        });
    }

    saveProgress(completed = false) {
        const currentTime = Math.floor(this.video.currentTime);
        const duration = Math.floor(this.video.duration);
        const isCompleted = completed || (this.video.currentTime >= duration - 1 && duration > 0);

        if (currentTime === this.lastSavedPosition && !isCompleted) return;

        this.lastSavedPosition = currentTime;

        const data = {
            position: currentTime,
            completed: isCompleted
        };

        fetch(`/lesson/${this.lessonId}/progress`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        }).catch(error => console.error('Progress save error:', error));
    }

    showCompleted() {
        const container = this.video.parentElement;
        let badge = container.querySelector('.lesson-completed-badge');
        if (!badge) {
            badge = document.createElement('div');
            badge.className = 'lesson-completed-badge';
            badge.style.cssText = `
                position: absolute;
                top: 16px;
                right: 16px;
                background: #4CAF50;
                color: #fff;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 8px;
                z-index: 10;
                animation: fadeIn 0.5s ease;
                pointer-events: none;
            `;
            container.style.position = 'relative';
            container.appendChild(badge);
        }
        badge.innerHTML = '✅ Dars yakunlandi';
    }

    destroy() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
        window.removeEventListener('beforeunload', this.saveProgress);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        video {
            -webkit-user-select: none;
            user-select: none;
        }
        /* Скрываем все элементы управления в Firefox */
        video::-moz-range-track,
        video::-moz-range-thumb {
            display: none !important;
        }
    `;
    document.head.appendChild(style);
});

// Блокировка клавиш на уровне документа
document.addEventListener('keydown', function(e) {
    const video = document.querySelector('video');
    if (video) {
        const blockedKeys = [' ', 'Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home', 'End', 'f', 'F'];
        if (blockedKeys.includes(e.key) || e.key === ' ') {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    }
}, true);