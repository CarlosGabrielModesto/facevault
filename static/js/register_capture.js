/**
 * register_capture.js — Controla a captura facial durante o cadastro no FaceVault.
 *
 * Fluxo:
 *   1. Inicia a webcam automaticamente ao carregar a página
 *   2. Ao clicar em "Capturar", extrai o frame e converte para base64
 *   3. Envia os dados do usuário + imagem para o backend finalizar o registro
 */

document.addEventListener('DOMContentLoaded', async () => {

    // ── Referências ao DOM ────────────────────────────────
    const video      = document.getElementById('video');
    const canvas     = document.getElementById('canvas');
    const btnCapture = document.getElementById('btn-capture');
    const alertBox   = document.getElementById('alert-box');

    // ── Utilitário de alerta inline ───────────────────────

    /**
     * Exibe um alerta colorido no card de captura.
     * @param {string} msg
     * @param {'danger'|'success'|'warning'} type
     */
    function showAlert(msg, type = 'danger') {
        alertBox.className = `inline-alert inline-alert--${type}`;
        alertBox.textContent = msg;
        alertBox.style.display = 'block';
        setTimeout(() => { alertBox.style.display = 'none'; }, 6000);
    }

    // ── Inicializa a webcam ao carregar a página ──────────

    try {
        // Solicita acesso à câmera frontal com resolução preferencial
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }
        });
        // Vincula o stream ao elemento de vídeo
        video.srcObject = stream;
    } catch (err) {
        // Em caso de falha, desativa o botão e exibe mensagem de erro
        showAlert('Não foi possível acessar a câmera. Verifique as permissões e recarregue a página.');
        btnCapture.disabled = true;
        console.error('getUserMedia error:', err);
        return;
    }

    // ── Coleta os dados do usuário dos campos ocultos ─────

    // Os campos ocultos foram preenchidos pelo template Jinja2 com os dados do formulário anterior
    const userData = {
        email:           document.getElementById('h-email').value,
        nome:            document.getElementById('h-nome').value,
        sobrenome:       document.getElementById('h-sobre').value,
        cpf:             document.getElementById('h-cpf').value,
        celular:         document.getElementById('h-cel').value,
        data_nascimento: document.getElementById('h-nasc').value,
        genero:          document.getElementById('h-genero').value,
    };

    // ── Captura e envio ao backend ────────────────────────

    btnCapture.addEventListener('click', async () => {
        if (!video.srcObject) {
            showAlert('Câmera não está ativa. Recarregue a página.');
            return;
        }

        // Define o tamanho do canvas igual ao frame do vídeo
        canvas.width  = video.videoWidth;
        canvas.height = video.videoHeight;

        // Renderiza o frame atual do vídeo no canvas oculto
        canvas.getContext('2d').drawImage(video, 0, 0);

        // Exporta o canvas como imagem PNG em base64
        const faceData = canvas.toDataURL('image/png');

        // Exibe feedback visual de processamento (DeepFace pode levar alguns segundos)
        btnCapture.disabled = true;
        btnCapture.innerHTML = '<span class="material-symbols-rounded">hourglass_top</span> Processando...';

        try {
            // Envia todos os dados do usuário + imagem facial para o endpoint de registro
            const response = await fetch('/register_capture', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ...userData, face_data: faceData }),
            });
            const data = await response.json();

            if (data.status === 'success') {
                // Exibe mensagem de sucesso e redireciona para o login após 1.5s
                showAlert('Cadastro realizado com sucesso! Redirecionando...', 'success');
                setTimeout(() => { window.location.href = '/login'; }, 1500);
            } else {
                // Falha (rosto não detectado, erro interno, etc.): reativa o botão
                showAlert(data.message);
                btnCapture.disabled = false;
                btnCapture.innerHTML = '<span class="material-symbols-rounded">photo_camera</span> Capturar e Finalizar Cadastro';
            }
        } catch {
            showAlert('Erro de conexão. Verifique sua internet e tente novamente.');
            btnCapture.disabled = false;
            btnCapture.innerHTML = '<span class="material-symbols-rounded">photo_camera</span> Capturar e Finalizar Cadastro';
        }
    });

});
