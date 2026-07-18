// 通用 AJAX 请求工具
async function apiCall(url, data) {
    try {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        return await resp.json();
    } catch (e) {
        return { error: e.message };
    }
}

// 渲染 LaTeX 结果到指定元素
function renderMath(elementId, latexStr) {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (!latexStr) {
        el.innerHTML = '';
        return;
    }
    el.innerHTML = '\\[' + latexStr + '\\]';
    if (window.MathJax && window.MathJax.typesetPromise) {
        window.MathJax.typesetPromise([el]);
    }
}

// 显示文本结果
function showText(elementId, text) {
    const el = document.getElementById(elementId);
    if (el) el.textContent = text || '';
}

// 显示错误
function showError(elementId, msg) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = '<div class="error-msg">' + msg + '</div>';
    }
}

// 显示图片
function showImage(elementId, base64Data) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = '<img src="data:image/png;base64,' + base64Data + '" alt="绘图结果">';
    }
}

// 存档导出
function exportProject() {
    window.location.href = '/api/save';
}

// 存档导入
async function importProject(input) {
    if (!input.files || !input.files[0]) return;
    const formData = new FormData();
    formData.append('file', input.files[0]);
    try {
        const resp = await fetch('/api/load', { method: 'POST', body: formData });
        const result = await resp.json();
        if (result.ok) {
            alert('读档成功！');
            window.location.reload();
        } else {
            alert('读档失败: ' + (result.error || '未知错误'));
        }
    } catch (e) {
        alert('读档失败: ' + e.message);
    }
}

// 添加到缓存区
async function addToCache(text) {
    if (!text || !text.trim()) return;
    await apiCall('/api/huancun/add', { text: text.trim() });
}

// 回车键触发
function bindEnterKey(inputId, btnId) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(btnId);
    if (input && btn) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                btn.click();
            }
        });
    }
}
