/**
 * login.js — Controlador do fluxo de login em 3 etapas do FaceVault.
 *
 * Etapa 1: Validação local + envio do CPF ao backend
 * Etapa 2: Validação do celular vinculado ao CPF
 * Etapa 3: Captura facial e comparação via DeepFace no backend
 */

document.addEventListener('DOMContentLoaded', () => {

    // ── Referências ao DOM ──────────────────────────────────
    const alertBox  = document.getElementById('alert-box');
    const step1     = document.getElementById('step-1');
    const step2     = document.getElementById('step-2');
    const step3     = document.getElementById('step-3');
    const video     = document.getElementById('video');
    const canvas    = document.getElementById('canvas');
    const btnCpf    = document.getElementById('btn-cpf');
    const btnCel    = document.getElementById('btn-cel');
    const btnCap    = document.getElementById('btn-capture');

    // Indicadores visuais do stepper no topo do card (0-based)
    const stepItems = [
        document.getElementById('si-1'),
        document.getElementById('si-2'),
        document.getElementById('si-3'),
    ];

    // ── Utilitários ────────────────────────────────────────

    /**
     * Exibe uma mensagem de alerta inline no card de login.
     * @param {string} msg   - Texto da mensagem
     * @param {'danger'|'success'|'warning'} type - Tipo visual do alerta
     */
    function alert(msg, type = 'danger') {
        alertBox.className = `inline-alert inline-alert--${type}`;
        alertBox.textContent = msg;
        alertBox.style.display = 'block';
        // Remove automaticamente após 5 segundos
        setTimeout(() => { alertBox.style.display = 'none'; }, 5000);
    }

    /**
     * Avança o fluxo para a próxima etapa:
     * - Oculta a etapa atual
     * - Exibe a próxima
     * - Atualiza o stepper: conclui a atual e ativa a próxima
     *
     * @param {HTMLElement} from  - Container da etapa atual
     * @param {HTMLElement} to    - Container da próxima etapa
     * @param {number} toIdx      - Índice (0-based) da próxima etapa no stepper
     */
    function nextStep(from, to, toIdx) {
        from.style.display = 'none';
        to.style.display = 'block';

        // Marca a etapa anterior como concluída (verde)
        stepItems[toIdx - 1].classList.remove('stepper__item--active');
        stepItems[toIdx - 1].classList.add('stepper__item--done');

        // Ativa a etapa atual (azul)
        stepItems[toIdx].classList.add('stepper__item--active');
    }

    /**
     * Ativa a câmera do dispositivo e vincula o stream ao elemento <video>.
     * Solicita permissão de câmera frontal ao navegador.
     */
    async function startCamera() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }
            });
            // Vincula o stream de vídeo ao elemento <video> da página
            video.srcObject = stream;
        } catch (err) {
            alert('Câmera não disponível. Verifique as permissões do navegador.');
            console.error('getUserMedia error:', err);
        }
    }

    /**
     * Envia uma requisição POST JSON ao backend e retorna o objeto de resposta.
     * @param {string} url     - Endpoint relativo
     * @param {object} payload - Dados a serializar como JSON
     * @returns {Promise<object>} Dados JSON da resposta
     */
    async function post(url, payload) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        return res.json();
    }

    // ── Etapa 1: verificar CPF ──────────────────────────────

    btnCpf.addEventListener('click', async () => {
        const cpf = document.getElementById('cpf').value.trim();

        // Validação local: CPF deve ter exatamente 11 dígitos numéricos
        if (!/^\d{11}$/.test(cpf)) {
            alert('CPF deve ter exatamente 11 dígitos numéricos.');
            return;
        }

        // Desabilita o botão enquanto aguarda resposta do servidor
        btnCpf.disabled = true;
        btnCpf.textContent = 'Verificando...';

        try {
            const data = await post('/verify_cpf', { cpf });

            if (data.status === 'success') {
                // CPF encontrado — avança para etapa do celular
                nextStep(step1, step2, 1);
            } else {
                alert(data.message);
            }
        } catch {
            alert('Erro de conexão. Verifique sua internet e tente novamente.');
        } finally {
            // Reabilita o botão independentemente do resultado
            btnCpf.disabled = false;
            btnCpf.innerHTML = 'Verificar CPF <span class="material-symbols-rounded">arrow_forward</span>';
        }
    });

    // ── Etapa 2: verificar celular ──────────────────────────

    btnCel.addEventListener('click', async () => {
        const cpf     = document.getElementById('cpf').value.trim();
        const celular = document.getElementById('celular').value.trim();

        if (!celular) {
            alert('Informe o celular com DDD.');
            return;
        }

        btnCel.disabled = true;
        btnCel.textContent = 'Verificando...';

        try {
            // Envia CPF + celular para validação cruzada no backend
            const data = await post('/verify_celular', { cpf, celular });

            if (data.status === 'success') {
                // Celular confirmado — avança para captura facial e inicia a câmera
                nextStep(step2, step3, 2);
                await startCamera();
            } else {
                alert(data.message);
            }
        } catch {
            alert('Erro de conexão. Tente novamente.');
        } finally {
            btnCel.disabled = false;
            btnCel.innerHTML = 'Verificar Celular <span class="material-symbols-rounded">arrow_forward</span>';
        }
    });

    // ── Etapa 3: captura e reconhecimento facial ────────────

    btnCap.addEventListener('click', async () => {
        const cpf = document.getElementById('cpf').value.trim();

        if (!video.srcObject) {
            alert('Câmera não inicializada. Recarregue a página.');
            return;
        }

        // Dimensiona o canvas exatamente como o frame do vídeo
        canvas.width  = video.videoWidth;
        canvas.height = video.videoHeight;

        // Desenha o frame atual do vídeo no canvas para obter a imagem
        canvas.getContext('2d').drawImage(video, 0, 0);

        // Converte o frame para base64 PNG (formato aceito pelo backend)
        const faceData = canvas.toDataURL('image/png');

        // Exibe feedback de processamento
        btnCap.disabled = true;
        btnCap.innerHTML = '<span class="material-symbols-rounded">hourglass_top</span> Processando...';

        try {
            // Envia CPF + imagem facial ao endpoint de comparação
            const data = await post('/login_capture', { cpf, face_data: faceData });

            if (data.status === 'success') {
                // Exibe feedback de sucesso antes de redirecionar
                alert('Login realizado! Redirecionando...', 'success');
                setTimeout(() => { window.location.href = data.redirect; }, 1500);
            } else {
                alert(data.message);
                // Reativa o botão para nova tentativa
                btnCap.disabled = false;
                btnCap.innerHTML = '<span class="material-symbols-rounded">photo_camera</span> Capturar e Entrar';
            }
        } catch {
            alert('Erro de conexão. Tente novamente.');
            btnCap.disabled = false;
            btnCap.innerHTML = '<span class="material-symbols-rounded">photo_camera</span> Capturar e Entrar';
        }
    });

});
