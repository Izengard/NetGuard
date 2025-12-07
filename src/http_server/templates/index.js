// NetGuard Captive Portal - Frontend JavaScript
// Manejo de autenticación del lado del cliente

document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const errorMessage = document.getElementById('errorMessage');
    const loginBtn = document.getElementById('loginBtn');

    // Manejo del formulario de login
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        // Deshabilitar botón durante el proceso
        loginBtn.disabled = true;
        loginBtn.textContent = 'Connecting...';
        errorMessage.textContent = '';
        errorMessage.className = 'error-message';
        
        try {
            // Enviar credenciales al servidor
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Login exitoso
                errorMessage.textContent = '✓ Connection successful! Redirecting...';
                errorMessage.className = 'success-message';
                
                // Redirigir después de 2 segundos
                setTimeout(() => {
                    window.location.href = '/';
                }, 2000);
            } else {
                // Login fallido
                errorMessage.textContent = '✗ ' + data.message;
                errorMessage.className = 'error-message';
                loginBtn.disabled = false;
                loginBtn.textContent = 'Connect to Network';
            }
        } catch (error) {
            console.error('Error:', error);
            errorMessage.textContent = '✗ Connection error. Please try again.';
            errorMessage.className = 'error-message';
            loginBtn.disabled = false;
            loginBtn.textContent = 'Connect to Network';
        }
    });

    // Limpiar mensaje de error cuando el usuario empieza a escribir
    document.getElementById('username').addEventListener('input', clearError);
    document.getElementById('password').addEventListener('input', clearError);

    function clearError() {
        errorMessage.textContent = '';
    }

    // Animaciones adicionales (opcional)
    const inputs = document.querySelectorAll('.input-box input');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (this.value === '') {
                this.parentElement.classList.remove('focused');
            }
        });
    });
});

// Función para verificar el estado de la conexión
async function checkConnectionStatus() {
    try {
        const response = await fetch('/status');
        const text = await response.text();
        console.log('Connection status:', text);
    } catch (error) {
        console.error('Status check error:', error);
    }
}

// Verificar estado cada 30 segundos
setInterval(checkConnectionStatus, 30000);
