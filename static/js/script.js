document.addEventListener('DOMContentLoaded', function() {
    // ---------- 标签页切换 ----------
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabId = this.dataset.tab;
            // 切换按钮状态
            tabButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            // 切换内容
            tabContents.forEach(c => c.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            // 重新渲染MathJax
            if (window.MathJax) MathJax.Hub.Queue(['Typeset', MathJax.Hub]);
        });
    });

    // ---------- 公共函数：渲染LaTeX ----------
    function renderMath() {
        if (window.MathJax) {
            MathJax.Hub.Queue(['Typeset', MathJax.Hub]);
        }
    }

    // ---------- 求导页面交互 ----------
    const implicitCheckbox = document.getElementById('derivative-implicit');
    const specificCheckbox = document.getElementById('derivative-specific');
    const yvarInput = document.getElementById('derivative-yvar');
    const xvalInput = document.getElementById('derivative-xval');

    // 隐函数复选框控制因变量输入框的启用状态
    implicitCheckbox.addEventListener('change', function() {
        yvarInput.disabled = !this.checked;
        if (!this.checked) specificCheckbox.checked = false; // 隐函数支持具体值？原逻辑支持，这里保持原样
    });

    // 求出具体值复选框控制自变量值输入框启用
    specificCheckbox.addEventListener('change', function() {
        xvalInput.disabled = !this.checked;
    });

    // 实时显示原函数（输入框内容变化时）
    const derivExprInput = document.getElementById('derivative-expr');
    derivExprInput.addEventListener('input', function() {
        const expr = this.value;
        if (!expr) return;
        fetch('/api/derivative', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ expr: expr, var: 'x', order: '1' }) // 仅获取原函数LaTeX
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('derivative-original').innerHTML = `\\(f(x)=${data.original}\\)`;
                renderMath();
            }
        })
        .catch(() => {});
    });

    // 求导按钮点击
    document.getElementById('derivative-btn').addEventListener('click', function() {
        const expr = derivExprInput.value;
        const var_ = document.getElementById('derivative-var').value;
        const order = document.getElementById('derivative-order').value;
        const isImplicit = implicitCheckbox.checked;
        const yVar = yvarInput.value || 'y';
        const isSpecific = specificCheckbox.checked;
        const xVal = xvalInput.value;

        const payload = {
            expr: expr,
            var: var_,
            order: order,
            is_implicit: isImplicit,
            y_var: yVar,
            is_specific: isSpecific,
            x_val: isSpecific ? xVal : null
        };

        fetch('/api/derivative', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // 更新原函数（可能输入时已经更新，但以防万一）
                document.getElementById('derivative-original').innerHTML = `\\(f(x)=${data.original}\\)`;
                // 导函数
                document.getElementById('derivative-result').innerHTML = `\\(f'(x)=${data.derivative}\\)`;
                // 导数值
                const valueDiv = document.getElementById('derivative-value');
                if (data.derivative_value) {
                    valueDiv.innerHTML = `\\(f'(${xVal})=${data.derivative_value}\\)`;
                } else {
                    valueDiv.innerHTML = '';
                }
                renderMath();
            } else {
                alert('求导失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });

    // 触发一次初始原函数显示
    if (derivExprInput.value) {
        derivExprInput.dispatchEvent(new Event('input'));
    }

    // ---------- 积分页面交互 ----------
    const definiteCheckbox = document.getElementById('integral-definite');
    const lowerInput = document.getElementById('integral-lower');
    const upperInput = document.getElementById('integral-upper');

    definiteCheckbox.addEventListener('change', function() {
        lowerInput.disabled = !this.checked;
        upperInput.disabled = !this.checked;
    });

    const integralExprInput = document.getElementById('integral-expr');
    integralExprInput.addEventListener('input', function() {
        const expr = this.value;
        if (!expr) return;
        fetch('/api/integral', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ expr: expr, var: 'x' })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('integral-original').innerHTML = `\\(f(x)=${data.original}\\)`;
                renderMath();
            }
        })
        .catch(() => {});
    });

    document.getElementById('integral-btn').addEventListener('click', function() {
        const expr = integralExprInput.value;
        const var_ = document.getElementById('integral-var').value;
        const isDefinite = definiteCheckbox.checked;
        const lower = lowerInput.value;
        const upper = upperInput.value;

        const payload = {
            expr: expr,
            var: var_,
            is_definite: isDefinite,
            lower: isDefinite ? lower : null,
            upper: isDefinite ? upper : null
        };

        fetch('/api/integral', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('integral-original').innerHTML = `\\(f(x)=${data.original}\\)`;
                document.getElementById('integral-antiderivative').innerHTML = `\\(F(x)=${data.antiderivative}\\)`;
                const definiteDiv = document.getElementById('integral-definite-value');
                if (data.definite_value) {
                    definiteDiv.innerHTML = `\\(\\int_{${lower}}^{${upper}} f(x)dx = ${data.definite_value}\\)`;
                } else {
                    definiteDiv.innerHTML = '';
                }
                renderMath();
            } else {
                alert('积分失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });

    if (integralExprInput.value) {
        integralExprInput.dispatchEvent(new Event('input'));
    }

    // ---------- 变形页面交互 ----------
    const simplifyExprInput = document.getElementById('simplify-expr');
    simplifyExprInput.addEventListener('input', function() {
        const expr = this.value;
        if (!expr) return;
        fetch('/api/simplify', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ expr: expr, method_index: 0 })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('simplify-original').innerHTML = `\\(${data.original}\\)`;
                renderMath();
            }
        })
        .catch(() => {});
    });

    document.getElementById('simplify-btn').addEventListener('click', function() {
        const expr = simplifyExprInput.value;
        const methodIndex = parseInt(document.getElementById('simplify-method').value, 10);

        fetch('/api/simplify', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ expr: expr, method_index: methodIndex })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('simplify-original').innerHTML = `\\(${data.original}\\)`;
                document.getElementById('simplify-result').innerHTML = `\\(${data.simplified}\\)`;
                document.getElementById('simplify-result-text').value = data.simplified_str;
                renderMath();
            } else {
                alert('变形失败：' + data.error);
            }
        })
        .catch(err => alert('网络错误：' + err));
    });

    if (simplifyExprInput.value) {
        simplifyExprInput.dispatchEvent(new Event('input'));
    }
});