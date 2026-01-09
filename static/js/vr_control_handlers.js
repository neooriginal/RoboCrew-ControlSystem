document.addEventListener('DOMContentLoaded', () => {
    // Camera Feed Handler
    const cameraImg = document.getElementById('cameraTexture');
    const cameraPlane = document.getElementById('cameraPlane');

    if (cameraImg) {
        cameraImg.src = '/video_feed';
    }

    const cameraImgRight = document.getElementById('cameraTextureRight');
    const cameraPlaneRight = document.getElementById('cameraPlaneRight');

    if (cameraImgRight) {
        cameraImgRight.src = '/video_feed_right';
    }

    // Force texture updates for A-Frame
    setInterval(() => {
        if (cameraPlane && cameraPlane.getObject3D('mesh')) {
            const mat = cameraPlane.getObject3D('mesh').material;
            if (mat.map) mat.map.needsUpdate = true;
        }
        if (cameraPlaneRight && cameraPlaneRight.getObject3D('mesh')) {
            const mat = cameraPlaneRight.getObject3D('mesh').material;
            if (mat.map) mat.map.needsUpdate = true;
        }
    }, 33);
});

// VR Entry Handler
document.addEventListener('DOMContentLoaded', () => {
    const scene = document.querySelector('a-scene');

    if (!navigator.xr) return;

    Promise.all([
        navigator.xr.isSessionSupported('immersive-ar').catch(() => false),
        navigator.xr.isSessionSupported('immersive-vr').catch(() => false)
    ]).then(([ar, vr]) => {
        if (!ar && !vr) return;

        const btn = document.createElement('button');
        btn.className = 'btn btn-primary vr-enter-btn'; // added class for potential css styling
        // Inline styles retained for now to match original exactly, but could be moved to CSS
        Object.assign(btn.style, {
            position: 'absolute',
            bottom: '30px',
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: '2000',
            fontSize: '1.2rem',
            padding: '15px 30px'
        });

        btn.textContent = '🥽 Enter VR';

        btn.onclick = async () => {
            btn.textContent = 'Starting...';
            btn.disabled = true;
            try {
                await document.querySelector('a-scene').enterVR(true);
            } catch (e) {
                btn.textContent = '🥽 Enter VR';
                btn.disabled = false;
                alert('VR Entry Failed: ' + e);
            }
        };

        const contentWrapper = document.querySelector('.content-wrapper > div');
        if (contentWrapper) {
            contentWrapper.appendChild(btn);
        } else {
            // Fallback if structure is different
            document.body.appendChild(btn);
        }

        scene.addEventListener('enter-vr', () => {
            btn.style.display = 'none';
            const statusPanel = document.getElementById('statusPanel');
            if (statusPanel) statusPanel.style.display = 'none';
        });

        scene.addEventListener('exit-vr', () => {
            btn.style.display = 'block';
            const statusPanel = document.getElementById('statusPanel');
            if (statusPanel) statusPanel.style.display = 'block';
        });
    });
});
